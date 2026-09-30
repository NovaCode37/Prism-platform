import importlib

import pytest


def _reload_security(monkeypatch, quota):
    monkeypatch.setenv("SCAN_QUOTA_PER_DAY", str(quota))
    import web.security as security
    return importlib.reload(security)


def test_quota_disabled_never_blocks(monkeypatch):
    security = _reload_security(monkeypatch, 0)
    for _ in range(50):
        security.record_scan("user-a")
    security.check_scan_quota("user-a")
    usage = security.get_usage("user-a")
    assert usage["limit"] is None


def test_quota_blocks_after_limit(monkeypatch):
    from fastapi import HTTPException
    security = _reload_security(monkeypatch, 3)
    for _ in range(3):
        security.check_scan_quota("user-b")
        security.record_scan("user-b")
    with pytest.raises(HTTPException) as exc:
        security.check_scan_quota("user-b")
    assert exc.value.status_code == 429


def test_usage_is_per_principal(monkeypatch):
    security = _reload_security(monkeypatch, 5)
    security.record_scan("user-c")
    security.record_scan("user-c")
    security.record_scan("user-d")
    assert security.get_usage("user-c")["used"] == 2
    assert security.get_usage("user-d")["used"] == 1
    assert security.get_usage("user-c")["remaining"] == 3
