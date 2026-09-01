import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.lunar import LunarLookup, is_enabled


class FakeResponse:
    def __init__(self, status_code=200, payload=None, raise_json=False):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._payload


REPORT_PAYLOAD = {
    "domain": "example.com",
    "status": "REPORT_READY",
    "report": {
        "period": {"from": "2025-08-01", "to": "2026-07-31"},
        "summary": {
            "total_events": 97994,
            "infostealer_events": 2662,
            "data_breach_events": 95332,
            "employee_events": 94992,
            "client_events": 3002,
            "first_seen": "2025-08-02",
            "last_seen": "2026-07-31",
        },
        "malware_family_breakdown": [
            {"family": "LummaC2", "events": 225},
            {"family": "Redline", "events": 1642},
            {"family": "Vidar", "events": 100},
        ],
        "service_classification_breakdown": [
            {"service": "Citrix", "events": 63},
            {"service": "Microsoft", "events": 971},
        ],
        "country_breakdown": [
            {"country": "Netherlands", "events": 423},
            {"country": "United States", "events": 854},
        ],
        "monthly_timeline": [
            {"month": "2025-08", "total_events": 2473, "infostealer_events": 193, "data_breach_events": 2280},
            {"month": "2025-09", "total_events": 16507, "infostealer_events": 748, "data_breach_events": 15759},
        ],
    },
}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("LUNAR_ENABLED", "true")


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("LUNAR_ENABLED", raising=False)
    assert is_enabled() is False
    result = LunarLookup().search_domain("example.com")
    assert result["status"] == "skipped"
    assert "LUNAR_ENABLED" in result["status_reason"]


def test_disabled_makes_no_request(monkeypatch):
    monkeypatch.delenv("LUNAR_ENABLED", raising=False)
    with patch("modules.lunar.requests.get") as mock_get:
        LunarLookup().search_domain("example.com")
        mock_get.assert_not_called()


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_enabled_flag_values(monkeypatch, value):
    monkeypatch.setenv("LUNAR_ENABLED", value)
    assert is_enabled() is True


def test_report_parsing(enabled):
    with patch("modules.lunar.requests.get", return_value=FakeResponse(payload=REPORT_PAYLOAD)):
        result = LunarLookup().search_domain("example.com")

    assert result["status"] == "ok"
    assert result["report_status"] == "REPORT_READY"
    assert result["period"] == {"from": "2025-08-01", "to": "2026-07-31"}
    assert result["total_events"] == 97994
    assert result["infostealer_events"] == 2662
    assert result["client_events"] == 3002

    assert [f["family"] for f in result["malware_families"]] == ["Redline", "LummaC2", "Vidar"]
    assert [s["service"] for s in result["services"]] == ["Microsoft", "Citrix"]
    assert [c["country"] for c in result["countries"]] == ["United States", "Netherlands"]
    assert [m["month"] for m in result["monthly_timeline"]] == ["2025-08", "2025-09"]


def test_generating_report_is_skipped_not_an_error(enabled):
    payload = {"status": "GENERATING_REPORT"}
    with patch("modules.lunar.requests.get", return_value=FakeResponse(payload=payload)):
        result = LunarLookup().search_domain("example.com")
    assert result["status"] == "skipped"
    assert result["report_status"] == "GENERATING_REPORT"
    assert result["error"] is None


def test_not_authorized_is_skipped_not_an_error(enabled):
    payload = {"status": "NOT_AUTHORIZED"}
    with patch("modules.lunar.requests.get", return_value=FakeResponse(payload=payload)):
        result = LunarLookup().search_domain("example.com")
    assert result["status"] == "skipped"
    assert result["error"] is None


def test_missing_report_body(enabled):
    payload = {"status": "REPORT_READY"}
    with patch("modules.lunar.requests.get", return_value=FakeResponse(payload=payload)):
        result = LunarLookup().search_domain("example.com")
    assert result["status"] == "error"


def test_rate_limited(enabled):
    with patch("modules.lunar.requests.get", return_value=FakeResponse(status_code=429)):
        result = LunarLookup().search_domain("example.com")
    assert result["status"] == "rate_limited"


def test_http_error(enabled):
    with patch("modules.lunar.requests.get", return_value=FakeResponse(status_code=500)):
        result = LunarLookup().search_domain("example.com")
    assert result["status"] == "error"
    assert "500" in result["status_reason"]


def test_non_json_response(enabled):
    with patch("modules.lunar.requests.get", return_value=FakeResponse(raise_json=True)):
        result = LunarLookup().search_domain("example.com")
    assert result["status"] == "error"
    assert "non-JSON" in result["status_reason"]


def test_empty_domain(enabled):
    result = LunarLookup().search_domain("")
    assert result["status"] == "error"


def test_partial_report_does_not_crash(enabled):
    payload = {"status": "REPORT_READY", "report": {"summary": {"total_events": 5}}}
    with patch("modules.lunar.requests.get", return_value=FakeResponse(payload=payload)):
        result = LunarLookup().search_domain("example.com")
    assert result["status"] == "ok"
    assert result["total_events"] == 5
    assert result["malware_families"] == []
    assert result["monthly_timeline"] == []
