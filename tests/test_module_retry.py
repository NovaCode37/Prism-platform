import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import modules as modules_pkg
from modules.cert_transparency import CertTransparency
from modules.wayback import WaybackMachine
from modules.module_status import ERROR, OK, RATE_LIMITED, classify


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = [] if data is None else data

    def json(self):
        return self._data


CERTS = [
    {
        "id": 1,
        "entry_timestamp": "2024-01-01T00:00:00",
        "not_before": "2024-01-01",
        "not_after": "2025-01-01",
        "common_name": "example.com",
        "issuer_name": "O=Test CA",
        "name_value": "example.com\nwww.example.com",
    }
]

CDX_ROWS = [
    ["timestamp", "statuscode", "mimetype", "length"],
    ["20200101120000", "200", "text/html", "12000"],
]

CDX_URL_ROWS = [
    ["original"],
    ["https://example.com/admin"],
]


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(modules_pkg, "RETRY_BACKOFF_SECONDS", 0)


def stub(monkeypatch, *outcomes, fallback=None):
    """Answer each request with the next outcome: a FakeResponse or an exception.

    `fallback` answers the certspotter request the CT module makes when crt.sh
    has failed (#379). It is not part of the outcome sequence, so a test about
    retries stays about retries: use `crt_sh_calls(calls)` to count the attempts
    against crt.sh itself.
    """
    calls = []

    def fake_get(url, **kwargs):
        calls.append({"url": url, "kwargs": kwargs})
        if fallback is not None and "certspotter" in url:
            if isinstance(fallback, Exception):
                raise fallback
            return fallback
        outcome = outcomes[len(crt_sh_calls(calls)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(requests, "get", fake_get)
    return calls


def crt_sh_calls(calls) -> list:
    """The calls that went to the retried source, without the CT fallback."""
    return [call for call in calls if "certspotter" not in call["url"]]


def test_crt_sh_503_is_retried_and_the_result_is_parsed(monkeypatch):
    calls = stub(monkeypatch, FakeResponse(503), FakeResponse(200, CERTS))

    result = CertTransparency().search("example.com")

    assert len(calls) == 2
    assert result["error"] is None
    assert result["total_certs"] == 1
    assert "www.example.com" in result["subdomains"]


def test_a_source_that_stays_down_still_reports_the_failure(monkeypatch):
    calls = stub(
        monkeypatch,
        *[FakeResponse(503)] * modules_pkg.RETRY_ATTEMPTS,
        fallback=FakeResponse(503),
    )

    result = CertTransparency().search("example.com")

    assert len(crt_sh_calls(calls)) == modules_pkg.RETRY_ATTEMPTS
    assert result["status"] == RATE_LIMITED
    assert "503" in result["status_reason"]
    assert "try again later" in result["status_reason"].lower()


def test_crtsh_429_after_retries_reports_rate_limit_if_fallback_fails(monkeypatch):
    calls = stub(
        monkeypatch,
        *[FakeResponse(429)] * modules_pkg.RETRY_ATTEMPTS,
        fallback=FakeResponse(503),
    )

    result = CertTransparency().search("example.com")

    assert len(crt_sh_calls(calls)) == modules_pkg.RETRY_ATTEMPTS
    assert result["status"] == RATE_LIMITED
    assert "try again later" in result["status_reason"].lower()


def test_an_answer_is_not_retried(monkeypatch):
    calls = stub(monkeypatch, FakeResponse(404), fallback=FakeResponse(404))

    result = CertTransparency().search("example.com")

    assert len(crt_sh_calls(calls)) == 1
    assert "404" in result["error"]


def test_a_timeout_is_retried(monkeypatch):
    calls = stub(monkeypatch, requests.Timeout("read timed out"), FakeResponse(200, CERTS))

    result = CertTransparency().search("example.com")

    assert len(calls) == 2
    assert result["error"] is None
    assert result["total_certs"] == 1


def test_timeouts_that_outlive_the_retries_keep_the_timeout_error(monkeypatch):
    calls = stub(
        monkeypatch,
        *[requests.Timeout("read timed out")] * modules_pkg.RETRY_ATTEMPTS,
        fallback=requests.Timeout("read timed out"),
    )

    result = CertTransparency().search("example.com")

    assert len(crt_sh_calls(calls)) == modules_pkg.RETRY_ATTEMPTS
    assert "timed out" in result["error"]
    assert result["status"] == ERROR


def test_empty_crtsh_answer_is_ok(monkeypatch):
    calls = stub(monkeypatch, FakeResponse(200, []))

    result = CertTransparency().search("example.com")

    assert len(crt_sh_calls(calls)) == 1
    assert result["status"] == OK
    assert result["error"] is None
    assert result["certificates"] == []


def test_cdx_snapshots_retry_a_transient_503(monkeypatch):
    calls = stub(monkeypatch, FakeResponse(503), FakeResponse(200, CDX_ROWS))

    result = WaybackMachine().get_snapshots("example.com")

    assert len(calls) == 2
    assert result["error"] is None
    assert result["total_snapshots"] == 1
    assert "web.archive.org" in result["snapshots"][0]["wayback_url"]


def test_cdx_url_harvest_retries_a_transient_504(monkeypatch):
    calls = stub(monkeypatch, FakeResponse(504), FakeResponse(200, CDX_URL_ROWS))

    result = WaybackMachine().get_all_urls("example.com")

    assert len(calls) == 2
    assert result["error"] is None
    assert result["urls"] == ["https://example.com/admin"]


def test_a_staying_down_cdx_api_still_reports_the_failure(monkeypatch):
    calls = stub(monkeypatch, *[FakeResponse(503)] * modules_pkg.RETRY_ATTEMPTS)

    result = WaybackMachine().get_snapshots("example.com")

    assert len(calls) == modules_pkg.RETRY_ATTEMPTS
    assert result["status"] == RATE_LIMITED
    assert "503" in result["status_reason"]
    assert "try again later" in result["status_reason"].lower()


def test_cdx_429_after_retries_reports_rate_limit(monkeypatch):
    calls = stub(monkeypatch, *[FakeResponse(429)] * modules_pkg.RETRY_ATTEMPTS)

    result = WaybackMachine().get_snapshots("example.com")

    assert len(calls) == modules_pkg.RETRY_ATTEMPTS
    assert result["status"] == RATE_LIMITED
    assert "try again later" in result["status_reason"].lower()


def test_cdx_timeout_after_retries_is_error(monkeypatch):
    calls = stub(
        monkeypatch,
        *[requests.Timeout("read timed out")] * modules_pkg.RETRY_ATTEMPTS,
    )

    result = WaybackMachine().get_snapshots("example.com")

    assert len(calls) == modules_pkg.RETRY_ATTEMPTS
    assert result["status"] == ERROR
    assert "timed out" in result["error"]


def test_empty_cdx_answers_are_ok(monkeypatch):
    stub(monkeypatch, FakeResponse(200, []))

    result = WaybackMachine().get_snapshots("example.com")

    assert result["status"] == OK
    assert result["error"] is None
    assert result["snapshots"] == []


def test_empty_cdx_url_harvest_is_ok(monkeypatch):
    stub(monkeypatch, FakeResponse(200, []))

    result = WaybackMachine().get_all_urls("example.com")

    assert result["status"] == OK
    assert result["error"] is None
    assert result["urls"] == []


@pytest.mark.parametrize("status_code", [429, 503])
def test_availability_rate_limit_is_annotated(monkeypatch, status_code):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse(status_code))

    result = WaybackMachine().check_availability("https://example.com")

    assert result["status"] == RATE_LIMITED
    assert "try again later" in result["status_reason"].lower()


def test_retries_reuse_the_proxies_and_the_per_attempt_timeout(monkeypatch):
    monkeypatch.setenv("MODULE_PROXY", "http://proxy.test:8080")
    calls = stub(monkeypatch, FakeResponse(502), FakeResponse(200, CERTS))

    result = CertTransparency().search("example.com")

    assert result["error"] is None
    assert len(calls) == 2
    for call in calls:
        assert call["kwargs"]["proxies"] == {
            "http": "http://proxy.test:8080",
            "https": "http://proxy.test:8080",
        }
        assert call["kwargs"]["timeout"] == 30
