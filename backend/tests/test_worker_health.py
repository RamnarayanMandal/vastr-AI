"""Regression tests for the Celery worker health check (pidbox ping).

The previous worker detection scanned Redis keys ``celery@*`` which is
unreliable on managed providers (empty even with live consumers). The
replacement pings workers over the pidbox broadcast and distinguishes
reachable / no-worker / broker-unavailable.
"""

import redis

from app.main import _worker_health_check


class _Inspector:
    def __init__(self, reply=None, exc=None):
        self._reply = reply
        self._exc = exc

    def ping(self):
        if self._exc is not None:
            raise self._exc
        return self._reply


def test_worker_health_reachable():
    res = _worker_health_check(
        inspector=_Inspector(reply={"celery@node1": {"ok": "pong"}})
    )
    assert res["reachable"] is True
    assert res["broker_ok"] is True
    assert res["workers"] == ["celery@node1"]


def test_worker_health_no_workers():
    res = _worker_health_check(inspector=_Inspector(reply={}))
    assert res["reachable"] is False
    assert res["broker_ok"] is True
    assert res["detail"] == "no worker replied"


def test_worker_health_broker_unavailable():
    res = _worker_health_check(
        inspector=_Inspector(exc=redis.exceptions.ConnectionError("boom"))
    )
    assert res["reachable"] is False
    assert res["broker_ok"] is False


def test_worker_health_timeout():
    res = _worker_health_check(inspector=_Inspector(exc=TimeoutError("ping timed out")))
    assert res["reachable"] is False
    assert res["broker_ok"] is False