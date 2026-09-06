import base64

import pytest
from unittest.mock import patch

from app.services import gemini
from app.services.gemini import (
    GeminiAPIError,
    GeminiNotConfigured,
    _build_payload,
    _mime_type,
    garment_prompts,
    generate_image,
)


def test_build_payload_has_images_and_prompt():
    img = b"\xff\xd8\xff" + b"\x00" * 32  # jpeg-ish
    payload = _build_payload("make a shirt", [img, img])
    parts = payload["contents"][0]["parts"]
    # 2 inline images + 1 text
    assert len(parts) == 3
    assert parts[0]["inline_data"]["mime_type"] == "image/jpeg"
    assert base64.b64decode(parts[0]["inline_data"]["data"]) == img
    assert parts[-1]["text"] == "make a shirt"
    cfg = payload["generationConfig"]
    assert cfg["responseModalities"] == ["TEXT", "IMAGE"]


def test_mime_type_sniffs_jpeg_and_png():
    assert _mime_type(b"\xff\xd8\xff\xe0....") == "image/jpeg"
    assert _mime_type(b"\x89PNG\r\n\x1a\n....") == "image/png"
    assert _mime_type(b"\x00\x01\x02") == "image/jpeg"


def test_generate_image_requires_key():
    with pytest.raises(GeminiNotConfigured):
        generate_image("make a shirt")


def test_generate_image_returns_bytes(mock_http_response):
    images = _build_payload("x", [])
    resp_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "ok"},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": base64.b64encode(b"PNG-IMAGE").decode(),
                            }
                        },
                    ]
                }
            }
        ]
    }
    with patch("app.services.gemini.httpx.post", return_value=mock_http_response(200, resp_json)):
        out = generate_image("make a shirt", api_key="k", model="m", base_url="http://x/v1beta")
    assert out == b"PNG-IMAGE"


def test_generate_image_no_image_raises(mock_http_response):
    resp_json = {"candidates": [{"content": {"parts": [{"text": "sorry"}]}}]}
    with patch("app.services.gemini.httpx.post", return_value=mock_http_response(200, resp_json)):
        with pytest.raises(GeminiAPIError):
            generate_image("make a shirt", api_key="k", model="m", base_url="http://x/v1beta")


def test_generate_image_http_error(mock_http_response):
    with patch("app.services.gemini.httpx.post", return_value=mock_http_response(429, {"error": "busy"})):
        with pytest.raises(GeminiAPIError):
            generate_image("make a shirt", api_key="k", model="m", base_url="http://x/v1beta")


def test_garment_prompts_are_distinct():
    p = garment_prompts("shirt", "casual", None)
    assert "garment" in p and "tryon" in p
    assert p["garment"] != p["tryon"]
    assert "fabric" in p["garment"].lower()