from celery import Celery
from celery.signals import worker_ready

from app.config import settings

celery_app = Celery(
    "vastrai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_default_queue="vastrai.tryon",
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
)


@worker_ready.connect
def _worker_ready(sender=None, **kwargs):
    print("VastrAI Celery Worker", flush=True)
    print(f"[WORKER] Broker: connected | queue=vastrai.tryon", flush=True)
    print("[WORKER] Registered try-on task: app.worker.tasks.process_try_on_job", flush=True)
    print("[WORKER] Ready", flush=True)