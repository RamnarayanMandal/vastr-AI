import uuid
import asyncio
from datetime import datetime

import pytest
from unittest.mock import MagicMock, patch

from app.models import MediaAsset, TryOnJob, TryOnResult
from app.services.pipeline import synthesize_fabric_bytes, synthesize_person_bytes
from app.services.try_on_provider import CatVTONProvider, MockVirtualTryOnProvider
from app.worker import tasks
from app.worker.tasks import _backoff, _claim_job, _fail, _process_job
from app.main import lifespan


def _seed_assets(db, user_id) -> dict:
    person = MediaAsset(
        user_id=user_id,
        kind="person",
        imagekit_file_id=f"p-{uuid.uuid4()}",
        url="https://example.com/person.jpg",
    )
    fabric = MediaAsset(
        user_id=user_id,
        kind="fabric",
        imagekit_file_id=f"f-{uuid.uuid4()}",
        url="https://example.com/fabric.jpg",
    )
    db.add_all([person, fabric])
    db.commit()
    db.refresh(person)
    db.refresh(fabric)
    return {"person": person, "fabric": fabric}


def _seed_job(db, user_id, assets) -> TryOnJob:
    job = TryOnJob(
        user_id=user_id,
        person_image_id=assets["person"].id,
        fabric_image_id=assets["fabric"].id,
        garment_type="shirt",
        garment_style="casual",
        gender="women",
        status="QUEUED",
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_backoff_exponential_capped():
    assert _backoff(0) == tasks.settings.retry_backoff_base
    assert _backoff(0) < _backoff(1) < _backoff(2)
    assert _backoff(10) == tasks.settings.retry_max_delay


def test_claim_job_idempotent(db_session, sample_user):
    assets = _seed_assets(db_session, sample_user.id)
    job = _seed_job(db_session, sample_user.id, assets)

    assert _claim_job(db_session, job.id, "mock") is True
    # Second claim must be refused (already PROCESSING or terminal).
    assert _claim_job(db_session, job.id, "mock") is False

    db_session.refresh(job)
    assert job.status == "PROCESSING"


def test_api_lifespan_autostarts_worker():
    """Uvicorn boot must call ensure_worker_running() so a plain
    `uvicorn app.main:app --reload` also spawns the Celery worker."""
    mock_connect = MagicMock()
    mock_connect.__enter__.return_value = object()
    mock_connect.__exit__.return_value = None

    with patch("app.main.engine.connect", return_value=mock_connect), patch(
        "app.main.redis.Redis.from_url"
    ) as redis_mock, patch(
        "app.main.ensure_worker_running", return_value=True
    ) as autostart_mock:
        redis_mock.return_value.ping.return_value = True
        redis_mock.return_value.scan_iter.return_value = [b"celery@vastrai-worker"]
        async def _run():
            async with lifespan(object()):
                pass
        asyncio.run(_run())

    autostart_mock.assert_called_once()


def test_process_job_completes(db_session, sample_user):
    with patch(
        "app.worker.tasks.get_provider",
        return_value=MockVirtualTryOnProvider(),
    ) as get_provider_patch:
        get_provider_patch.return_value._delay = 0
        with patch("app.worker.tasks.settings.workflow_engine", "pipeline"):
            assets = _seed_assets(db_session, sample_user.id)
            job = _seed_job(db_session, sample_user.id, assets)

            result = _process_job(db_session, job.id)

    assert result["status"] == "COMPLETED"
    assert result["provider"] == "mock"
    assert result["model_version"] == "mock-pipeline-1.0"
    assert result["result_url"]

    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.provider == "mock"
    assert job.model_version == "mock-pipeline-1.0"

    result_row = (
        db_session.query(TryOnResult).filter(TryOnResult.try_on_job_id == job.id).first()
    )
    assert result_row is not None
    assert result_row.result_url


def test_process_job_is_idempotent(db_session, sample_user):
    with patch(
        "app.worker.tasks.get_provider",
        return_value=MockVirtualTryOnProvider(),
    ) as get_provider_patch:
        get_provider_patch.return_value._delay = 0
        with patch("app.worker.tasks.settings.workflow_engine", "pipeline"):
            assets = _seed_assets(db_session, sample_user.id)
            job = _seed_job(db_session, sample_user.id, assets)

            first = _process_job(db_session, job.id)
            second = _process_job(db_session, job.id)

    assert first["status"] == "COMPLETED"
    assert second["status"] == "COMPLETED"
    rows = (
        db_session.query(TryOnResult).filter(TryOnResult.try_on_job_id == job.id).count()
    )
    assert rows == 1


def test_process_job_missing_media_fails(db_session, sample_user):
    assets = _seed_assets(db_session, sample_user.id)
    job = _seed_job(db_session, sample_user.id, assets)
    db_session.delete(assets["person"])
    db_session.commit()

    result = _process_job(db_session, job.id)

    assert result["status"] == "FAILED"
    db_session.refresh(job)
    assert job.status == "FAILED"
    assert "missing" in (job.error_message or "").lower()


def test_process_job_permanent_error_marks_failed(db_session, sample_user):
    """Unconfigured CatVTON must end the job FAILED with useful info, not hang."""
    provider = CatVTONProvider()
    with patch("app.worker.tasks.get_provider", return_value=provider):
        with patch(
            "app.services.pipeline.download_url",
            side_effect=[synthesize_person_bytes(), synthesize_fabric_bytes()],
        ):
            with patch("app.worker.tasks.settings.workflow_engine", "pipeline"):
                assets = _seed_assets(db_session, sample_user.id)
                job = _seed_job(db_session, sample_user.id, assets)

                result = _process_job(db_session, job.id)

    assert result["status"] == "FAILED"
    db_session.refresh(job)
    assert job.status == "FAILED"
    assert "AI_GARMENT_GENERATION_ENDPOINT" in (job.error_message or "")


def test_fail_writes_message(db_session, sample_user):
    assets = _seed_assets(db_session, sample_user.id)
    job = _seed_job(db_session, sample_user.id, assets)
    _fail(db_session, job.id, "custom message")
    db_session.refresh(job)
    assert job.status == "FAILED"
    assert job.error_message == "custom message"


def test_process_job_langgraph_engine_persists_result(db_session, sample_user):
    """AI_WORKFLOW_ENGINE=langgraph: the worker runs the graph, the saver
    callback persists a valid TryOnResult + result asset, job -> COMPLETED."""
    called = {}

    def fake_run_workflow(**kwargs):
        # Capture the saver callback and invoke it with a COMPLETED state.
        saver = kwargs["saver"]
        state = {
            "job_id": kwargs["job_id"],
            "status": "COMPLETED",
            "result_url": "https://ik.imagekit.io/vastrai/result-langgraph.jpg",
        }
        saver(state)
        called["saver_invoked"] = True
        return state

    with patch("app.worker.tasks.get_provider", return_value=MockVirtualTryOnProvider()):
        with patch("app.services.workflow.run_workflow", side_effect=fake_run_workflow):
            with patch("app.services.image_gen.get_image_gen_backend") as get_backend:
                get_backend.return_value = object()  # mocked run_workflow ignores it
                assets = _seed_assets(db_session, sample_user.id)
                job = _seed_job(db_session, sample_user.id, assets)
                with patch("app.worker.tasks.settings.workflow_engine", "langgraph"):
                    result = _process_job(db_session, job.id)

    assert called["saver_invoked"] is True
    assert result["status"] == "COMPLETED"
    assert result["result_url"] == "https://ik.imagekit.io/vastrai/result-langgraph.jpg"

    db_session.refresh(job)
    assert job.status == "COMPLETED"
    result_row = (
        db_session.query(TryOnResult).filter(TryOnResult.try_on_job_id == job.id).first()
    )
    assert result_row is not None
    assert result_row.result_url == "https://ik.imagekit.io/vastrai/result-langgraph.jpg"


def test_process_job_langgraph_engine_transient_raises_retryable(db_session, sample_user):
    """A transient graph failure must raise RetryableTryOnError so Celery retries
    with exponential backoff instead of failing the job immediately."""
    from app.worker.tasks import RetryableTryOnError

    def fake_run_workflow(**kwargs):
        return {
            "job_id": kwargs["job_id"],
            "status": "FAILED",
            "error": "Garment generation failed: model timeout",
            "retryable": True,
        }

    with patch("app.worker.tasks.get_provider", return_value=MockVirtualTryOnProvider()):
        with patch("app.services.workflow.run_workflow", side_effect=fake_run_workflow):
            with patch("app.services.image_gen.get_image_gen_backend") as get_backend:
                get_backend.return_value = object()
                assets = _seed_assets(db_session, sample_user.id)
                job = _seed_job(db_session, sample_user.id, assets)
                with patch("app.worker.tasks.settings.workflow_engine", "langgraph"):
                    with pytest.raises(RetryableTryOnError):
                        _process_job(db_session, job.id)


def test_process_job_langgraph_engine_permanent_fails(db_session, sample_user):
    """A permanent graph failure must fail the job immediately (no retry)."""
    def fake_run_workflow(**kwargs):
        return {
            "job_id": kwargs["job_id"],
            "status": "FAILED",
            "error": "Garment type and style are required.",
            "retryable": False,
        }

    with patch("app.worker.tasks.get_provider", return_value=MockVirtualTryOnProvider()):
        with patch("app.services.workflow.run_workflow", side_effect=fake_run_workflow):
            with patch("app.services.image_gen.get_image_gen_backend") as get_backend:
                get_backend.return_value = object()
                assets = _seed_assets(db_session, sample_user.id)
                job = _seed_job(db_session, sample_user.id, assets)
                with patch("app.worker.tasks.settings.workflow_engine", "langgraph"):
                    result = _process_job(db_session, job.id)

    assert result["status"] == "FAILED"
    db_session.refresh(job)
    assert job.status == "FAILED"
    assert "Garment type and style" in (job.error_message or "")
