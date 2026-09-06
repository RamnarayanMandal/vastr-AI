from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
from sqlalchemy import text
import redis
from kombu.exceptions import OperationalError as KombuOperationalError

from .config import settings
from .database import engine
from .router import auth, credits, history, notifications, try_on, uploads, users
from .router.uploads import LOCAL_DIR
from .worker.autostart import ensure_worker_running
from .worker.celery_app import celery_app as worker_celery_app


def _worker_health_check(timeout: float = 1.0, inspector=None) -> dict:
    """Probe Celery workers via the pidbox broadcast.

    Returns:
      reachable=True            -> a worker replied to ping
      reachable=False, broker_ok=True  -> broker reachable, no worker replying
      reachable=False, broker_ok=False -> broker itself is unavailable

    Unlike scanning Redis keys for ``celery@*``, ping reflects reality: the
    key scan is unreliable on managed Redis providers (no keys appear even
    when workers are consuming).
    """
    try:
        insp = inspector or worker_celery_app.control.inspect(timeout=timeout)
        reply = insp.ping()
    except (KombuOperationalError, redis.exceptions.ConnectionError, TimeoutError, OSError) as exc:
        return {"reachable": False, "broker_ok": False, "detail": f"{type(exc).__name__}: {exc}"}
    except Exception as exc:  # noqa: BLE001 - safest to degrade to "unknown"
        return {"reachable": False, "broker_ok": False, "detail": f"unexpected: {type(exc).__name__}: {exc}"}
    if not reply:
        return {"reachable": False, "broker_ok": True, "detail": "no worker replied"}
    return {"reachable": True, "broker_ok": True, "workers": sorted(str(k) for k in reply)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-start the Celery worker so a plain `uvicorn app.main:app --reload`
    # also brings up the worker alongside the API. app/worker/autostart.py uses
    # a PID lock file, so under `--reload` (parent + reload child) it spawns
    # exactly ONE worker. Disable the autostart with: VASTRAVIEW_NO_AUTOSTART=1
    print("[API] Uvicorn started", flush=True)
    try:
        await asyncio.to_thread(ensure_worker_running)
    except Exception as exc:
        print(f"[WORKER] Autostart failed: {type(exc).__name__}: {exc}", flush=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("[DATABASE] Connected", flush=True)
    except Exception as exc:
        print(f"[DATABASE] Connection failed: {type(exc).__name__}", flush=True)
    try:
        redis.Redis.from_url(settings.redis_url).ping()
        print("[REDIS] Connected", flush=True)
    except Exception as exc:
        print(f"[REDIS] Connection failed: {type(exc).__name__}", flush=True)
    try:
        if settings.celery_broker_url.startswith("memory://"):
            # In-memory test/local broker: no separate worker process to probe.
            print("[WORKER_HEALTH] reachable=false (memory broker, no worker)", flush=True)
        else:
            result = await asyncio.wait_for(
                asyncio.to_thread(_worker_health_check), timeout=6.0
            )
            if result["reachable"]:
                print(f"[WORKER_HEALTH] reachable=true workers={result['workers']}", flush=True)
            elif result["broker_ok"]:
                print(
                    "[WORKER_HEALTH] reachable=false workers=0 - broker reachable but no "
                    "worker replying yet (worker may still be booting)",
                    flush=True,
                )
            else:
                print(f"[WORKER_HEALTH] broker-unavailable detail={result['detail']}", flush=True)
    except asyncio.TimeoutError:
        print("[WORKER_HEALTH] timeout worker=unknown", flush=True)
    except Exception as exc:
        print(f"[WORKER_HEALTH] check failed: {type(exc).__name__}: {exc}", flush=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_origins == "*" else settings.cors_origins.split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.api_prefix
app.include_router(auth.router, prefix=prefix)
app.include_router(uploads.router, prefix=prefix)
app.include_router(try_on.router, prefix=prefix)
app.include_router(history.router, prefix=prefix)
app.include_router(notifications.router, prefix=prefix)
app.include_router(credits.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)


@app.get("/local_uploads/{kind}/{name}")
def local_upload(kind: str, name: str):
    """Serve images stored locally when ImageKit is unavailable.

    ``kind`` is one of person / fabric / result / misc (or a legacy marker).
    """
    from fastapi import HTTPException

    import os

    path = os.path.join(LOCAL_DIR, kind, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path)


@app.get("/local_uploads/{name}")
def local_upload_legacy(name: str):
    """Serve legacy flat-layout local files (saved before per-kind folders)."""
    from fastapi import HTTPException

    import os

    path = os.path.join(LOCAL_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}