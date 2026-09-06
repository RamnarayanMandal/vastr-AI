from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
from sqlalchemy import text
import redis

from .config import settings
from .database import engine
from .router import auth, credits, history, notifications, try_on, uploads, users
from .router.uploads import LOCAL_DIR
from .worker.autostart import ensure_worker_running


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
        _rb = redis.Redis.from_url(settings.redis_url)
        _workers = list(_rb.scan_iter("celery@*", count=1000))
        if not _workers:
            print(
                "[WORKER] WARNING: No Celery worker detected - jobs will stay QUEUED. "
                "Check the autostart log above (or run backend/run_dev.ps1 / the Docker 'worker' service).",
                flush=True,
            )
        else:
            names = ", ".join(w.decode("utf-8") for w in _workers)
            print(f"[WORKER] Detected {len(_workers)} worker(s): {names}", flush=True)
    except Exception as exc:
        print(f"[WORKER] Could not check worker presence: {type(exc).__name__}", flush=True)
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