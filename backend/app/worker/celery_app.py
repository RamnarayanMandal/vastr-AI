import socket

from celery import Celery
from celery.signals import worker_ready

from app.config import settings

celery_app = Celery(
    "vastrai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

# The managed Redis provider (e.g. Vercel HTTP/Redis) drops idle TCP
# connections, and a dropped socket is exactly what surfaced in the recent
# enqueue failures ("ConnectionResetError: [WinError 10054]"). Keep the
# sockets alive so idle pooled connections survive, and reconnect on timeout
# instead of raising straight away.
_socket_keepalive_options: dict[int, int] = {}
if hasattr(socket, "TCP_KEEPIDLE"):
    _socket_keepalive_options[socket.TCP_KEEPIDLE] = 60  # idle 60s before probing
if hasattr(socket, "TCP_KEEPINTVL"):
    _socket_keepalive_options[socket.TCP_KEEPINTVL] = 30  # probe every 30s
if hasattr(socket, "TCP_KEEPCNT"):
    _socket_keepalive_options[socket.TCP_KEEPCNT] = 3  # give up after 3 probes

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
    broker_connection_max_retries=10,
    broker_connection_timeout=5.0,
    broker_channel_error_retry=True,
    task_publish_retry=True,
    task_publish_retry_policy={
        "max_retries": 10,
        "interval_start": 0.5,
        "interval_step": 1.0,
        "interval_max": 10,
    },
    broker_transport_options={
        "socket_keepalive": True,
        "socket_keepalive_options": _socket_keepalive_options,
        "socket_connect_timeout": 10,
        "health_check_interval": 30,
        "retry_on_timeout": True,
        "max_connections": 20,
    },
)


@worker_ready.connect
def _worker_ready(sender=None, **kwargs):
    print("VastrAI Celery Worker", flush=True)
    print(f"[WORKER] Broker: connected | queue=vastrai.tryon", flush=True)
    print("[WORKER] Registered try-on task: app.worker.tasks.process_try_on_job", flush=True)
    try:
        from app.worker.tasks import recover_stale_jobs

        recover_stale_jobs()
    except Exception as exc:
        print(f"[RECOVERY] Startup sweep failed: {type(exc).__name__}: {exc}", flush=True)
    print("[WORKER] Ready", flush=True)