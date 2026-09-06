"""Structured [PERF] performance instrumentation.

Purely observational: emits a parseable ``[PERF] <event> k=v ...`` line to
stdout (``print(..., flush=True)``) and appends the same line (plus a UTC
epoch-millisecond prefix) to ``backend/logs/perf.log`` so API and worker
processes share one time-ordered performance feed. Never raises and never
changes generation behaviour.

Timings are produced by callers via ``time.perf_counter()``; events carry
``duration_ms`` etc. so the report can be built from logs alone.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()
_HANDLE = None
_ENABLED = True


def perf(event: str, **fields) -> None:
    """Emit one structured performance line. Errors are swallowed on purpose."""
    global _HANDLE  # noqa: PLW0603
    if not _ENABLED:
        return
    try:
        parts = [f"[PERF] {event}"]
        parts.extend(f"{k}={v}" for k, v in fields.items())
        line = " ".join(parts)
        print(line, flush=True)
        with _LOCK:
            if _HANDLE is None:
                log_dir = Path(__file__).resolve().parents[2] / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                _HANDLE = open(log_dir / "perf.log", "a", encoding="utf-8")  # noqa: SIM115
            ts = int(time.time() * 1000)
            iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            _HANDLE.write(f"{ts} {iso}Z {line}\n")
            _HANDLE.flush()
    except Exception:  # noqa: BLE001 - instrumentation must never crash the app
        pass


def ago_ms(started: float) -> float:
    """Milliseconds elapsed since ``started`` (time.perf_counter())."""
    return (time.perf_counter() - started) * 1000.0