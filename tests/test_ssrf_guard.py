import importlib

import pytest
from fastapi import HTTPException


def _reload_security(monkeypatch, allow_private):
    if allow_private is None:
        monkeypatch.delenv("ALLOW_PRIVATE_TARGETS", raising=False)
    else:
        monkeypatch.setenv("ALLOW_PRIVATE_TARGETS", allow_private)
    import web.security as security
    return importlib.reload(security)


@pytest.mark.parametrize("target", ["127.0.0.1", "169.254.169.254", "192.168.1.1", "10.0.0.5"])
def test_private_ip_targets_blocked(monkeypatch, target):
    security = _reload_security(monkeypatch, None)
    with pytest.raises(HTTPException) as exc:
        security.validate_public_target(target, "ip")
    assert exc.value.status_code == 400


@pytest.mark.parametrize("target,scan_type", [("8.8.8.8", "ip"), ("example.com", "domain")])
def test_public_targets_allowed(monkeypatch, target, scan_type):
    security = _reload_security(monkeypatch, None)
    security.validate_public_target(target, scan_type)


def test_non_network_scan_types_skipped(monkeypatch):
    security = _reload_security(monkeypatch, None)
    security.validate_public_target("127.0.0.1", "username")


def test_override_env_allows_private(monkeypatch):
    security = _reload_security(monkeypatch, "true")
    security.validate_public_target("127.0.0.1", "ip")
