from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Callable

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal, get_db
from ..deps import get_current_user
from ..models import MediaAsset, TryOnJob, TryOnResult, User
from ..schemas import TryOnCreate, TryOnJobOut, TryOnResultOut
from ..services.credits import reserve_try_on_credit
from ..services.perf import ago_ms, perf
from ..services.try_on_provider import get_provider
from ..worker.celery_app import celery_app
from ..worker.tasks import process_try_on_job

router = APIRouter(prefix="/try-on", tags=["try-on"])

MAX_ENQUEUE_RETRIES = 4
ENQUEUE_BACKOFF_BASE = 0.5
ENQUEUE_BACKOFF_FACTOR = 2.0
ENQUEUE_BACKOFF_MAX = 5.0
BACKGROUND_ENQUEUE_RETRIES = 6
BACKGROUND_ENQUEUE_BACKOFF_BASE = 2.0

_ENQUEUE_FAILED_MESSAGE = "We couldn't create your look right now. Please try again in a moment."


def _enqueue_backoff(attempt: int) -> float:
    """Exponential backoff in seconds for enqueue attempt ``attempt``."""
    return min(ENQUEUE_BACKOFF_MAX, ENQUEUE_BACKOFF_BASE * (ENQUEUE_BACKOFF_FACTOR ** (attempt - 1)))


def _sleep_backoff(seconds: float) -> None:
    time.sleep(seconds)


def _enqueue_once(job_id: str, attempt: int | None = None) -> None:
    """Publish the Celery task on a BRAND-NEW broker connection.

    The managed Redis provider drops idle pooled sockets, so reuse of a stale
    pooled connection re-fails publishing on every retry. A fresh connection
    per attempt (via ``apply_async(connection=...)``) sidesteps the producer
    pool entirely; ``conn.close()`` tears it down after the publish.
    """
    started = time.perf_counter()
    if attempt is not None:
        perf("celery_publish_start", job_id=job_id, attempt=attempt)
    conn = celery_app.connection()
    try:
        process_try_on_job.apply_async(args=[job_id], connection=conn)
        if attempt is not None:
            perf("celery_publish_end", job_id=job_id, attempt=attempt, duration_ms=ago_ms(started))
    finally:
        conn.close()


def _enqueue_job(
    job_id: str,
    max_attempts: int = MAX_ENQUEUE_RETRIES,
    _sleep: Callable[[float], None] | None = None,
) -> dict:
    """Deliver the Celery task, retrying transient broker failures.

    Never raises: a broker outage here must not destroy a freshly created job.
    Returns ``{"ok": bool, "attempts": int, "error": str | None}`` so callers
    decide whether to leave the job QUEUED (retryable) for the background loop.
    """
    _sleep = _sleep or _sleep_backoff
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        print(f"[QUEUE] enqueue attempt={attempt} job_id={job_id}", flush=True)
        try:
            _enqueue_once(job_id, attempt=attempt)
            print(f"[QUEUE] enqueue successful job_id={job_id}", flush=True)
            return {"ok": True, "attempts": attempt, "error": None}
        except Exception as exc:  # noqa: BLE001 - broker/kombu connection errors
            last_error = exc
            print(
                f"[QUEUE] broker connection failed job_id={job_id} "
                f"error={type(exc).__name__}: {exc}",
                flush=True,
            )
            if attempt < max_attempts:
                backoff = _enqueue_backoff(attempt)
                print(f"[QUEUE] reconnecting job_id={job_id} backoff={backoff:.1f}s", flush=True)
                _sleep(backoff)
    detail = f"{type(last_error).__name__}: {last_error}" if last_error else "unknown"
    print(
        f"[QUEUE] enqueue retries exhausted job_id={job_id} "
        f"attempts={max_attempts} error={detail}",
        flush=True,
    )
    return {"ok": False, "attempts": max_attempts, "error": detail}


def _retry_enqueue_loop(
    job_id: str,
    db_factory: Callable[[], Session] = SessionLocal,
    _sleep: Callable[[float], None] | None = None,
) -> None:
    """Background enqueue retry with exponential backoff.

    Runs after the HTTP response. Keeps re-publishing the same job with a fresh
    connection per attempt; once the broker recovers the worker picks the
    QUEUED job up normally. Bounded: if the broker stays down long enough, the
    job is marked FAILED so the client is never left polling a QUEUED job
    forever.
    """
    _sleep = _sleep or _sleep_backoff
    for attempt in range(1, BACKGROUND_ENQUEUE_RETRIES + 1):
        backoff = min(ENQUEUE_BACKOFF_MAX, BACKGROUND_ENQUEUE_BACKOFF_BASE * (2 ** (attempt - 1)))
        _sleep(backoff)
        try:
            _enqueue_once(job_id)
            print(
                f"[QUEUE] enqueue successful job_id={job_id} (background attempt={attempt})",
                flush=True,
            )
            return
        except Exception as exc:  # noqa: BLE001 - broker/kombu connection errors
            print(
                f"[QUEUE] broker connection failed job_id={job_id}"
                f" (background attempt={attempt}) error={type(exc).__name__}: {exc}",
                flush=True,
            )
    print(
        f"[QUEUE] background enqueue retries exhausted job_id={job_id}"
        f" attempts={BACKGROUND_ENQUEUE_RETRIES}",
        flush=True,
    )
    _mark_enqueue_failed(job_id, db_factory=db_factory)


def _mark_enqueue_failed(
    job_id: str,
    message: str = _ENQUEUE_FAILED_MESSAGE,
    db_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """Mark a job FAILED after enqueue retries are exhausted.

    Uses a fresh session because the request session is gone by the time the
    background work runs. Only touches jobs still QUEUED so it can never
    overwrite a job the worker already finished. The user-facing message stays
    the same; internal broker details live in the logs only.
    """
    db = db_factory()
    try:
        job = db.query(TryOnJob).filter(TryOnJob.id == uuid.UUID(job_id)).first()
        if job is None or job.status != "QUEUED":
            return
        job.status = "FAILED"
        job.error_message = message
        job.completed_at = datetime.utcnow()
        db.commit()
        print(f"[TRYON][job_id={job_id}][API] Enqueue retries exhausted -> FAILED", flush=True)
    finally:
        db.close()


@router.post("", response_model=TryOnJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_try_on(
    payload: TryOnCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    req_started = time.perf_counter()
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
    perf(
        "job_created",
        job_id=str(job.id),
        duration_ms=ago_ms(req_started),
        person_image_id=str(person.id),
        fabric_image_id=str(fabric.id),
    )

    enq_started = time.perf_counter()
    perf("celery_enqueue_start", job_id=str(job.id))
    enqueue = _enqueue_job(str(job.id))
    perf(
        "celery_enqueue_end",
        job_id=str(job.id),
        duration_ms=ago_ms(enq_started),
        ok=str(enqueue["ok"]).lower(),
        attempts=enqueue["attempts"],
    )
    if enqueue["ok"]:
        print(
            f"[QUEUE] Job enqueued job_id={job.id} "
            f"queue=vastrai.tryon broker={settings.celery_broker_url}",
            flush=True,
        )
    else:
        # Broker is down after the in-request retries: keep the job QUEUED
        # (retryable) instead of permanently failing it, record how far the
        # synchronous retries got, and hand the job to a bounded background
        # retry loop. The loop re-publishes with backoff and only marks the
        # job FAILED (with a user-safe message) once it gives up.
        job.retry_count = enqueue["attempts"]
        db.commit()
        background_tasks.add_task(_retry_enqueue_loop, str(job.id))
        print(
            f"[QUEUE] Enqueue deferred job_id={job.id} "
            f"attempts={enqueue['attempts']} error={enqueue['error']}",
            flush=True,
        )

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
    started = time.perf_counter()
    job = _get_job_or_404(db, job_id, user)
    print(f"[TRYON][job_id={job.id}][API] Status response status={job.status}", flush=True)
    perf("job_status_response", job_id=str(job.id), duration_ms=ago_ms(started), status=job.status)
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