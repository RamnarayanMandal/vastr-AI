from __future__ import annotations

import io
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import MediaAsset, User
from ..schemas import UploadResponse
from ..services.imagekit import upload_bytes

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/heic"}
MAX_BYTES = 15 * 1024 * 1024  # 15 MB

LOCAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "local_uploads",
)


def _validate_image_bytes(data: bytes, filename: str) -> None:
    """Reject decoys/garbage by confirming Pillow can decode the upload.

    Only *verifies* the bytes (Pillow ``verify()``); the user's image is not
    re-encoded or modified here, so no corruption is introduced.  This catches
    files whose declared content type lies (e.g. a PDF named ``.jpg``) before
    they reach ImageKit.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The file is not a valid image. Please upload a JPG, PNG or WEBP photo.",
        )


def _save_local(kind: str, ext: str, data: bytes, user_id: str) -> tuple:
    """Persist image bytes to a local file and return (path, filename).

    Fallback used when ImageKit is unavailable so the try-on pipeline always
    receives a real, downloadable image (never a broken placeholder URL).
    Files are organised into per-kind subfolders (person / fabric / result) so
    the media library stays structured even without ImageKit.
    """
    sub = kind if kind in ("person", "fabric", "result") else "misc"
    kind_dir = os.path.join(LOCAL_DIR, sub)
    os.makedirs(kind_dir, exist_ok=True)
    name = f"{kind}-{user_id}-{uuid.uuid4().hex[:12]}{ext}"
    path = os.path.join(kind_dir, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path, name


def _handle_upload(
    file: UploadFile,
    kind: str,
    folder: str,
    db: Session,
    user: User,
) -> UploadResponse:
    if file.content_type not in ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please use a clearer image (JPG, PNG, WEBP).",
        )
    data = file.file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is too large (max 15 MB).",
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )
    _validate_image_bytes(data, file.filename or f"{kind}.jpg")
    ext = ".jpg" if file.content_type == "image/jpeg" else ".png"
    uploaded = upload_bytes(data, f"{kind}{ext}", folder)
    if uploaded is None:
        # ImageKit unavailable: keep the real image so the pipeline still works.
        _path, name = _save_local(kind, ext, data, str(user.id))
        sub = kind if kind in ("person", "fabric", "result") else "misc"
        asset = MediaAsset(
            user_id=user.id,
            kind=kind,
            imagekit_file_id=f"local-{name}",
            url=f"/local_uploads/{sub}/{name}",
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return UploadResponse(image_id=asset.id, url=asset.url)

    asset = MediaAsset(
        user_id=user.id,
        kind=kind,
        imagekit_file_id=uploaded["fileId"],
        url=uploaded["url"],
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return UploadResponse(image_id=asset.id, url=asset.url)


@router.post("/person", response_model=UploadResponse)
def upload_person(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _handle_upload(file, "person", "/vastrai/person/", db, user)


@router.post("/fabric", response_model=UploadResponse)
def upload_fabric(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _handle_upload(file, "fabric", "/vastrai/fabric/", db, user)