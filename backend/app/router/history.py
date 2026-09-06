import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, aliased

from ..database import get_db
from ..deps import get_current_user
from ..models import MediaAsset, TryOnJob, TryOnResult, User
from ..schemas import HistoryItemOut

router = APIRouter(prefix="/history", tags=["history"])


def _item(job: TryOnJob, result: TryOnResult, person: MediaAsset, fabric: MediaAsset) -> HistoryItemOut:
    return HistoryItemOut(
        id=result.id,
        job_id=job.id,
        person_image_url=person.url,
        fabric_image_url=fabric.url,
        result_url=result.result_url,
        garment_type=job.garment_type,
        garment_style=job.garment_style,
        gender=job.gender,
        created_at=result.created_at,
    )


@router.get("", response_model=list[HistoryItemOut])
def list_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    person = aliased(MediaAsset)
    fabric = aliased(MediaAsset)
    rows = (
        db.query(TryOnJob, TryOnResult, person, fabric)
        .join(TryOnResult, TryOnResult.try_on_job_id == TryOnJob.id)
        .join(person, person.id == TryOnJob.person_image_id)
        .join(fabric, fabric.id == TryOnJob.fabric_image_id)
        .filter(TryOnJob.user_id == user.id, TryOnJob.status == "COMPLETED")
        .order_by(TryOnResult.created_at.desc())
        .all()
    )
    return [_item(job, result, person, fabric) for job, result, person, fabric in rows]


@router.get("/{history_id}", response_model=HistoryItemOut)
def get_history(history_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        history_uuid = uuid.UUID(history_id)
    except ValueError:
        raise HTTPException(status_code=404, detail={"code": "HISTORY_NOT_FOUND", "message": "History item not found."})
    person = aliased(MediaAsset)
    fabric = aliased(MediaAsset)
    row = (
        db.query(TryOnJob, TryOnResult, person, fabric)
        .join(TryOnResult, TryOnResult.try_on_job_id == TryOnJob.id)
        .join(person, person.id == TryOnJob.person_image_id)
        .join(fabric, fabric.id == TryOnJob.fabric_image_id)
        .filter(TryOnResult.id == history_uuid, TryOnJob.user_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "HISTORY_NOT_FOUND", "message": "History item not found."})
    return _item(*row)