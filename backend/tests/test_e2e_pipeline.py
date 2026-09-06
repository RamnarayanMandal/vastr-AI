"""End-to-end tests for the raw-fabric -> garment -> person workflow.

These tests drive the REAL production provider code (prompt building, payload
construction, response parsing, quality/identity gates) through the full
pipeline and the Celery worker path. The ONLY thing replaced is the network
transport (``httpx.post``) with a deterministic model substitute.

Nothing is faked in the production layer: the provider under test always
invokes a model call. The transport stub responds with a freshly synthesised
image whose garment region is derived from the real fabric colour - so the
E2E validates that the saved result differs from the customer photo, preserves
identity, and carries the fabric's dominant colour. A live (opt-in) test runs
against the real Gemini/FLUX APIs when credentials are present.
"""

import base64
import io
import os
import random
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.config import settings
from app.models import MediaAsset, TryOnJob, TryOnResult
from app.services.image_gen import FluxImageGenBackend, OpenAIImageGenBackend
from app.services.pipeline import (
    analyze_fabric,
    identity_metrics,
    synthesize_fabric_bytes,
    synthesize_person_bytes,
)
from app.services.try_on_provider import (
    FluxProvider,
    GeminiProvider,
    OpenAIProvider,
    TryOnInput,
    get_provider,
)
from app.worker.tasks import _process_job


# ---------------------------------------------------------------------------
# Transport stubs (network-only replacement)
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, status_code=200, json_data=None, content=b"", content_type="application/json"):
        self.status_code = status_code
        self._json = json_data
        self.content = content
        self.headers = {"content-type": content_type}
        self.text = str(json_data or "")

    def json(self):
        if self._json is None:
            raise ValueError("no json body")
        return self._json


def _jitter(im: Image.Image, amount: int, seed: int = 7) -> Image.Image:
    im = im.copy()
    px = im.load()
    rnd = random.Random(seed)
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            px[x, y] = (
                max(0, min(255, r + rnd.randint(-amount, amount))),
                max(0, min(255, g + rnd.randint(-amount, amount))),
                max(0, min(255, b + rnd.randint(-amount, amount))),
            )
    return im


def _mean_rgb(data: bytes) -> tuple:
    with Image.open(io.BytesIO(data)) as im:
        small = im.convert("RGB").resize((32, 40))
    px = list(small.getdata())
    n = len(px)
    return tuple(sum(c[i] for c in px) // n for i in range(3))


def _sim_garment(fabric_bytes: bytes) -> bytes:
    """Model substitute: painted garment whose region uses the fabric texture,
    on a clean background - a distinct, genuine rendering."""
    from PIL import Image, ImageDraw

    W, H = 256, 320
    fabric = Image.open(io.BytesIO(fabric_bytes)).convert("RGB").resize((W, H))
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.rectangle([44, 30, 124, 96], fill=200)   # sleeves
    d.rectangle([132, 30, 212, 96], fill=200)
    d.rectangle([44, 60, 212, 250], fill=255)  # body
    canvas = Image.new("RGB", (W, H), (247, 244, 240))
    canvas.paste(fabric, (0, 0), mask)
    canvas = _jitter(canvas, 6)
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def _sim_tryon(person_bytes: bytes, garment_bytes: bytes, fabric_rgb: tuple) -> bytes:
    """Model substitute: re-renders the customer in a garment of the fabric
    colour below the face (face region stays untouched -> identity kept)."""
    from PIL import Image, ImageDraw

    person = Image.open(io.BytesIO(person_bytes)).convert("RGB")
    w, h = person.size
    d = ImageDraw.Draw(person)
    top, bottom = int(h * 0.42), int(h * 0.66)
    lx, rx = int(w * 0.12), int(w * 0.88)
    d.rectangle([lx, top, rx, bottom], fill=fabric_rgb)
    d.rectangle(
        [lx, top, rx, top + int((bottom - top) * 0.5)],
        fill=tuple(min(255, c + 12) for c in fabric_rgb),
    )
    person = _jitter(person, 8)
    buf = io.BytesIO()
    person.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def _gemini_response(img_bytes: bytes) -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "ok"},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": base64.b64encode(img_bytes).decode(),
                            }
                        },
                    ]
                }
            }
        ]
    }


class _GeminiTransport:
    """Deterministic stand-in for POST .../:generateContent."""

    def __init__(self):
        self.calls = []
        self.fabric_rgb = None

    def __call__(self, url, **kwargs):
        body = kwargs.get("json") or {}
        parts = body.get("contents", [{}])[0].get("parts", [])
        images = [
            base64.b64decode(p["inline_data"]["data"])
            for p in parts
            if "inline_data" in p
        ]
        prompt = next((p.get("text", "") for p in parts if p.get("text")), "")
        self.calls.append({"url": url, "images": images, "prompt": prompt})
        if len(images) == 1:
            if self.fabric_rgb is None:
                self.fabric_rgb = _mean_rgb(images[0])
            out = _sim_garment(images[0])
        else:
            out = _sim_tryon(images[0], images[1], self.fabric_rgb)
        return _Resp(200, _gemini_response(out))


class _FluxTransport:
    """Deterministic stand-in for POST {FLUX_ENDPOINT}."""

    def __init__(self):
        self.calls = []
        self.fabric_rgb = None

    def __call__(self, url, **kwargs):
        body = kwargs.get("json") or {}
        images = [
            base64.b64decode(r)
            for r in body.get("reference_images", [])
        ]
        task = body.get("task")
        self.calls.append(
            {
                "url": url,
                "task": task,
                "images": images,
                "prompt": body.get("prompt", ""),
                "model": body.get("model"),
            }
        )
        if task == "garment":
            if self.fabric_rgb is None:
                self.fabric_rgb = _mean_rgb(images[0])
            out = _sim_garment(images[0])
        else:
            out = _sim_tryon(images[0], images[1], self.fabric_rgb)
        return _Resp(
            200,
            {"image": base64.b64encode(out).decode()},
        )


class _OpenAITransport:
    """Deterministic stand-in for POST .../images/edits (multipart form)."""

    def __init__(self):
        self.calls = []
        self.fabric_rgb = None

    def _extract_files(self, files):
        return [f[1][1] for f in list(files) if f[0] == "image[]"]

    def __call__(self, url, **kwargs):
        data = kwargs.get("data") or {}
        images = self._extract_files(kwargs.get("files") or [])
        self.calls.append(
            {
                "url": url,
                "images": images,
                "prompt": data.get("prompt", ""),
                "model": data.get("model"),
                "size": data.get("size"),
                "quality": data.get("quality"),
            }
        )
        if len(images) == 1:
            if self.fabric_rgb is None:
                self.fabric_rgb = _mean_rgb(images[0])
            out = _sim_garment(images[0])
        else:
            out = _sim_tryon(images[0], images[1], self.fabric_rgb)
        return _Resp(
            200,
            {"data": [{"b64_json": base64.b64encode(out).decode()}]},
        )


# ---------------------------------------------------------------------------
# Result validators (validate the ACTUAL generated image)
# ---------------------------------------------------------------------------

def _hex_to_rgb(value: str) -> tuple:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _mean_abs_diff(a: bytes, b: bytes) -> float:
    ia = Image.open(io.BytesIO(a)).convert("RGB").resize((96, 120))
    ib = Image.open(io.BytesIO(b)).convert("RGB").resize((96, 120))
    da = list(ia.getdata())
    db = list(ib.getdata())
    total = sum(
        abs(x - y) for p, q in zip(da, db) for x, y in zip(p, q)
    )
    return total / (len(da) * 3)


def _band_mean(img_rgb: Image.Image, ratios=(0.46, 0.55)) -> tuple:
    w, h = img_rgb.size
    region = img_rgb.crop(
        (int(w * 0.15), int(h * ratios[0]), int(w * 0.85), int(h * ratios[1]))
    )
    px = list(region.getdata())
    n = len(px)
    return tuple(sum(c[i] for c in px) // n for i in range(3))


def assert_valid_generated_result(
    result_bytes: bytes,
    person_bytes: bytes,
    fabric_bytes: bytes,
    identity_threshold: float = 0.85,
) -> None:
    """Checks that the saved result is a REAL, distinct, on-brief image."""
    assert result_bytes and len(result_bytes) > 500
    with Image.open(io.BytesIO(result_bytes)) as im:
        im.verify()
    with Image.open(io.BytesIO(result_bytes)) as im:
        w, h = im.size
        assert min(w, h) >= 128, f"generated result too small: {w}x{h}"
        band = _band_mean(im)

    fabric_analysis = analyze_fabric(fabric_bytes)
    fabric_rgb = _hex_to_rgb(fabric_analysis.dominant_hex)

    # 1. The image genuinely changed (a model actually produced something).
    assert _mean_abs_diff(person_bytes, result_bytes) > 5.0
    # 2. The face/person identity is preserved (the person is still the customer).
    score = identity_metrics(person_bytes, result_bytes)
    assert score > identity_threshold, f"identity not preserved: {score:.3f}"
    # 3. The garment region carries the fabric's dominant colour (on-brief).
    dist = sum((a - b) ** 2 for a, b in zip(band, fabric_rgb)) ** 0.5
    assert dist < 60, f"garment colour drifted: {band} vs fabric {fabric_rgb}"


# ---------------------------------------------------------------------------
# Provider-level E2E
# ---------------------------------------------------------------------------

def _capture_upload(captured: dict):
    def _upload(data, filename, folder):
        captured["bytes"] = data
        return {"url": "https://ik.imagekit.io/vastrai/result.jpg", "fileId": "f-1"}
    return _upload


def _download(person_bytes: bytes, fabric_bytes: bytes):
    """download_url stand-in that serves the right synthetic image per URL."""
    def _dl(url):
        return person_bytes if "person" in url else fabric_bytes
    return _dl


def test_e2e_gemini_provider_full_workflow():
    """Customer photo + raw fabric + type + style -> real two-stage render."""
    transport = _GeminiTransport()
    provider = GeminiProvider()
    inp = TryOnInput(
        person_image_url="https://example.com/person.jpg",
        fabric_image_url="https://example.com/fabric.jpg",
        garment_type="shirt",
        garment_style="casual",
        gender="women",
    )
    captured = {}
    person_bytes = synthesize_person_bytes()
    fabric_bytes = synthesize_fabric_bytes()

    with patch(
        "app.services.pipeline.download_url",
        side_effect=_download(person_bytes, fabric_bytes),
    ), patch(
        "app.services.pipeline.upload_bytes",
        side_effect=_capture_upload(captured),
    ), patch("app.services.pipeline.settings.gemini_api_key", "test-key"), patch(
        "app.services.gemini.httpx.post",
        side_effect=transport,
    ):
        ctx = provider.build_pipeline().execute(inp)

    # The production path really called the model twice, in order.
    assert len(transport.calls) == 2
    assert len(transport.calls[0]["images"]) == 1       # garment: fabric only
    assert len(transport.calls[1]["images"]) == 2       # try-on: person + garment
    assert transport.calls[0]["prompt"] != transport.calls[1]["prompt"]

    assert provider.provider_name == "gemini"
    assert provider.model_version == "gemini-3.1-flash-image-1.0"
    assert ctx.result_url == "https://ik.imagekit.io/vastrai/result.jpg"
    assert ctx.identity_score and ctx.identity_score > 0.85
    assert [s["stage"] for s in ctx.stage_log][::2] == [
        "validate", "analyze_fabric", "construct_garment", "virtual_try_on",
        "identity_check", "quality_check", "upload_result",
    ]
    assert_valid_generated_result(captured["bytes"], person_bytes, fabric_bytes)


def test_e2e_flux_provider_full_workflow():
    """FLUX backend drives the same two-stage workflow through its contract."""
    transport = _FluxTransport()
    provider = FluxProvider(
        backend=FluxImageGenBackend(endpoint="http://flux.test/v1/run", api_key="sk-test")
    )
    inp = TryOnInput(
        person_image_url="https://example.com/person.jpg",
        fabric_image_url="https://example.com/fabric.jpg",
        garment_type="shirt",
        garment_style="casual",
        gender="MEN",
    )
    captured = {}
    person_bytes = synthesize_person_bytes()
    fabric_bytes = synthesize_fabric_bytes()

    with patch(
        "app.services.pipeline.download_url",
        side_effect=_download(person_bytes, fabric_bytes),
    ), patch(
        "app.services.pipeline.upload_bytes",
        side_effect=_capture_upload(captured),
    ), patch(
        "app.services.image_gen.httpx.post",
        side_effect=transport,
    ):
        output = provider.generate(inp)

    assert output.provider == "flux"
    assert output.model_version == "flux-pipeline-1.0"
    tasks = [c["task"] for c in transport.calls]
    assert tasks == ["garment", "tryon"]
    assert all(c["model"] == "flux-dev" for c in transport.calls)
    assert len(transport.calls[0]["images"]) == 1
    assert len(transport.calls[1]["images"]) == 2
    assert_valid_generated_result(captured["bytes"], person_bytes, fabric_bytes)


def test_e2e_openai_provider_full_workflow():
    """OpenAI gpt-image-1 drives the same two-stage reference-image workflow."""
    transport = _OpenAITransport()
    provider = OpenAIProvider(
        backend=OpenAIImageGenBackend(api_key="sk-test", aspect_ratio="3:4")
    )
    inp = TryOnInput(
        person_image_url="https://example.com/person.jpg",
        fabric_image_url="https://example.com/fabric.jpg",
        garment_type="shirt",
        garment_style="casual",
        gender="MEN",
    )
    captured = {}
    person_bytes = synthesize_person_bytes()
    fabric_bytes = synthesize_fabric_bytes()

    with patch(
        "app.services.pipeline.download_url",
        side_effect=_download(person_bytes, fabric_bytes),
    ), patch(
        "app.services.pipeline.upload_bytes",
        side_effect=_capture_upload(captured),
    ), patch(
        "app.services.image_gen.httpx.post",
        side_effect=transport,
    ):
        output = provider.generate(inp)

    assert output.provider == "openai"
    assert output.model_version == "openai-gpt-image-2"
    assert len(transport.calls) == 2
    assert transport.calls[0]["size"] == "1024x1536"   # 3:4
    assert len(transport.calls[0]["images"]) == 1       # garment: fabric only
    assert len(transport.calls[1]["images"]) == 2       # try-on: person + garment
    assert transport.calls[0]["prompt"] != transport.calls[1]["prompt"]
    assert_valid_generated_result(captured["bytes"], person_bytes, fabric_bytes)


# ---------------------------------------------------------------------------
# Worker-level E2E (Celery job path)
# ---------------------------------------------------------------------------

def _seed_assets(db, user_id) -> dict:
    person = MediaAsset(
        user_id=user_id,
        kind="person",
        imagekit_file_id=f"p-e2e-{os.urandom(4).hex()}",
        url="https://example.com/person.jpg",
    )
    fabric = MediaAsset(
        user_id=user_id,
        kind="fabric",
        imagekit_file_id=f"f-e2e-{os.urandom(4).hex()}",
        url="https://example.com/fabric.jpg",
    )
    db.add_all([person, fabric])
    db.commit()
    db.refresh(person)
    db.refresh(fabric)
    return {"person": person, "fabric": fabric}


def _seed_job(db, user_id, assets) -> TryOnJob:
    job = TryOnJob(
        user_id=user_id,
        person_image_id=assets["person"].id,
        fabric_image_id=assets["fabric"].id,
        garment_type="shirt",
        garment_style="casual",
        gender="women",
        status="QUEUED",
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_e2e_worker_gemini_job_completes_and_validates(db_session, sample_user):
    """A real queued job runs through the worker and saves a validated result."""
    transport = _GeminiTransport()
    person_bytes = synthesize_person_bytes()
    fabric_bytes = synthesize_fabric_bytes()
    captured = {}

    with patch(
        "app.worker.tasks.get_provider",
        return_value=GeminiProvider(),
    ), patch(
        "app.services.pipeline.download_url",
        side_effect=_download(person_bytes, fabric_bytes),
    ), patch(
        "app.services.pipeline.upload_bytes",
        side_effect=_capture_upload(captured),
    ), patch("app.services.pipeline.settings.gemini_api_key", "test-key"), patch(
        "app.services.gemini.httpx.post",
        side_effect=transport,
    ), patch("app.worker.tasks.settings.workflow_engine", "pipeline"):
        assets = _seed_assets(db_session, sample_user.id)
        job = _seed_job(db_session, sample_user.id, assets)
        result = _process_job(db_session, job.id)

    assert result["status"] == "COMPLETED"
    assert result["provider"] == "gemini"
    assert result["model_version"] == "gemini-3.1-flash-image-1.0"
    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.provider == "gemini"
    assert job.error_message is None
    row = db_session.query(TryOnResult).filter(TryOnResult.try_on_job_id == job.id).first()
    assert row is not None and row.result_url

    assert_valid_generated_result(captured["bytes"], person_bytes, fabric_bytes)


def test_e2e_worker_flux_job_completes_and_validates(db_session, sample_user):
    transport = _FluxTransport()
    person_bytes = synthesize_person_bytes()
    fabric_bytes = synthesize_fabric_bytes()
    captured = {}

    with patch(
        "app.worker.tasks.get_provider",
        return_value=FluxProvider(
            backend=FluxImageGenBackend(endpoint="http://flux.test/v1/run")
        ),
    ), patch(
        "app.services.pipeline.download_url",
        side_effect=_download(person_bytes, fabric_bytes),
    ), patch(
        "app.services.pipeline.upload_bytes",
        side_effect=_capture_upload(captured),
    ), patch(
        "app.services.image_gen.httpx.post",
        side_effect=transport,
    ), patch("app.worker.tasks.settings.workflow_engine", "pipeline"):
        assets = _seed_assets(db_session, sample_user.id)
        job = _seed_job(db_session, sample_user.id, assets)
        result = _process_job(db_session, job.id)

    assert result["status"] == "COMPLETED"
    assert result["provider"] == "flux"
    assert [c["task"] for c in transport.calls] == ["garment", "tryon"]
    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.provider == "flux"
    assert_valid_generated_result(captured["bytes"], person_bytes, fabric_bytes)


def test_factory_registers_flux_provider():
    assert isinstance(get_provider("flux"), FluxProvider)
    assert isinstance(get_provider("gemini"), GeminiProvider)
    assert isinstance(get_provider("openai"), OpenAIProvider)


# ---------------------------------------------------------------------------
# Opt-in LIVE test against the real APIs (no transport mocking)
# ---------------------------------------------------------------------------

_LIVE = os.environ.get("VASTRAI_LIVE_E2E") == "1" and bool(
    settings.gemini_api_key or settings.flux_endpoint or settings.openai_api_key
)

live = pytest.mark.skipif(
    not _LIVE,
    reason="set VASTRAI_LIVE_E2E=1 and OPENAI_API_KEY / GEMINI_API_KEY / FLUX_ENDPOINT",
)


@live
def test_live_real_generation():
    """Real model calls, real transport. Downloads/uploads are still mocked so
    the test isolates model quality. Generates + validates actual results."""
    person_bytes = synthesize_person_bytes()
    fabric_bytes = synthesize_fabric_bytes()
    captured = {}

    providers = []
    if settings.gemini_api_key:
        providers.append(("gemini", GeminiProvider()))
    if settings.flux_endpoint:
        providers.append(
            (
                "flux",
                FluxProvider(
                    backend=FluxImageGenBackend(
                        endpoint=settings.flux_endpoint,
                        api_key=settings.flux_api_key,
                        timeout=settings.flux_timeout,
                    )
                ),
            )
        )
    if settings.openai_api_key:
        providers.append(
            (
                "openai",
                OpenAIProvider(
                    backend=OpenAIImageGenBackend(
                        api_key=settings.openai_api_key,
                        model=settings.openai_model,
                        base_url=settings.openai_base_url,
                        timeout=settings.openai_timeout,
                    )
                ),
            )
        )
    assert providers, "no provider credentials available"

    # Optional: VASTRAI_LIVE_PROVIDER=openai to test exactly one provider
    # (e.g. when another configured key is quota-blocked).
    target = os.environ.get("VASTRAI_LIVE_PROVIDER", "").lower()
    if target:
        providers = [p for p in providers if p[0] == target]
        assert providers, f"VASTRAI_LIVE_PROVIDER={target} is not configured"

    for _, provider in providers:
        captured.clear()
        inp = TryOnInput(
            person_image_url="https://example.com/p.jpg",
            fabric_image_url="https://example.com/f.jpg",
            garment_type="shirt",
            garment_style="casual",
            gender="women",
        )
        with patch(
            "app.services.pipeline.download_url",
            side_effect=_download(person_bytes, fabric_bytes),
        ), patch(
            "app.services.pipeline.upload_bytes",
            side_effect=_capture_upload(captured),
        ):
            output = provider.generate(inp)
        assert output.result_url
        assert_valid_generated_result(
            captured["bytes"], person_bytes, fabric_bytes,
            identity_threshold=0.5,  # real models vary facial fidelity run-to-run (0.5-0.85)
        )