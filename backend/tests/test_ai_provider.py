"""Tests for the LangChain-backed AI provider abstraction (ai_provider.py)."""

import base64
import io

import pytest
from PIL import Image

from app.services.ai_provider import (
    AIProviderNotConfigured,
    GeminiImageProvider,
    OpenAIImageProvider,
    get_ai_provider,
)


def _png(color=(58, 131, 200), size=(256, 256)) -> bytes:
    im = Image.new("RGB", size, color)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


class _FakeImages:
    def __init__(self, edit_fn):
        self._edit = edit_fn

    def edit(self, **kw):
        return self._edit(**kw)


class _FakeClient:
    def __init__(self, edit_fn):
        self.images = _FakeImages(edit_fn)


def test_openai_provider_fails_honestly_when_unconfigured():
    provider = OpenAIImageProvider(api_key="")
    with pytest.raises(AIProviderNotConfigured):
        provider.generate_garment(b"fabric", "shirt", "casual", None)
    with pytest.raises(AIProviderNotConfigured):
        provider.generate_tryon(b"person", b"garment", "shirt", "casual", None)


def test_openai_provider_uses_langchain_prompt_and_returns_image(monkeypatch):
    fabric = _png(color=(58, 131, 200))
    garment_out = _png(color=(90, 90, 90))
    tryon_out = _png(color=(120, 120, 120), size=(320, 400))

    calls = {}

    class FakeResultItem:
        b64_json = None

    def fake_edit(*, model, prompt, image, size, quality, output_format, input_fidelity):
        calls["prompt"] = prompt
        calls["model"] = model
        calls["size"] = size
        calls["input_fidelity"] = input_fidelity
        n = len(list(image))
        out = garment_out if n == 1 else tryon_out
        item = FakeResultItem()
        item.b64_json = base64.b64encode(out).decode()
        resp = type("R", (), {"data": [item]})()
        return resp

    import openai as openai_pkg

    monkeypatch.setattr(openai_pkg, "OpenAI", lambda *a, **k: _FakeClient(fake_edit))

    provider = OpenAIImageProvider(api_key="sk-test", model="gpt-image-2")
    garment = provider.generate_garment(fabric, "shirt", "casual", {"dominant_hex": "#0d0b1a"})
    assert garment == garment_out
    assert calls["model"] == "gpt-image-2"
    assert calls["size"] == "1024x1536"
    assert calls["input_fidelity"] == "high"
    assert "shirt" in calls["prompt"]
    assert "#0d0b1a" in calls["prompt"]

    person = _png(color=(235, 228, 218), size=(320, 400))
    tryon = provider.generate_tryon(person, garment, "shirt", "casual", None)
    assert tryon == tryon_out
    assert calls["prompt"] != ""  # try-on prompt differs


def test_get_ai_provider_resolves_openai_and_gemini():
    provider = get_ai_provider("openai")
    assert isinstance(provider, OpenAIImageProvider)
    assert provider.model_tag == "gpt-image-2"

    gemini = get_ai_provider("gemini")
    assert isinstance(gemini, GeminiImageProvider)
