"""Unit tests for the image-generation backend abstraction (image_gen)."""

import base64

import pytest
from unittest.mock import patch

from app.services.image_gen import (
    FluxImageGenBackend,
    GeminiImageGenBackend,
    ImageGenAPIError,
    ImageGenNotConfigured,
    OpenAIImageGenBackend,
    OpenRouterImageGenBackend,
    build_garment_prompt,
    build_tryon_prompt,
    get_image_gen_backend,
)


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


def test_prompt_builders_are_distinct():
    garment = build_garment_prompt("shirt", "casual", None)
    tryon = build_tryon_prompt("shirt", "casual", None)
    assert garment and tryon
    assert garment != tryon
    assert "shirt" in garment.lower() and "fabric" in garment.lower()


# --- Garment-type + style accuracy (hard constraints) -----------------------

def test_blouse_boat_neck_prompt_is_hard_constrained():
    """TEST 1: blouse + boat neck -> recognizable boat-neck blouse, not a tee."""
    prompt = build_tryon_prompt("blouse", "boat_neck", None).lower()
    assert "boat neck blouse" in prompt
    assert "blouse silhouette" in prompt or "feminine blouse" in prompt
    assert "boat neckline" in prompt or "boat neck" in prompt
    # style must not replace the category
    assert "remain a blouse" in prompt
    assert "never change the garment category" in prompt
    # negative constraints for a generic top
    assert "generic t-shirt" in prompt or "t-shirt" in prompt
    assert "tunic" in prompt and "oversized top" in prompt


def test_blouse_round_neck_prompt():
    """TEST 2: blouse + round neck -> blouse with a ROUND neckline."""
    prompt = build_tryon_prompt("blouse", "round_neck", None).lower()
    assert "round crew neckline" in prompt or "round neckline" in prompt
    assert "blouse" in prompt
    # round neck must not degrade into a boat/V/sweetheart neck
    assert "keep it as the garment's neckline" in prompt


def test_shirt_formal_prompt_stays_a_shirt():
    """TEST 3: shirt + formal -> clearly a shirt, not a blouse/top."""
    prompt = build_garment_prompt("shirt", "formal", None).lower()
    assert "button-down shirt" in prompt and "collar" in prompt
    assert "never a blouse, top or knit" in prompt or "blouse" in prompt
    assert "remain a shirt" in prompt


def test_t_shirt_prompt_stays_a_t_shirt():
    """TEST 4: t-shirt + casual -> clearly a T-shirt (crew neck, no tailoring)."""
    prompt = build_garment_prompt("t_shirt", "casual", None).lower()
    assert "t-shirt" in prompt or "t shirt" in prompt
    assert "crew-neck round collar" in prompt or "crew" in prompt
    assert "blouse" not in prompt.split("explicitly avoid")[0]


def test_checkered_fabric_preservation_with_blouse_constraint():
    """TEST 5: blouse + boat neck + checkered fabric keeps both constraints
    (recognizable boat-neck blouse AND checkered pattern preservation text)."""
    analysis = {
        "dominant_hex": "#c0392b",
        "palette": ["#c0392b", "#f1c40f"],
        "has_pattern": True,
        "brightness": 0.5,
    }
    from app.services.prompts import VastrAIPrompts
    prompt = build_tryon_prompt("blouse", "boat_neck", analysis)
    low = prompt.lower()
    assert "checkered" in low or "checks or checkered patterns" in low
    assert VastrAIPrompts.PRESERVATION_MARKER in prompt
    assert "boat neck" in low and "blouse silhouette" in low
    # the fabric description text must still reach the prompt
    assert "dominant colour #c0392b" in low or "dominant color #c0392b" in low


def test_prompt_constraint_flags(capsys):
    """Audit helper reports type/style constraint flags + runtime fields."""
    from app.services.prompts import VastrAIPrompts

    flags = VastrAIPrompts.constraint_flags("blouse", "boat_neck")
    assert flags == {"garment_type_constraint": True, "style_constraint": True}

    VastrAIPrompts.audit_request("tryon", "blouse", "boat_neck", True)
    out = capsys.readouterr().out
    assert "[TRYON][GARMENT]" in out and "type=blouse" in out
    assert "style=boat_neck" in out and "reference_attached=true" in out
    assert "[TRYON][PROMPT]" in out
    assert "garment_type_constraint=true" in out and "style_constraint=true" in out


def test_blouse_designer_prompt_never_a_shirt_kurta_tunic():
    """Bug fix: blouse + designer must stay a blouse, never shirt/kurta/tunic."""
    from app.services.image_gen import build_tryon_prompt
    from app.services.garment_spec import garment_negative_constraint

    prompt = build_tryon_prompt("blouse", "designer", None).lower()
    # feminine blouse remains the hard constraint
    assert "feminine blouse construction" in prompt or "blouse silhouette" in prompt
    assert "remain a blouse" in prompt
    assert "must never override, replace, re-categorise or genericize it" in prompt
    # designer stays a modifier on the blouse, not a category change
    assert "designer" in prompt and "designer-level detailing" in prompt
    # explicit antis: no shirt/kurta/ethnic/tunic/mandarin/stand collar
    neg = garment_negative_constraint("blouse", "designer")
    assert "kurta" in neg and "kurti" in neg and "ethnic straight-cut top" in neg
    assert "mandarin collar" in neg and "stand collar" in neg
    assert "shirt collar" in neg and "men's button-down shirt" in neg
    # the same antis must actually reach the full try-on prompt
    for term in (
        "kurta", "kurti", "mandarin collar", "stand collar",
        "men's button-down shirt", "tunic",
    ):
        assert term in prompt


def test_garment_negative_constraint_designer_only_reinforces_own_type():
    """Designer adds a small dev-negative reinforcement on top of the type's
    own (already strengthened) antis; unrelated types stay clean."""
    from app.services.garment_spec import garment_negative_constraint

    # blouse + designer: full antis include shirt/kurta/tunic/mandarin collar
    blouse_designer = garment_negative_constraint("blouse", "designer")
    assert "kurta" in blouse_designer and "stand collar" in blouse_designer
    assert "men's button-down shirt" in blouse_designer
    # blouse (any style) already forbids kurta/stand collar via its type spec
    boat = garment_negative_constraint("blouse", "boat_neck")
    assert "kurta" in boat and "stand collar" in boat
    assert "generic top" in boat and "tunic" in boat
    # t-shirt + designer keeps ITS OWN antis - never blouse tailoring terms
    tshirt_designer = garment_negative_constraint("t_shirt", "designer")
    assert "men's button-down shirt" not in tshirt_designer
    assert "shirt collar" not in tshirt_designer


def test_t_shirt_designer_stays_a_t_shirt():
    """Blouse-specific antis never leak into an unrelated type, even designer."""
    from app.services.image_gen import build_garment_prompt
    from app.services.garment_spec import garment_negative_constraint

    prompt = build_garment_prompt("t_shirt", "designer", None).lower()
    assert "t-shirt" in prompt or "t shirt" in prompt
    # t-shirt keeps its OWN correct negatives (a tee must not become a blouse)
    neg = garment_negative_constraint("t_shirt", "designer")
    assert "blouse" in neg  # from t_shirt's own spec - correct
    # dev-only designer reinforcement never injects blouse-unrelated tailors
    assert "men's button-down shirt" not in neg  # t-shirt superset keeps it clean
    assert "shirt collar" not in neg


def test_get_backend_by_name():
    assert isinstance(get_image_gen_backend("gemini"), GeminiImageGenBackend)
    assert isinstance(get_image_gen_backend("flux"), FluxImageGenBackend)
    assert isinstance(get_image_gen_backend("openai"), OpenAIImageGenBackend)
    with pytest.raises(ImageGenNotConfigured):
        get_image_gen_backend("nope")


def test_gemini_backend_fails_honestly_when_unconfigured():
    """No GEMINI_API_KEY (test env) -> ImageGenNotConfigured, never a fake."""
    backend = GeminiImageGenBackend()
    with pytest.raises(ImageGenNotConfigured):
        backend.generate_garment(b"fabric-bytes", "shirt", "casual", None)


def test_gemini_backend_returns_bytes():
    backend = GeminiImageGenBackend()
    with patch("app.services.gemini.generate_image", return_value=b"\xff\xd8jpeg!"):
        out = backend.generate_garment(b"fabric", "shirt", "casual", None)
    assert out == b"\xff\xd8jpeg!"


def test_gemini_backend_maps_api_errors():
    backend = GeminiImageGenBackend()
    with patch(
        "app.services.gemini.generate_image", side_effect=RuntimeError("boom")
    ):
        with pytest.raises(ImageGenAPIError):
            backend.generate_tryon(b"p", b"g", "shirt", "casual", None)


def test_flux_backend_fails_honestly_without_endpoint():
    backend = FluxImageGenBackend(endpoint="")
    with pytest.raises(ImageGenNotConfigured):
        backend.generate_garment(b"fabric", "shirt", "casual", None)


def test_flux_backend_posts_expected_payload():
    captured = {}
    img_bytes = b"\xff\xd8" + bytes(range(64)) * 4  # 258 bytes, realistic

    def fake_post(url, *, json=None, headers=None, timeout=None, **kw):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _Resp(200, {"image": base64.b64encode(img_bytes).decode()})

    backend = FluxImageGenBackend(endpoint="http://flux.test/v1/run", api_key="sk-1")
    with patch("app.services.image_gen.httpx.post", side_effect=fake_post):
        out = backend.generate_garment(b"\x89PNGfabric", "shirt", "casual", None)

    assert out == img_bytes
    assert captured["url"] == "http://flux.test/v1/run"
    assert captured["headers"]["Authorization"] == "Bearer sk-1"
    body = captured["json"]
    assert body["task"] == "garment"
    assert body["model"] == "flux-dev"
    assert "prompt" in body and "fabric" in body["prompt"].lower()
    assert len(body["reference_images"]) == 1
    assert base64.b64decode(body["reference_images"][0]) == b"\x89PNGfabric"


def test_flux_backend_tryon_sends_person_and_garment():
    captured = {}
    img_bytes = b"\xff\xd8" + bytes(range(64)) * 4

    def fake_post(url, *, json=None, headers=None, timeout=None, **kw):
        captured["json"] = json
        return _Resp(200, {"image": base64.b64encode(img_bytes).decode()})

    backend = FluxImageGenBackend(endpoint="http://flux.test/v1/run")
    with patch("app.services.image_gen.httpx.post", side_effect=fake_post):
        out = backend.generate_tryon(b"PERSON", b"GARMENT", "shirt", "casual", None)

    assert out == img_bytes
    body = captured["json"]
    assert body["task"] == "tryon"
    assert [len(base64.b64decode(x)) for x in body["reference_images"]] == [6, 7]


def test_flux_backend_http_error():
    backend = FluxImageGenBackend(endpoint="http://flux.test/v1/run")
    with patch("app.services.image_gen.httpx.post", return_value=_Resp(503, {"error": "busy"})):
        with pytest.raises(ImageGenAPIError):
            backend.generate_garment(b"f", "shirt", "casual", None)


def test_flux_backend_missing_image_field():
    backend = FluxImageGenBackend(endpoint="http://flux.test/v1/run")
    with patch("app.services.image_gen.httpx.post", return_value=_Resp(200, {"ok": True})):
        with pytest.raises(ImageGenAPIError):
            backend.generate_tryon(b"p", b"g", "shirt", "casual", None)


def test_flux_backend_accepts_raw_image_bytes_response():
    raw = b"RAW-PNG-DATA" * 20
    backend = FluxImageGenBackend(endpoint="http://flux.test/v1/run")
    with patch(
        "app.services.image_gen.httpx.post",
        return_value=_Resp(200, content=raw, content_type="image/png"),
    ):
        out = backend.generate_garment(b"f", "shirt", "casual", None)
    assert out == raw


def test_openrouter_backend_uses_standard_qwen_model_and_single_output():
    backend = OpenRouterImageGenBackend(api_key="sk-1")
    assert backend.model == "qwen/qwen-image-3"
    assert backend.fallback_model == ""

    captured = {}
    img_bytes = b"IMG" + bytes(range(50))

    def fake_post(url, *, json=None, headers=None, timeout=None, **kw):
        captured["json"] = json
        return _Resp(200, {"data": [{"b64_json": base64.b64encode(img_bytes).decode()}]})

    with patch("app.services.image_gen.httpx.post", side_effect=fake_post):
        out = backend.generate_tryon(b"person", b"garment", "shirt", "casual", None)

    assert out == img_bytes
    assert captured["json"]["model"] == "qwen/qwen-image-3"
    assert captured["json"]["num_images"] == 1
    assert len(captured["json"]["input_references"]) == 2


def test_openrouter_no_automatic_fallback_by_default():
    """The model-404 fallback must be OFF unless a fallback is explicitly set.

    Normal requests must never silently upgrade to a more expensive model.
    """
    backend = OpenRouterImageGenBackend(api_key="sk-1", model="qwen/qwen-image-3")
    assert backend.fallback_model == ""
    assert backend._should_fallback(
        Exception("Model not found")
    ) is False


def test_openrouter_fallback_only_when_explicitly_configured():
    """An explicitly configured fallback still works, but only in that case."""
    backend = OpenRouterImageGenBackend(
        api_key="sk-1",
        model="qwen/qwen-image-3",
        fallback_model="qwen/qwen-image-3-pro",
    )
    assert backend.fallback_model == "qwen/qwen-image-3-pro"
    assert backend._should_fallback(Exception("Model not found")) is True
    assert backend.model != backend.fallback_model


# --- OpenAI backend ---------------------------------------------------------

def test_openai_backend_fails_honestly_when_unconfigured():
    backend = OpenAIImageGenBackend(api_key="")
    with pytest.raises(ImageGenNotConfigured):
        backend.generate_garment(b"fabric", "shirt", "casual", None)


def test_openai_backend_posts_expected_payload():
    captured = {}
    img_bytes = b"\x89PNG" + bytes(range(64)) * 4

    def fake_post(url, *, data=None, files=None, headers=None, timeout=None, **kw):
        captured["url"] = url
        captured["data"] = data
        captured["files"] = files
        captured["headers"] = headers
        return _Resp(200, {"data": [{"b64_json": base64.b64encode(img_bytes).decode()}]})

    backend = OpenAIImageGenBackend(api_key="sk-openai", aspect_ratio="3:4")
    with patch("app.services.image_gen.httpx.post", side_effect=fake_post):
        out = backend.generate_garment(b"\xff\xd8fabric", "shirt", "casual", None)

    assert out == img_bytes
    assert captured["url"] == "https://api.openai.com/v1/images/edits"
    assert captured["headers"]["Authorization"] == "Bearer sk-openai"
    assert captured["headers"].get("Content-Type") is None  # multipart sets its own
    body = captured["data"]
    assert body["model"] == "gpt-image-2"
    assert body["size"] == "1024x1536"          # 3:4 aspect
    assert body["quality"] == "high"
    assert "prompt" in body and "fabric" in body["prompt"].lower()
    parts = list(captured["files"])
    assert len(parts) == 1
    field, file = parts[0]
    assert field == "image[]"
    assert file[2] == "image/png"               # content_type required
    assert file[1] == b"\xff\xd8fabric"


def test_openai_backend_tryon_sends_person_and_garment():
    captured = {}
    img_bytes = b"\x89PNG" + bytes(range(64)) * 4

    def fake_post(url, *, data=None, files=None, headers=None, timeout=None, **kw):
        captured["data"] = data
        captured["files"] = list(files)
        return _Resp(200, {"data": [{"b64_json": base64.b64encode(img_bytes).decode()}]})

    backend = OpenAIImageGenBackend(api_key="sk-openai")
    with patch("app.services.image_gen.httpx.post", side_effect=fake_post):
        out = backend.generate_tryon(b"PERSON", b"GARMENT", "shirt", "casual", None)

    assert out == img_bytes
    names = [f[1][0] for f in captured["files"]]
    assert names == ["person.png", "garment.png"]
    assert [f[1][1] for f in captured["files"]] == [b"PERSON", b"GARMENT"]
    assert captured["data"]["input_fidelity"] == "high"
    assert len(captured["files"]) == 2


def test_openai_backend_api_error_with_message():
    backend = OpenAIImageGenBackend(api_key="sk-openai")
    with patch(
        "app.services.image_gen.httpx.post",
        return_value=_Resp(400, {"error": {"message": "unsafe prompt"}}),
    ):
        with pytest.raises(ImageGenAPIError) as exc_info:
            backend.generate_garment(b"f", "shirt", "casual", None)
    assert "400" in str(exc_info.value) and "unsafe prompt" in str(exc_info.value)


def test_openai_backend_missing_image_data():
    backend = OpenAIImageGenBackend(api_key="sk-openai")
    with patch(
        "app.services.image_gen.httpx.post",
        return_value=_Resp(200, {"data": [{"revised_prompt": "nope"}]}),
    ):
        with pytest.raises(ImageGenAPIError):
            backend.generate_tryon(b"p", b"g", "shirt", "casual", None)