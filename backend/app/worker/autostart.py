"""Auto-start the Celery worker alongside the FastAPI app.

The FastAPI server and the background worker are separate processes.  When the
app boots we check whether a worker is already running (via a PID lock file);
if not, we spawn one as a detached background subprocess with the same Python
interpreter that launched uvicorn.  A PID lock prevents ``--reload`` from
spawning duplicates every time the reload subprocess restarts.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

_LAUNCHED_BY_AUTOSTART = False


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def worker_lock_path() -> Path:
    return backend_root() / ".worker.pid"


def _read_lock() -> tuple[str, str] | None:
    """Return (pid, cmd) from the lock file, or None if absent/stale."""
    lock = worker_lock_path()
    try:
        parts = lock.read_text().strip().split("\n", 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    except OSError:
        pass
    return None


def _process_alive(pid: str) -> bool:
    """Return True only if *pid* is alive **and** looks like a celery worker."""
    try:
        import psutil
    except Exception:
        psutil = None
    try:
        pid_int = int(pid)
    except ValueError:
        return False

    alive = False
    if psutil is not None:
        try:
            alive = psutil.pid_exists(pid_int)
        except Exception:
            alive = False
    else:
        # Cross-platform fallback (no psutil dependency).
        if sys.platform == "win32":
            try:
                import ctypes

                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION, False, pid_int
                )
                if handle:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    alive = True
            except Exception:
                pass
        else:
            try:
                os.kill(pid_int, 0)
                alive = True
            except (ProcessLookupError, PermissionError):
                pass

    if not alive:
        return False

    # Verify the process is actually our celery worker, not a recycled PID.
    if psutil is not None:
        try:
            proc = psutil.Process(pid_int)
            cmdline = " ".join(proc.cmdline()).lower()
            return "celery" in cmdline
        except Exception:
            return False
    return True  # no psutil — trust the PID lock


def _write_lock(pid: str, cmd: str) -> None:
    try:
        worker_lock_path().write_text(f"{pid}\n{cmd}")
    except OSError:
        pass


def _clear_lock(pid: str) -> None:
    current = _read_lock()
    if current and current[0] == pid:
        try:
            worker_lock_path().unlink()
        except OSError:
            pass


def ensure_worker_running() -> bool:
    """Spawn the Celery worker if it is not already running.

    Returns True when a worker is running (either pre-existing or just started).
    """
    global _LAUNCHED_BY_AUTOSTART
    if _LAUNCHED_BY_AUTOSTART:
        return True

    # Allow disabling via env var (useful for --reload or manual management).
    if os.environ.get("VASTRAVIEW_NO_AUTOSTART", "").strip() in ("1", "true", "yes"):
        return False

    existing = _read_lock()
    if existing:
        pid, cmd = existing
        # Older lock files may record a different cmd; trust it only if alive.
        if _process_alive(pid):
            _LAUNCHED_BY_AUTOSTART = True
            return True
        # Stale lock — clean it up and fall through to spawn.
        _clear_lock(pid)

    # No live worker => spawn one.
    backend_dir = backend_root()
    python = sys.executable
    celery_cmd = [
        python,
        "-m",
        "celery",
        "-A",
        "app.worker.celery_app",
        "worker",
        "-l",
        "info",
        "-Q",
        "vastrai.tryon",
        # Force a single, headless worker process. Celery's default concurrency
        # is the CPU count, which spawns one "billiard" child per core (often
        # 10-30 extra processes on modern machines) and makes a dev server feel
        # like it opened dozens of windows/terminals. Try-on jobs are long and
        # hit a paid image API, so running them serially is safer and cheaper.
        "--concurrency",
        "1",
        "--pool",
        "solo",
    ]

    creationflags = 0
    if sys.platform == "win32":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )

    try:
        proc = subprocess.Popen(
            celery_cmd,
            cwd=str(backend_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[AUTOSTART] Failed to spawn Celery worker: {exc}")
        return False

    _write_lock(str(proc.pid), " ".join(celery_cmd))
    _LAUNCHED_BY_AUTOSTART = True

    # Give Celery a moment to boot before we declare it running.
    for _ in range(30):
        if not _process_alive(str(proc.pid)):
            _clear_lock(str(proc.pid))
            _LAUNCHED_BY_AUTOSTART = False
            print("[AUTOSTART] Celery worker exited during boot.")
            return False
        time.sleep(0.5)

    print(f"[AUTOSTART] Celery worker started (pid={proc.pid}).")
    return True
