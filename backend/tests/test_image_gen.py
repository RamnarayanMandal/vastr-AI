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