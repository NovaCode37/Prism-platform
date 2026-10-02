import base64

import pytest
import requests

import modules.url_scanner as url_scanner


class MockResponse:
    def __init__(self, *, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def _expected_permalink(url: str) -> str:
    encoded = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    return f"https://www.virustotal.com/gui/url/{encoded}"


def test_scan_clean_result(monkeypatch):
    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "test-key")

    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(payload={"data": {"id": "analysis-123"}}),
    )
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: MockResponse(
            payload={
                "data": {
                    "attributes": {
                        "status": "completed",
                        "stats": {
                            "malicious": 0,
                            "suspicious": 0,
                            "harmless": 3,
                            "undetected": 2,
                        },
                        "categories": {"phishing": "malicious"},
                    }
                }
            }
        ),
    )

    result = url_scanner.URLScanner().scan("https://example.com")

    assert result["status"] == "completed"
    assert result["malicious"] == 0
    assert result["suspicious"] == 0
    assert result["harmless"] == 3
    assert result["undetected"] == 2
    assert result["categories"] == {"phishing": "malicious"}
    assert result["error"] is None
    assert result["permalink"] == _expected_permalink("https://example.com")


def test_scan_with_detections(monkeypatch):
    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "test-key")

    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(payload={"data": {"id": "analysis-456"}}),
    )
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: MockResponse(
            payload={
                "data": {
                    "attributes": {
                        "status": "completed",
                        "stats": {
                            "malicious": 2,
                            "suspicious": 1,
                            "harmless": 7,
                            "undetected": 3,
                        },
                    }
                }
            }
        ),
    )

    result = url_scanner.URLScanner().scan("https://example.com/evil")

    assert result["status"] == "completed"
    assert result["malicious"] == 2
    assert result["suspicious"] == 1
    assert result["harmless"] == 7
    assert result["undetected"] == 3
    assert result["permalink"] == _expected_permalink("https://example.com/evil")


def test_scan_permalink_shape(monkeypatch):
    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "test-key")

    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(payload={"data": {"id": "analysis-789"}}),
    )
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: MockResponse(
            payload={
                "data": {
                    "attributes": {
                        "status": "completed",
                        "stats": {
                            "malicious": 0,
                            "suspicious": 0,
                            "harmless": 1,
                            "undetected": 0,
                        },
                    }
                }
            }
        ),
    )

    target = "https://sub.example.com/path?x=1&y=2"
    result = url_scanner.URLScanner().scan(target)

    assert result["permalink"] == _expected_permalink(target)
    assert result["permalink"].startswith("https://www.virustotal.com/gui/url/")
    assert "=" not in result["permalink"].split("/gui/url/")[-1]


def test_scan_missing_api_key(monkeypatch):
    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "")

    result = url_scanner.URLScanner().scan("https://example.com")

    assert result["status"] == "skipped"
    assert result["status_reason"] == "No VirusTotal API key configured (add VIRUSTOTAL_API_KEY to .env)"
    assert result["error"] is None


@pytest.mark.parametrize("status_code", [401, 403])
def test_scan_auth_errors_are_not_hard_failures(monkeypatch, status_code):
    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "test-key")

    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(status_code=status_code, text="Unauthorized"),
    )

    result = url_scanner.URLScanner().scan("https://example.com")

    assert result["status"] == "error"
    assert str(status_code) in result["status_reason"]
    assert result["error"] == result["status_reason"]


def test_scan_rate_limit_comes_back_via_module_status(monkeypatch):
    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "test-key")

    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(status_code=429, text="Too Many Requests"),
    )

    result = url_scanner.URLScanner().scan("https://example.com")

    assert result["status"] == "rate_limited"
    assert result["status_reason"] == "VirusTotal API rate limit reached"
    assert result["error"] is None


def test_scan_bad_json_is_handled_as_error(monkeypatch):
    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "test-key")

    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(payload=None),
    )

    result = url_scanner.URLScanner().scan("https://example.com")

    assert result["status"] == "error"
    assert "not json" in result["status_reason"].lower()
    assert result["error"] == result["status_reason"]
