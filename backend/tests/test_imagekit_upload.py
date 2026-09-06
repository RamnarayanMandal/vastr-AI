"""Tests for the ImageKit upload fix.

Root cause: ``imagekitio`` v4.x corrupts raw ``bytes`` uploads (its multipart
field becomes ``(None, bytes)``), so files stored on ImageKit were a few
hundred bytes of garbage that no image decoder could open.  The fixed
``upload_bytes`` calls the ImageKit REST API directly with a correct multipart
file field and returns ``{fileId, url}``.
"""

import io

import pytest
from PIL import Image

from app.services import imagekit
from app.services.imagekit import upload_bytes


def _jpeg_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (201, 169, 106)).save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (13, 11, 26)).save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _not_configured():
    return not (imagekit.settings.imagekit_public_key and imagekit.settings.imagekit_private_key)


@pytest.fixture()
def fake_ik_response():
    """Mock the ImageKit REST call: capture the request and echo a success body."""
    captured = {}

    class _FakeResp:
        status_code = 200

        def json(self):
            return {"fileId": "fake-file-id-123", "url": "https://ik.imagekit.io/x/person/pic.jpg"}

    def _post(url, data, files, headers, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["files"] = files
        captured["headers"] = headers
        return _FakeResp()

    monkey_patch = pytest.MonkeyPatch()
    monkey_patch.setattr(imagekit.httpx, "post", _post)
    yield captured
    monkey_patch.undo()


def test_upload_bytes_returns_fileid_and_url(fake_ik_response):
    if _not_configured():
        pytest.skip("ImageKit not configured")
    result = upload_bytes(_jpeg_bytes(), "pic.jpg", "/vastrai/person/")
    assert result == {"fileId": "fake-file-id-123", "url": "https://ik.imagekit.io/x/person/pic.jpg"}


def test_upload_bytes_sends_multipart_file_field(fake_ik_response):
    """The single biggest regression guard: the file must be a 3-tuple multipart
    upload ``(filename, BytesIO, content_type)``, NOT the SDK's ``(None, bytes)``
    that silently corrupts the image."""
    if _not_configured():
        pytest.skip("ImageKit not configured")
    upload_bytes(_jpeg_bytes(), "pic.jpg", "/vastrai/person/")
    files = fake_ik_response["files"]
    assert "file" in files
    name, fileobj, ctype = files["file"]
    assert name == "pic.jpg"
    assert hasattr(fileobj, "read")  # a file-like object, not raw bytes as value
    assert ctype == "image/jpeg"
    # The exact bytes must round-trip through the BytesIO that is sent.
    assert fileobj.read() == _jpeg_bytes()


def test_upload_bytes_uses_basic_auth(fake_ik_response):
    if _not_configured():
        pytest.skip("ImageKit not configured")
    upload_bytes(_png_bytes(), "fabric.png", "/vastrai/fabric/")
    headers = fake_ik_response["headers"]
    assert headers["Authorization"].startswith("Basic ")
    assert fake_ik_response["data"]["fileName"] == "fabric.png"


def test_upload_bytes_empty_data_returns_none():
    assert upload_bytes(b"", "x.png", "/vastrai/person/") is None


def test_upload_bytes_not_configured_returns_none(monkeypatch):
    monkeypatch.setattr(imagekit.settings, "imagekit_public_key", "")
    monkeypatch.setattr(imagekit.settings, "imagekit_private_key", "")
    assert upload_bytes(_png_bytes(), "x.png", "/vastrai/person/") is None
