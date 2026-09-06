import io

from PIL import Image


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


def _decoy_pdf_bytes():
    return b"%PDF-1.0 some fake pdf content that is not a real image"


def test_upload_person_success(client, auth_headers):
    headers, _ = auth_headers
    resp = client.post(
        "/api/v1/upload/person",
        files={"file": ("photo.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["image_id"]
    assert body["url"]


def test_upload_fabric_success(client, auth_headers):
    headers, _ = auth_headers
    resp = client.post(
        "/api/v1/upload/fabric",
        files={"file": ("fabric.png", io.BytesIO(_png_bytes()), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["image_id"]


def test_upload_invalid_filetype(client, auth_headers):
    headers, _ = auth_headers
    resp = client.post(
        "/api/v1/upload/person",
        files={"file": ("doc.pdf", io.BytesIO(_decoy_pdf_bytes()), "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_upload_corrupt_image_rejected(client, auth_headers):
    headers, _ = auth_headers
    # Declared as jpeg but bytes are not decodeable -> must be rejected by Pillow.
    resp = client.post(
        "/api/v1/upload/person",
        files={"file": ("bad.jpg", io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100), "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_upload_empty_file_rejected(client, auth_headers):
    headers, _ = auth_headers
    resp = client.post(
        "/api/v1/upload/person",
        files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_upload_too_large(client, auth_headers):
    headers, _ = auth_headers
    big = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * (16 * 1024 * 1024))
    resp = client.post(
        "/api/v1/upload/person",
        files={"file": ("huge.jpg", big, "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 413


def test_upload_unauthenticated(client):
    resp = client.post(
        "/api/v1/upload/person",
        files={"file": ("pic.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
    )
    assert resp.status_code == 401
