import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.hudsonrock import HudsonRockLookup, is_enabled


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", raise_json=False):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._payload


DOMAIN_PAYLOAD = {
    "total": 29652,
    "employees": 548,
    "users": 28330,
    "third_parties": 774,
    "data": {
        "employees_urls": [
            {"url": "https://sso.example.com/a", "occurrence": 10},
            {"url": "https://sso.example.com/b", "occurrence": 250},
            {"url": "https://sso.example.com/c", "occurrence": 100},
        ]
    },
    "stealerFamilies": {"total": 27647, "Lumma": 5905, "RedLine": 6918, "StealC": 1019},
    "employeePasswords": {
        "totalPass": 751,
        "has_stats": True,
        "too_weak": {"qty": 207, "perc": 27.6},
        "strong": {"qty": 219, "perc": 29.2},
    },
}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("HUDSONROCK_ENABLED", "true")


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HUDSONROCK_ENABLED", raising=False)
    assert is_enabled() is False
    result = HudsonRockLookup().search_domain("example.com")
    assert result["status"] == "skipped"
    assert "HUDSONROCK_ENABLED" in result["status_reason"]


def test_disabled_makes_no_request(monkeypatch):
    monkeypatch.delenv("HUDSONROCK_ENABLED", raising=False)
    with patch("modules.hudsonrock.requests.get") as mock_get:
        HudsonRockLookup().search_domain("example.com")
        mock_get.assert_not_called()


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_enabled_flag_values(monkeypatch, value):
    monkeypatch.setenv("HUDSONROCK_ENABLED", value)
    assert is_enabled() is True


def test_domain_parsing(enabled):
    with patch("modules.hudsonrock.requests.get", return_value=FakeResponse(payload=DOMAIN_PAYLOAD)):
        result = HudsonRockLookup().search_domain("example.com")

    assert result["status"] == "ok"
    assert result["total_compromised"] == 29652
    assert result["employees"] == 548
    assert result["third_parties"] == 774

    urls = result["employee_urls"]
    assert [u["occurrence"] for u in urls] == [250, 100, 10]

    families = result["stealer_families"]
    assert "total" not in families
    assert list(families) == ["RedLine", "Lumma", "StealC"]

    stats = result["employee_password_stats"]
    assert stats["total"] == 751
    assert stats["too_weak"] == 27.6


def test_password_stats_skipped_without_has_stats(enabled):
    payload = dict(DOMAIN_PAYLOAD, employeePasswords={"totalPass": 5, "has_stats": False})
    with patch("modules.hudsonrock.requests.get", return_value=FakeResponse(payload=payload)):
        result = HudsonRockLookup().search_domain("example.com")
    assert result["employee_password_stats"] is None


def test_rate_limited(enabled):
    with patch("modules.hudsonrock.requests.get", return_value=FakeResponse(status_code=429)):
        result = HudsonRockLookup().search_domain("example.com")
    assert result["status"] == "rate_limited"


def test_http_error(enabled):
    with patch("modules.hudsonrock.requests.get", return_value=FakeResponse(status_code=500)):
        result = HudsonRockLookup().search_domain("example.com")
    assert result["status"] == "error"
    assert "500" in result["status_reason"]


def test_non_json_response(enabled):
    with patch("modules.hudsonrock.requests.get", return_value=FakeResponse(raise_json=True)):
        result = HudsonRockLookup().search_domain("example.com")
    assert result["status"] == "error"
    assert "non-JSON" in result["status_reason"]


def test_timeout(enabled):
    import requests

    with patch("modules.hudsonrock.requests.get", side_effect=requests.Timeout()):
        result = HudsonRockLookup().search_domain("example.com")
    assert result["status"] == "error"
    assert "did not respond" in result["status_reason"]


def test_empty_target(enabled):
    result = HudsonRockLookup().search_domain("")
    assert result["status"] == "error"


def test_username_strips_at_sign(enabled):
    payload = {"stealers": [{}, {}], "total_corporate_services": 3, "total_user_services": 7}
    with patch("modules.hudsonrock.requests.get", return_value=FakeResponse(payload=payload)) as mock_get:
        result = HudsonRockLookup().search_username("@testadmin")

    assert mock_get.call_args.kwargs["params"] == {"username": "testadmin"}
    assert result["stealers_found"] == 2
    assert result["compromised"] is True
    assert result["corporate_services"] == 3


def test_email_lowercased(enabled):
    with patch("modules.hudsonrock.requests.get", return_value=FakeResponse(payload={"stealers": []})) as mock_get:
        result = HudsonRockLookup().search_email("  User@Example.COM ")

    assert mock_get.call_args.kwargs["params"] == {"email": "user@example.com"}
    assert result["compromised"] is False


def test_proxy_used_when_set(enabled, monkeypatch):
    monkeypatch.setenv("MODULE_PROXY", "http://proxy:8080")
    with patch("modules.hudsonrock.requests.get", return_value=FakeResponse(payload=DOMAIN_PAYLOAD)) as mock_get:
        HudsonRockLookup().search_domain("example.com")
    assert mock_get.call_args.kwargs["proxies"] == {
        "http": "http://proxy:8080",
        "https": "http://proxy:8080",
    }


def test_no_proxy_by_default(enabled, monkeypatch):
    monkeypatch.delenv("MODULE_PROXY", raising=False)
    with patch("modules.hudsonrock.requests.get", return_value=FakeResponse(payload=DOMAIN_PAYLOAD)) as mock_get:
        HudsonRockLookup().search_domain("example.com")
    assert mock_get.call_args.kwargs["proxies"] is None
