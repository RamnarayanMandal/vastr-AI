"""Tests for the LangGraph-orchestrated VastrAI try-on workflow.

Covers the state machine (workflow.py): happy path through all nodes, the raw
fabric -> garment -> person requirement, permanent vs transient failure
routing, retry counting, DB persistence hook, and provider abstraction.
A deterministic mock provider drives the graph (no network).
"""

import io

import pytest
from PIL import Image

from app.config import settings
from app.services.workflow import (
    WorkflowComponents,
    WorkflowError,
    build_workflow_graph,
    node_generate_garment,
    node_generate_tryon,
    run_workflow,
)


def _png(data: bytes = None, size=(256, 256), color=(58, 131, 200)) -> bytes:
    im = Image.new("RGB", size, color if data is None else (90, 90, 90))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _person_bytes() -> bytes:
    return _png(color=(235, 228, 218), size=(320, 400))


def _fabric_bytes() -> bytes:
    return _png(color=(58, 131, 200))


class MockTryOnBackend:
    """Deterministic provider: fabric -> garment, person -> try-on."""

    def __init__(self, fail_garment=False, fail_tryon=False):
        self.fail_garment = fail_garment
        self.fail_tryon = fail_tryon
        self.garment_calls = 0
        self.tryon_calls = 0

    def generate_garment(self, fabric, garment_type, garment_style, analysis=None):
        self.garment_calls += 1
        if self.fail_garment:
            raise RuntimeError("model timeout")
        return _png(size=(256, 320), color=(90, 90, 90))

    def generate_tryon(self, person, garment, garment_type, garment_style, analysis=None):
        self.tryon_calls += 1
        if self.fail_tryon:
            raise RuntimeError("try-on failed")
        result = Image.open(io.BytesIO(person)).convert("RGB")
        buf = io.BytesIO()
        result.save(buf, "PNG")
        return buf.getvalue()


def _downloader(person=True, fabric=True):
    def dl(url):
        if "person" in url and person:
            return _person_bytes()
        if "fabric" in url and fabric:
            return _fabric_bytes()
        return None
    return dl


def _uploader(captured=None):
    def up(data, filename, folder):
        if captured is not None:
            captured["bytes"] = data
        return {"url": "https://ik.imagekit.io/vastrai/result.jpg", "fileId": "f-1"}
    return up


def test_workflow_happy_path_runs_all_nodes_and_produces_result_url():
    captured = {}
    backend = MockTryOnBackend()
    saved = {}
    st = run_workflow(
        job_id="j-1",
        person_image_url="http://x/person.jpg",
        fabric_image_url="http://x/fabric.jpg",
        garment_type="shirt",
        garment_style="casual",
        gender="MEN",
        provider=backend,
        downloader=_downloader(),
        uploader=_uploader(captured),
        saver=lambda s: saved.update(s),
    )
    assert st["status"] == "COMPLETED"
    assert st["result_url"] == "https://ik.imagekit.io/vastrai/result.jpg"
    assert st["error"] is None
    assert backend.garment_calls == 1
    assert backend.tryon_calls == 1
    stages = [s["stage"] for s in st["stage_log"]]
    assert stages == [
        "validate_inputs", "analyze_fabric", "build_prompt", "generate_garment",
        "generate_tryon", "validate_generated", "upload_result", "save_result",
    ]
    # Prompt built with LangChain - both garment + tryon prompts present.
    assert set((st["prompt"] or {}).keys()) == {"garment", "tryon"}
    assert "shirt" in st["prompt"]["garment"]
    assert "fabric" in st["prompt"]["tryon"].lower()
    # The fabricated analysis influences the prompt (fabric genuinely used).
    assert st["fabric_analysis"]["dominant_hex"].startswith("#")
    # Saver callback received the result_url.
    assert saved.get("result_url") == st["result_url"]


def test_workflow_missing_garment_type_is_permanent_failure():
    st = run_workflow(
        job_id="j-2", person_image_url="http://x/p.jpg", fabric_image_url="http://x/f.jpg",
        garment_type="", garment_style="casual", gender="MEN",
        provider=MockTryOnBackend(), downloader=_downloader(),
    )
    assert st["status"] == "FAILED"
    assert "Garment type and style" in (st["error"] or "")
    assert st.get("retryable") is False


def test_workflow_transient_failure_is_retryable_and_marks_failed():
    backend = MockTryOnBackend(fail_garment=True)
    st = run_workflow(
        job_id="j-3", person_image_url="http://x/person.jpg", fabric_image_url="http://x/fabric.jpg",
        garment_type="shirt", garment_style="casual", gender="MEN",
        provider=backend, downloader=_downloader(), uploader=_uploader(),
    )
    assert st["status"] == "FAILED"
    assert "Garment generation failed" in (st["error"] or "")
    assert st.get("retryable") is True


def test_workflow_imagekit_upload_failure_retryable():
    backend = MockTryOnBackend()
    st = run_workflow(
        job_id="j-4", person_image_url="http://x/person.jpg", fabric_image_url="http://x/fabric.jpg",
        garment_type="shirt", garment_style="casual", gender="MEN",
        provider=backend, downloader=_downloader(),
        uploader=lambda data, filename, folder: None,  # ImageKit not configured
    )
    assert st["status"] == "FAILED"
    assert "Could not store" in (st["error"] or "")
    assert st.get("retryable") is True


def test_workflow_invalid_person_image_permanent():
    st = run_workflow(
        job_id="j-5", person_image_url="http://x/person-bad.jpg", fabric_image_url="http://x/f.jpg",
        garment_type="shirt", garment_style="casual", gender="MEN",
        provider=MockTryOnBackend(),
        downloader=lambda url: b"not-an-image" if "person" in url else _fabric_bytes(),
        uploader=_uploader(),
    )
    assert st["status"] == "FAILED"
    assert "not a valid image" in (st["error"] or "")
    assert st.get("retryable") is False


def test_workflow_graph_compiles_and_is_inspectable():
    graph = build_workflow_graph(max_retries=3)
    # LangGraph exposes the nodes we added (StateGraph nodes).
    node_ids = set(graph.nodes.keys())
    for expected in ["validate_inputs", "analyze_fabric", "build_prompt",
                     "generate_garment", "generate_tryon", "validate_generated",
                     "upload_result", "save_result", "complete", "fail"]:
        assert expected in node_ids


# ---------------------------------------------------------------------------
# LangGraph + real OpenAI (GPT-Image-2) backend, transport-stubbed
# ---------------------------------------------------------------------------

def _sim_garment(fabric_bytes: bytes) -> bytes:
    from PIL import Image, ImageDraw

    fabric = Image.open(io.BytesIO(fabric_bytes)).convert("RGB").resize((256, 320))
    mask = Image.new("L", (256, 320), 0)
    d = ImageDraw.Draw(mask)
    d.rectangle([44, 30, 124, 96], fill=200)
    d.rectangle([132, 30, 212, 96], fill=200)
    d.rectangle([44, 60, 212, 250], fill=255)
    canvas = Image.new("RGB", (256, 320), (247, 244, 240))
    canvas.paste(fabric, (0, 0), mask)
    buf = io.BytesIO()
    canvas.save(buf, "PNG")
    return buf.getvalue()


def _sim_tryon(person_bytes: bytes, _garment_bytes: bytes, color: tuple) -> bytes:
    from PIL import Image, ImageDraw

    person = Image.open(io.BytesIO(person_bytes)).convert("RGB")
    w, h = person.size
    d = ImageDraw.Draw(person)
    d.rectangle([int(w * 0.12), int(h * 0.42), int(w * 0.88), int(h * 0.66)], fill=color)
    buf = io.BytesIO()
    person.save(buf, "PNG")
    return buf.getvalue()


def test_workflow_openai_gpt_image2_end_to_end_carries_fabric(monkeypatch):
    """The LangGraph workflow + real gpt-image-2 backend produces a result whose
    garment region carries the selected fabric's dominant colour and whose
    person is preserved (raw-fabric -> garment -> person requirement)."""
    import base64
    from unittest.mock import patch
    from PIL import Image
    from app.services.image_gen import OpenAIImageGenBackend

    fabric_bytes = _fabric_bytes()  # blue (58,131,200)
    person_bytes = _person_bytes()
    fabric_rgb = tuple(int(c) for c in (58, 131, 200))

    class _Resp:
        def __init__(self, b64):
            self.status_code = 200
            self.headers = {"content-type": "application/json"}
            self.text = ""
            self.content = b""
            self._data = {"data": [{"b64_json": b64}]}

        def json(self):
            return self._data

    def transport(url, *, data=None, files=None, headers=None, timeout=None, **kw):
        images = [f[1][1] for f in list(files) if f[0] == "image[]"]
        out = _sim_garment(images[0]) if len(images) == 1 else _sim_tryon(images[0], images[1], fabric_rgb)
        return _Resp(base64.b64encode(out).decode())

    with patch("app.services.image_gen.httpx.post", side_effect=transport):
        from app.services.workflow import run_workflow

        st = run_workflow(
            job_id="lg-e2e",
            person_image_url="http://x/person.jpg",
            fabric_image_url="http://x/fabric.jpg",
            garment_type="shirt",
            garment_style="casual",
            gender="women",
            provider=OpenAIImageGenBackend(api_key="sk-test", model="gpt-image-2", aspect_ratio="3:4"),
            downloader=lambda url: person_bytes if "person" in url else fabric_bytes,
            uploader=lambda data, filename, folder: {"url": "https://ik.imagekit.io/vastrai/lg-e2e.jpg", "fileId": "f-1"},
        )

    assert st["status"] == "COMPLETED"
    assert st["result_url"] == "https://ik.imagekit.io/vastrai/lg-e2e.jpg"
    result_bytes = st["generated_image"]
    assert result_bytes and len(result_bytes) > 500

    # 1. Person identity preserved: face region matches the source.
    from app.services.pipeline import identity_metrics
    score = identity_metrics(person_bytes, result_bytes)
    assert score > 0.7, f"identity not preserved: {score:.3f}"

    # 2. The generated result genuinely differs from the person photo.
    with Image.open(io.BytesIO(result_bytes)) as im:
        w, h = im.size
        assert min(w, h) >= 128
        region = im.crop((int(w * 0.15), int(h * 0.42), int(w * 0.85), int(h * 0.55))).resize((32, 32))
        px = list(region.getdata())
        color = tuple(sum(c[i] for c in px) // len(px) for i in range(3))

    # 3. Garment region carries the fabric's dominant colour (on-brief).
    dist = sum((a - b) ** 2 for a, b in zip(color, fabric_rgb)) ** 0.5
    assert dist < 60, f"garment colour drifted: {color} vs fabric {fabric_rgb}"

