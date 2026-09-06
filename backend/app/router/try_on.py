from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import MediaAsset, TryOnJob, TryOnResult, User
from ..schemas import TryOnCreate, TryOnJobOut, TryOnResultOut
from ..services.try_on_provider import get_provider
from ..services.credits import reserve_try_on_credit
from ..worker.tasks import process_try_on_job
from ..config import settings

router = APIRouter(prefix="/try-on", tags=["try-on"])


@router.post("", response_model=TryOnJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_try_on(
    payload: TryOnCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    print(
        f"[TRYON][job_id=pending][API] Job create request"
        f" person_image_id={payload.person_image_id}"
        f" fabric_image_id={payload.fabric_image_id}"
        f" garment_type={payload.garment_type!r}"
        f" garment_style={payload.garment_style!r}"
        f" user_id={user.id}"
    )
    # Validate that both image assets exist and belong to this user.
    person = (
        db.query(MediaAsset)
        .filter(MediaAsset.id == payload.person_image_id, MediaAsset.user_id == user.id)
        .first()
    )
    fabric = (
        db.query(MediaAsset)
        .filter(MediaAsset.id == payload.fabric_image_id, MediaAsset.user_id == user.id)
        .first()
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer photo is required.",
        )
    if fabric is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cloth or garment image is required.",
        )

    existing = (
        db.query(TryOnJob)
        .filter(
            TryOnJob.user_id == user.id,
            TryOnJob.person_image_id == person.id,
            TryOnJob.fabric_image_id == fabric.id,
            TryOnJob.garment_type == payload.garment_type,
            TryOnJob.garment_style == payload.garment_style,
            TryOnJob.gender == payload.gender,
            TryOnJob.status.in_(["QUEUED", "PROCESSING"]),
        )
        .order_by(TryOnJob.created_at.desc())
        .first()
    )
    if existing is not None:
        print(f"[TRYON][job_id={existing.id}][API] Returning existing in-flight job to prevent duplicate generation.", flush=True)
        return _job_to_schema(existing, db)

    job = TryOnJob(
        user_id=user.id,
        person_image_id=person.id,
        fabric_image_id=fabric.id,
        garment_type=payload.garment_type,
        garment_style=payload.garment_style,
        gender=payload.gender,
        status="QUEUED",
        provider=get_provider().provider_name,
    )
    db.add(job)
    db.flush()
    reserve_try_on_credit(db, user.id, str(job.id))
    db.commit()
    db.refresh(job)
    print(f"[TRYON][job_id={job.id}][API] Job created status={job.status} user_id={user.id}", flush=True)

    try:
        process_try_on_job.delay(str(job.id))
        print(
            f"[QUEUE] Job enqueued job_id={job.id} "
            f"queue=vastrai.tryon broker={settings.celery_broker_url}",
            flush=True,
        )
    except Exception:
        # If the broker is unavailable, mark the job failed so it is visible.
        job.status = "FAILED"
        job.error_message = "We couldn't create your look. Please try again."
        db.commit()

    return _job_to_schema(job, db)


def _job_to_schema(job: TryOnJob, db: Session) -> TryOnJobOut:
    result_url = None
    result_image_id = None
    result = db.query(TryOnResult).filter(TryOnResult.try_on_job_id == job.id).first()
    if result:
        result_url = result.result_url
        result_image_id = result.result_image_id
    return TryOnJobOut(
        id=job.id,
        user_id=job.user_id,
        person_image_id=job.person_image_id,
        fabric_image_id=job.fabric_image_id,
        garment_type=job.garment_type,
        garment_style=job.garment_style,
        gender=job.gender,
        status=job.status,
        error_message=job.error_message,
        provider=job.provider,
        model_version=job.model_version,
        result_url=result_url,
        result_image_id=result_image_id,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def _get_job_or_404(db: Session, job_id: str, user: User) -> TryOnJob:
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Try-on job not found.")
    job = db.query(TryOnJob).filter(TryOnJob.id == uid, TryOnJob.user_id == user.id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Try-on job not found.")
    return job


@router.get("/{job_id}", response_model=TryOnJobOut)
def get_job(job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = _get_job_or_404(db, job_id, user)
    print(f"[TRYON][job_id={job.id}][API] Status response status={job.status}", flush=True)
    return _job_to_schema(job, db)


@router.get("/{job_id}/result", response_model=TryOnResultOut)
def get_result(
    job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    job = _get_job_or_404(db, job_id, user)
    result = db.query(TryOnResult).filter(TryOnResult.try_on_job_id == job.id).first()
    if result is None or job.status != "COMPLETED":
        print(f"[TRYON][job_id={job.id}][API] Result not ready status={job.status}", flush=True)
        raise HTTPException(status_code=404, detail="Result not ready yet.")
    print(f"[TRYON][job_id={job.id}][API] Result response URL present={bool(result.result_url)}", flush=True)
    return TryOnResultOut.model_validate(result)