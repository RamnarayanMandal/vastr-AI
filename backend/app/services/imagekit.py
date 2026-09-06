from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Optional

import httpx

from ..config import settings


def _auth_header() -> dict:
    """Server side signature for ImageKit image endpoint."""
    # If private credentials present, authenticate with basic auth.
    headers = {}
    if settings.imagekit_use_private and settings.imagekit_private_key:
        cred = f"{settings.imagekit_public_key}:{settings.imagekit_private_key}"
        headers["Authorization"] = "Basic " + base64.b64encode(cred.encode()).decode()
    return headers


def generate_client_upload_token() -> dict:
    """Returns an upload token the mobile client can use for direct upload.

    NOTE: This token approach requires ImageKit public/private key config.
    The reference implementation keeps server-side signing minimal.
    """
    return {
        "token": "",
        "expire": str(int(time.time()) + 600),
        "signature": "",
    }


def _ik_upload_base_url() -> str:
    return "https://upload.imagekit.io/api/v1/files/upload"


def upload_bytes(
    data: bytes,
    filename: str,
    folder: str,
    use_file_name: bool = True,
) -> Optional[dict]:
    """Upload raw image bytes to ImageKit and return { fileId, url } or None.

    The underlying ``imagekitio`` SDK (v4.x) corrupts raw ``bytes`` uploads:
    its ``File.upload`` maps ``isinstance(file, bytes)`` to a malformed
    multipart field ``(None, file)``, so the actual image bytes never reach
    ImageKit (the stored file ends up a few hundred bytes of garbage that no
    image decoder can open).  To guarantee byte-for-byte correctness we call
    the ImageKit upload REST API directly with ``httpx`` using a proper
    multipart file field ``(filename, BytesIO(data), content_type)``.
    """
    import io
    import mimetypes
    import logging

    if not (settings.imagekit_public_key and settings.imagekit_private_key):
        return None  # not configured
    if not data:
        return None

    # Authenticate exactly like the SDK: HTTP Basic with base64(private_key + ":").
    import base64

    cred = base64.b64encode(
        (settings.imagekit_private_key + ":").encode("utf-8")
    ).decode("ascii")

    content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
    files = {
        "file": (filename, io.BytesIO(data), content_type),
    }
    fields = {
        "fileName": filename,
        "useUniqueFileName": "true",
    }
    if folder:
        fields["folder"] = folder.rstrip("/")

    try:
        resp = httpx.post(
            _ik_upload_base_url(),
            data=fields,
            files=files,
            headers={
                "Authorization": f"Basic {cred}",
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=180.0,
        )
    except httpx.HTTPError as exc:
        logging.warning("ImageKit upload request failed: %s", exc)
        return None

    if resp.status_code != 200:
        logging.warning(
            "ImageKit upload failed: status=%s body=%s",
            resp.status_code,
            resp.text[:300],
        )
        return None

    try:
        result = resp.json()
    except ValueError:
        logging.warning("ImageKit upload returned unparseable JSON.")
        return None

    file_id = result.get("fileId") or result.get("file_id")
    url = result.get("url")
    if not file_id or not url:
        logging.warning("ImageKit upload response missing fileId/url: %s", result)
        return None
    return {"fileId": file_id, "url": url}


def download_url(url: str) -> Optional[bytes]:
    """Download an image from a URL (used to fetch the AI result for storage).

    Also resolves local ``/local_uploads/...`` URLs stored when ImageKit was
    unavailable at upload time.  Supports both the flat legacy layout
    (``/local_uploads/<name>``) and the organised per-kind layout
    (``/local_uploads/<person|fabric|result>/<name>``).
    """
    if url.startswith("/local_uploads/"):
        from ..router.uploads import LOCAL_DIR

        rel = url[len("/local_uploads/"):].lstrip("/")
        parts = rel.split("/")
        if len(parts) == 2 and parts[0] in ("person", "fabric", "result", "misc"):
            path = os.path.join(LOCAL_DIR, parts[0], parts[1])
        else:
            # Legacy flat layout: the whole remainder is the filename.
            path = os.path.join(LOCAL_DIR, os.path.basename(rel))
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except OSError:
            return None
    try:
        resp = httpx.get(url, timeout=60)
        if resp.status_code == 200:
            return resp.content
    except Exception:
        return None
    return None


def generate_mock_result_bytes() -> bytes:
    """Produce a small placeholder image byte blob used by the mock provider."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (256, 384), (13, 11, 26))
    d = ImageDraw.Draw(img)
    d.rectangle([24, 120, 232, 300], fill=(201, 169, 106))
    img_bytes = __import__("io").BytesIO()
    img.save(img_bytes, format="JPEG")
    return img_bytes.getvalue()