from __future__ import annotations

import time as _time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import MediaAsset, TryOnJob, TryOnResult
from app.models import Notification
from app.services.perf import ago_ms, perf
from app.services.try_on_provider import (
    PermanentTryOnError,
    RetryableTryOnError,
    TryOnInput,
    get_provider,
)
from .celery_app import celery_app


def _status_log(job_id, status: str, note: str = "") -> None:
    suffix = f" | {note}" if note else ""
    print(
        f"[JOB] Status updated job_id={job_id} status={status}{suffix}",
        flush=True,
    )


def _utc_aware(dt) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _job_total_ms(created_at) -> float:
    """Wall-clock ms from job creation to now, treating DB timestamp as UTC."""
    return (datetime.now(timezone.utc) - _utc_aware(created_at)).total_seconds() * 1000.0


def _backoff(retries: int) -> int:
    """Exponential backoff in seconds, capped at retry_max_delay."""
    base = max(1, settings.retry_backoff_base)
    return min(settings.retry_max_delay, base * (2 ** retries))


def _user_message(exc: Exception) -> str:
    detail = (str(exc) or "").strip()
    if not detail:
        return "Your look could not be created. Please try again."
    return detail[:280]


_STALE_MESSAGE = "This try-on took too long and was cancelled. Please try again."


def recover_stale_jobs(db: Session | None = None) -> int:
    """Mark jobs stuck too long in QUEUED or PROCESSING as FAILED.

    A worker that dies mid-flight (or a broker that never delivered the task)
    would otherwise leave the client polling forever. Requires no scheduler:
    call it at worker startup and before each job claim.
    """
    _close = db is None
    db = db if db is not None else SessionLocal()
    try:
        now = datetime.utcnow()
        queue_cutoff = now - timedelta(seconds=settings.try_on_stale_queue_ttl)
        processing_cutoff = now - timedelta(
            seconds=settings.try_on_stale_processing_ttl
        )
        failed = 0
        stale_queued = (
            db.query(TryOnJob)
            .filter(
                TryOnJob.status == "QUEUED",
                TryOnJob.created_at < queue_cutoff,
            )
            .all()
        )
        for job in stale_queued:
            _fail(db, job.id, _STALE_MESSAGE)
            failed += 1
        stale_processing = (
            db.query(TryOnJob)
            .filter(
                TryOnJob.status == "PROCESSING",
                TryOnJob.started_at.isnot(None),
                TryOnJob.started_at < processing_cutoff,
            )
            .all()
        )
        for job in stale_processing:
            _fail(db, job.id, _STALE_MESSAGE)
            failed += 1
        if failed:
            print(f"[RECOVERY] Marked {failed} stale job(s) FAILED", flush=True)
        return failed
    finally:
        if _close:
            db.close()


def _claim_job(db: Session, job_id: uuid.UUID, provider_name: str) -> bool:
    """Atomically move a QUEUED job to PROCESSING.

    Returns False when another run already claimed this job or it reached a
    terminal state, which makes re-delivered retries idempotent.
    """
    updated = (
        db.query(TryOnJob)
        .filter(
            TryOnJob.id == job_id,
            TryOnJob.status == "QUEUED",
        )
        .update(
            {
                "status": "PROCESSING",
                "started_at": datetime.utcnow(),
                "provider": provider_name,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    if updated == 1:
        _status_log(job_id, "PROCESSING")
    return updated == 1


def _fail(db: Session, job_id: uuid.UUID, message: str) -> None:
    db.query(TryOnJob).filter(TryOnJob.id == job_id).update(
        {
            "status": "FAILED",
            "error_message": message,
            "completed_at": datetime.utcnow(),
        },
        synchronize_session=False,
    )
    job = db.query(TryOnJob).filter(TryOnJob.id == job_id).first()
    if job:
        db.add(Notification(user_id=job.user_id, title="Try-on failed", message=message[:280], type="TRY_ON_FAILED"))
    db.commit()
    _status_log(job_id, "FAILED", message[:280])
    print(f"[TRYON][job_id={job_id}][ERROR] {message[:280]}", flush=True)


def _fail_safe(db: Session, job_id: uuid.UUID, message: str) -> None:
    """Mark a job FAILED even when the worker's long-lived session died.

    Image generation takes minutes; managed Postgres poolers can drop the idle
    connection in between. If the write on ``db`` fails, reopen a fresh session
    and roll the failure state in so the client is never left polling forever.
    """
    try:
        _fail(db, job_id, message)
        return
    except Exception as exc:  # noqa: BLE001 - the same dropped-connection hazard
        print(
            f"[TASKS] Failure write failed on worker session"
            f" ({type(exc).__name__}: {exc}); using a fresh DB session",
            flush=True,
        )
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        try:
            db.close()
        except Exception:  # noqa: BLE001
            pass
    fresh = SessionLocal()
    try:
        _fail(fresh, job_id, message)
    finally:
        fresh.close()


def _reset_to_queued(db: Session, job_id: uuid.UUID) -> Session:
    """Move a job back to QUEUED for a Celery retry; return a usable session.

    Same dropped-connection hazard as ``_fail_safe``: fall back to a fresh
    session so the retried run can be re-claimed and the retry is not lost.
    """
    update = {
        "status": "QUEUED",
        "started_at": None,
        "retry_count": TryOnJob.retry_count + 1,
    }
    try:
        db.query(TryOnJob).filter(TryOnJob.id == job_id).update(update, synchronize_session=False)
        db.commit()
        return db
    except Exception as exc:  # noqa: BLE001 - the same dropped-connection hazard
        print(
            f"[TASKS] Reset-to-QUEUED failed on worker session"
            f" ({type(exc).__name__}: {exc}); using a fresh DB session",
            flush=True,
        )
        try:
            db.close()
        except Exception:  # noqa: BLE001
            pass
        fresh = SessionLocal()
        fresh.query(TryOnJob).filter(TryOnJob.id == job_id).update(update, synchronize_session=False)
        fresh.commit()
        return fresh


def _process_job(db: Session, uid: uuid.UUID) -> dict:
    job = db.query(TryOnJob).filter(TryOnJob.id == uid).first()
    if job is None:
        return {"status": "NOT_FOUND", "job_id": str(uid)}
    created_at = job.created_at

    provider = get_provider()
    print(f"[TASKS] Provider loaded: {provider.provider_name} | model: {provider.model_version}")
    claim_t = _time.perf_counter()
    claimed = _claim_job(db, uid, provider.provider_name)
    perf("job_claimed", job_id=str(uid), duration_ms=ago_ms(claim_t), ok=str(claimed).lower())
    if not claimed:
        # Already claimed by a concurrent run or in a terminal state.
        latest = db.query(TryOnJob.status).filter(TryOnJob.id == uid).first()
        return {"status": latest.status if latest else "UNKNOWN", "job_id": str(uid)}

    media_t = _time.perf_counter()
    person = db.query(MediaAsset).filter(MediaAsset.id == job.person_image_id).first()
    fabric = db.query(MediaAsset).filter(MediaAsset.id == job.fabric_image_id).first()
    perf("media_load", job_id=str(uid), duration_ms=ago_ms(media_t))
    if person is None or fabric is None:
        _fail(db, uid, "One of the images for this look is missing.")
        return {"status": "FAILED", "job_id": str(uid)}

    # LangGraph orchestration engine (AI_WORKFLOW_ENGINE=langgraph).
    if settings.workflow_engine == "langgraph":
        from app.services.workflow import run_workflow
        from app.services.image_gen import get_image_gen_backend

        # The LangGraph workflow nodes call generate_garment() / generate_tryon()
        # which live on ImageGenBackend (not VirtualTryOnProvider).  Pass the
        # actual backend so the nodes don't crash with AttributeError.
        try:
            backend = get_image_gen_backend()
        except Exception as exc:
            print(f"[TASKS] Failed to get image gen backend: {exc}")
            _fail(db, uid, f"AI backend not configured: {exc}")
            return {"status": "FAILED", "job_id": str(uid), "error_message": str(exc)[:280]}

        print(f"[TASKS] LangGraph path | job={uid} | backend={type(backend).__name__} | person={person.url} | fabric={fabric.url}")

        def saver(state) -> None:
            _save_langgraph_result(db, job, state)

        state = run_workflow(
            job_id=str(uid),
            person_image_url=person.url,
            fabric_image_url=fabric.url,
            garment_type=job.garment_type,
            garment_style=job.garment_style,
            gender=job.gender,
            provider=backend,
            saver=saver,
            max_retries=0,
        )
        print(f"[TASKS] LangGraph finished | job={uid} | status={state.get('status')} | error={state.get('error')}")

        if state.get("status") == "COMPLETED" and state.get("result_url"):
            perf(
                "job_completed",
                job_id=str(uid),
                total_duration_ms=round(_job_total_ms(created_at), 1),
                status="COMPLETED",
            )
            return {
                "status": "COMPLETED",
                "job_id": str(uid),
                "result_url": state.get("result_url"),
                "provider": provider.provider_name,
                "model_version": provider.model_version,
            }
        message = state.get("error") or "Your look could not be created."
        # Raise transient failures so Celery's retry (exponential backoff) applies;
        # permanent ones fail the job immediately without retrying.
        if state.get("retryable"):
            raise RetryableTryOnError(message[:280])
        _fail_safe(db, uid, message[:280])
        return {"status": "FAILED", "job_id": str(uid), "error_message": message[:280]}

    input_ = TryOnInput(
        person_image_url=person.url,
        fabric_image_url=fabric.url,
        garment_type=job.garment_type,
        garment_style=job.garment_style,
        gender=job.gender,
    )

    print(f"[TASKS] Pipeline path | job={uid} | provider={provider.provider_name}")
    try:
        print(f"[AI] Generation request started job_id={uid} task=tryon provider={provider.provider_name} model={provider.model_version}", flush=True)
        output = provider.generate(input_)
        print(f"[AI] Generation completed job_id={uid} task=tryon result_url={output.result_url}", flush=True)
    except PermanentTryOnError as exc:
        print(f"[TASKS] Pipeline PERMANENT error | job={uid} | {exc}")
        _fail_safe(db, uid, _user_message(exc))
        return {"status": "FAILED", "job_id": str(uid), "error_message": _user_message(exc)}
    except Exception as exc:
        print(f"[TASKS] Pipeline UNEXPECTED error | job={uid} | {type(exc).__name__}: {exc}")
        _fail_safe(db, uid, _user_message(exc))
        return {"status": "FAILED", "job_id": str(uid), "error_message": _user_message(exc)}

    asset = MediaAsset(
        user_id=job.user_id,
        kind="result",
        imagekit_file_id=f"result-{job.id}-{uuid.uuid4()}",
        url=output.result_url,
    )
    db.add(asset)
    db.flush()

    existing = db.query(TryOnResult).filter(TryOnResult.try_on_job_id == job.id).first()
    if existing:
        existing.result_image_id = asset.id
        existing.result_url = output.result_url
    else:
        db.add(
            TryOnResult(
                try_on_job_id=job.id,
                result_image_id=asset.id,
                result_url=output.result_url,
            )
        )

    db.query(TryOnJob).filter(TryOnJob.id == uid).update(
        {
            "status": "COMPLETED",
            "completed_at": datetime.utcnow(),
            "provider": output.provider,
            "model_version": output.model_version,
            "error_message": None,
        },
        synchronize_session=False,
    )
    db.commit()
    _status_log(uid, "COMPLETED", output.result_url)
    perf(
        "job_completed",
        job_id=str(uid),
        total_duration_ms=round(_job_total_ms(created_at), 1),
        status="COMPLETED",
    )

    return {
        "status": "COMPLETED",
        "job_id": str(uid),
        "result_url": output.result_url,
        "provider": output.provider,
        "model_version": output.model_version,
    }


def _write_langgraph_result(
    db: Session,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
    result_url: str,
    provider_name: str,
    model_version: str,
) -> None:
    """Persist a completed LangGraph result (idempotent single-result write)."""
    asset = MediaAsset(
        user_id=user_id,
        kind="result",
        imagekit_file_id=f"result-{job_id}-{uuid.uuid4()}",
        url=result_url,
    )
    db.add(asset)
    db.flush()

    existing = db.query(TryOnResult).filter(TryOnResult.try_on_job_id == job_id).first()
    if existing:
        existing.result_image_id = asset.id
        existing.result_url = result_url
    else:
        db.add(
            TryOnResult(
                try_on_job_id=job_id,
                result_image_id=asset.id,
                result_url=result_url,
            )
        )

    db.query(TryOnJob).filter(TryOnJob.id == job_id).update(
        {
            "status": "COMPLETED",
            "completed_at": datetime.utcnow(),
            "provider": provider_name,
            "model_version": model_version,
            "error_message": None,
        },
        synchronize_session=False,
    )
    db.add(Notification(user_id=user_id, title="Your look is ready", message="Your AI try-on has finished.", type="TRY_ON_COMPLETED"))
    db.commit()
    _status_log(job_id, "COMPLETED", result_url)


def _save_langgraph_result(db: Session, job: TryOnJob, state: dict) -> None:
    """Persist a LangGraph workflow result into the PostgreSQL tables.

    The graph uploaded the image to ImageKit and placed ``result_url`` on the
    state; this callback records the ``MediaAsset`` + ``TryOnResult`` rows and
    flips the job to COMPLETED (idempotent, mirroring the pipeline path).

    The worker holds one session for the whole job, and managed Postgres
    poolers drop idle connections after long image generations. If the write on
    that stale session fails, re-run the exact same (idempotent) persistence on
    a brand-new session so the expensive AI output is not lost.
    """
    if not state.get("result_url"):
        raise RetryableTryOnError("Workflow produced no result URL to persist.")

    job_id = job.id
    user_id = job.user_id
    result_url = state["result_url"]
    provider_name = job.provider or get_provider().provider_name
    model_version = get_provider().model_version

    try:
        _write_langgraph_result(db, job_id, user_id, result_url, provider_name, model_version)
    except Exception as exc:  # noqa: BLE001 - the wrapper node marks it retryable anyway
        print(
            f"[TASKS] Result persistence failed on worker session"
            f" ({type(exc).__name__}: {exc}); retrying with a fresh DB session",
            flush=True,
        )
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        try:
            db.close()
        except Exception:  # noqa: BLE001
            pass
        fresh = SessionLocal()
        try:
            _write_langgraph_result(fresh, job_id, user_id, result_url, provider_name, model_version)
        finally:
            fresh.close()


@celery_app.task(bind=True, max_retries=settings.try_on_max_retries, default_retry_delay=settings.retry_backoff_base)
def process_try_on_job(self, job_id: str):
    perf("worker_received", job_id=job_id, attempt=self.request.retries)
    worker_t = _time.perf_counter()
    db: Session = SessionLocal()
    try:
        recover_stale_jobs(db)
        perf("worker_setup_end", job_id=job_id, duration_ms=ago_ms(worker_t))
        print(f"[WORKER] Job picked up job_id={job_id} attempt={self.request.retries}/{self.max_retries}", flush=True)
        try:
            uid = uuid.UUID(job_id)
        except ValueError:
            return {"status": "NOT_FOUND", "job_id": job_id}

        try:
            print(f"[WORKER] Processing job job_id={job_id}", flush=True)
            return _process_job(db, uid)
        except RetryableTryOnError as exc:
            print(f"[TASKS] RETRYABLE error | job={job_id} | {exc}")
            # Reset to QUEUED so the retried run can claim the job again. The
            # worker's session may already be dead (idle-dropped pooled
            # connection), so _reset_to_queued reopens a fresh session when
            # needed so the retry is never lost.
            db = _reset_to_queued(db, uid)
            _status_log(uid, "QUEUED", f"retry {self.request.retries}/{self.max_retries}")
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc, countdown=_backoff(self.request.retries))
            _fail_safe(db, uid, _user_message(exc))
            return {"status": "FAILED", "job_id": job_id}
        except PermanentTryOnError as exc:
            print(f"[TASKS] PERMANENT error | job={job_id} | {exc}")
            _fail_safe(db, uid, _user_message(exc))
            return {"status": "FAILED", "job_id": job_id}
        except Exception as exc:
            print(f"[TASKS] UNEXPECTED error | job={job_id} | {type(exc).__name__}: {exc}")
            # Unexpected bugs should fail immediately rather than creating another
            # billable generation attempt. Only known retryable cases are requeued.
            _fail_safe(db, uid, "Your look could not be created. Please try again.")
            return {"status": "FAILED", "job_id": job_id}
    finally:
        print(f"[TRYON][job_id={job_id}][WORKER] Task finished", flush=True)
        db.close()