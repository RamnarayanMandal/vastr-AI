"""Regression tests for retryable Celery enqueue.

Covers the broker-outage path that used to permanently FAIL freshly created
jobs: transient failures must be retried (fresh connection per attempt),
recovery must re-enqueue, and a genuinely dead broker must eventually FAIL the
job with the user-safe message instead of leaving it QUEUED forever.
"""

import io
import uuid

from PIL import Image

import app.router.try_on as try_on_module
from app.models import TryOnJob

_MSG = "We couldn't create your look right now. Please try again in a moment."


def _jpeg_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (201, 169, 106)).save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (13, 11, 26)).save(buf, format="PNG")
    buf.seek(0)
    return buf


def _upload_person(client, headers):
    resp = client.post(
        "/api/v1/upload/person",
        files={"file": ("person.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["image_id"]


def _upload_fabric(client, headers):
    resp = client.post(
        "/api/v1/upload/fabric",
        files={"file": ("fabric.png", _png_bytes(), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["image_id"]


def _create_payload(person_id, fabric_id):
    return {
        "person_image_id": person_id,
        "fabric_image_id": fabric_id,
        "garment_type": "shirt",
        "garment_style": "casual",
    }


def _seed_job(db_session, status="QUEUED"):
    job = TryOnJob(
        user_id=uuid.uuid4(),
        person_image_id=uuid.uuid4(),
        fabric_image_id=uuid.uuid4(),
        garment_type="shirt",
        garment_style="casual",
        gender="female",
        status=status,
        provider="mock",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


class _FlakyTask:
    def __init__(self, fail_count, exc=ConnectionError("reset by peer")):
        self.fail_count = fail_count
        self.exc = exc
        self.calls = 0

    def apply_async(self, *a, **kw):
        self.calls += 1
        if self.calls <= self.fail_count:
            raise self.exc
        return object()


class _DeadTask:
    def __init__(self, exc=ConnectionError("broker down")):
        self.exc = exc
        self.calls = 0

    def apply_async(self, *a, **kw):
        self.calls += 1
        raise self.exc


def test_enqueue_job_retries_then_succeeds(monkeypatch):
    task = _FlakyTask(fail_count=2)
    monkeypatch.setattr(try_on_module, "process_try_on_job", task)
    res = try_on_module._enqueue_job("job-id", _sleep=lambda s: None)
    assert res == {"ok": True, "attempts": 3, "error": None}
    assert task.calls == 3


def test_enqueue_job_exhausts_reports_failure(monkeypatch):
    task = _DeadTask()
    monkeypatch.setattr(try_on_module, "process_try_on_job", task)
    res = try_on_module._enqueue_job("job-id", max_attempts=3, _sleep=lambda s: None)
    assert res["ok"] is False
    assert res["attempts"] == 3
    assert "ConnectionError" in res["error"]
    assert task.calls == 3


def test_enqueue_job_never_raises(monkeypatch):
    task = _DeadTask()
    monkeypatch.setattr(try_on_module, "process_try_on_job", task)
    try_on_module._enqueue_job("job-id", _sleep=lambda s: None)  # must not raise


def test_background_loop_recovers_after_transient_failures(monkeypatch):
    task = _FlakyTask(fail_count=3)  # attempts 1-3 fail, attempt 4 recovers
    monkeypatch.setattr(try_on_module, "process_try_on_job", task)
    try_on_module._retry_enqueue_loop(str(uuid.uuid4()), _sleep=lambda s: None)  # must not raise
    assert task.calls == 4


def test_background_loop_exhaustion_marks_failed(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Factory = sessionmaker(bind=engine)

    session = Factory()
    job = _seed_job(session, status="QUEUED")
    job_id = str(job.id)
    session.close()

    monkeypatch.setattr(try_on_module, "process_try_on_job", _DeadTask())
    try_on_module._retry_enqueue_loop(job_id, db_factory=Factory, _sleep=lambda s: None)

    check = Factory()
    row = check.get(TryOnJob, uuid.UUID(job_id))
    assert row.status == "FAILED"
    assert row.error_message == _MSG
    check.close()


def test_mark_enqueue_failed_only_touches_queued(db_session):
    for status in ("PROCESSING", "COMPLETED"):
        job = _seed_job(db_session, status=status)
        try_on_module._mark_enqueue_failed(str(job.id), db_factory=lambda: db_session)
        db_session.expire_all()
        assert db_session.get(TryOnJob, job.id).status == status


def test_create_try_on_transient_failure_recovers_via_background(client, auth_headers, db_session, monkeypatch):
    headers, _ = auth_headers
    person_id = _upload_person(client, headers)
    fabric_id = _upload_fabric(client, headers)

    task = _FlakyTask(fail_count=4)  # sync attempts (1-4) fail, background attempt 5 succeeds
    monkeypatch.setattr(try_on_module, "process_try_on_job", task)
    monkeypatch.setattr(try_on_module, "_sleep_backoff", lambda s: None)

    resp = client.post("/api/v1/try-on", json=_create_payload(person_id, fabric_id), headers=headers)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "QUEUED"  # never permanently FAILED on a blip

    db_session.expire_all()
    job = db_session.get(TryOnJob, uuid.UUID(body["id"]))
    assert job is not None
    assert job.status == "QUEUED"
    assert job.retry_count == 4
    assert task.calls == 5  # 4 sync + 1 background retry, then recovered


def test_create_try_on_persistent_broker_outage_eventually_fails(client, auth_headers, db_session, monkeypatch):
    headers, _ = auth_headers
    person_id = _upload_person(client, headers)
    fabric_id = _upload_fabric(client, headers)

    monkeypatch.setattr(try_on_module, "process_try_on_job", _DeadTask())
    monkeypatch.setattr(try_on_module, "_sleep_backoff", lambda s: None)

    def _mark_failed_db(job_id, message=_MSG, db_factory=None):
        job = db_session.get(TryOnJob, uuid.UUID(job_id))
        if job is not None and job.status == "QUEUED":
            job.status = "FAILED"
            job.error_message = message
            db_session.commit()

    monkeypatch.setattr(try_on_module, "_mark_enqueue_failed", _mark_failed_db)

    resp = client.post("/api/v1/try-on", json=_create_payload(person_id, fabric_id), headers=headers)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "QUEUED"  # response is immediate; FAILED happens in background

    db_session.expire_all()
    job = db_session.get(TryOnJob, uuid.UUID(body["id"]))
    assert job is not None
    assert job.status == "FAILED"  # bounded: not left QUEUED forever
    assert job.error_message == _MSG  # user-facing message preserved