"""crt.sh stays primary; certspotter answers only when crt.sh fails (#379)."""

import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.cert_transparency import CertTransparency  # noqa: E402

CRTSH_OK = [
    {"id": 1, "entry_timestamp": "2026-01-01T00:00:00", "not_before": "2026-01-01",
     "not_after": "2027-01-01", "common_name": "example.com",
     "issuer_name": "C=US, O=Let's Encrypt, CN=R11",
     "name_value": "example.com\nwww.example.com"},
]

# Shaped like a real api.certspotter.com/v1/issuances answer with
# expand=dns_names&expand=issuer. The certificate also covers unrelated domains.
CERTSPOTTER_OK = [
    {"id": "12809115180", "dns_names": ["example.com", "*.example.com", "api.example.com", "example.net"],
     "issuer": {"friendly_name": "Sectigo", "name": "C=GB, O=Sectigo Limited, CN=Sectigo R36"},
     "not_before": "2025-11-20T00:00:00Z", "not_after": "2026-11-20T23:59:59Z"},
    {"id": "12809115181", "dns_names": ["API.example.com", "mail.example.com", "example.org"],
     "issuer": {"name": "C=US, O=DigiCert Inc, CN=DigiCert Global G2"},
     "not_before": "2026-01-01T00:00:00Z", "not_after": "2027-01-01T00:00:00Z"},
]


class _Response:
    def __init__(self, status_code, payload=None, bad_json=False):
        self.status_code = status_code
        self._payload = payload
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("not json")
        return self._payload


def _route(monkeypatch, crtsh, certspotter):
    """Answer requests.get by host, recording which sources were asked."""
    calls = []

    def fake_get(url, **kwargs):
        if "crt.sh" in url:
            calls.append(("crt.sh", kwargs))
            answer = crtsh
        elif "certspotter" in url:
            calls.append(("certspotter", kwargs))
            answer = certspotter
        else:
            raise AssertionError(f"unexpected request to {url}")
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(requests, "get", fake_get)
    return calls


def test_healthy_crtsh_never_asks_the_fallback(monkeypatch):
    calls = _route(monkeypatch, _Response(200, CRTSH_OK), _Response(200, CERTSPOTTER_OK))

    result = CertTransparency().search("example.com")

    assert result["error"] is None
    assert result["source"] == "crt.sh"
    assert result["subdomains"] == ["example.com", "www.example.com"]
    assert [source for source, _ in calls] == ["crt.sh"]


@pytest.mark.parametrize(
    "crtsh",
    [
        pytest.param(_Response(502), id="502"),
        pytest.param(_Response(200, bad_json=True), id="unparseable"),
        pytest.param(requests.Timeout(), id="timeout"),
        pytest.param(requests.ConnectionError("unreachable"), id="unreachable"),
    ],
)
def test_crtsh_failure_falls_back_to_certspotter(monkeypatch, crtsh):
    calls = _route(monkeypatch, crtsh, _Response(200, CERTSPOTTER_OK))

    result = CertTransparency().search("example.com")

    assert result["error"] is None
    assert result["source"] == "certspotter"
    assert result["fallback_reason"]
    assert [source for source, _ in calls] == ["crt.sh", "certspotter"]


def test_fallback_subdomains_are_filtered_normalised_and_deduplicated(monkeypatch):
    _route(monkeypatch, _Response(503), _Response(200, CERTSPOTTER_OK))

    result = CertTransparency().search("example.com")

    # *.example.com folds into example.com, API.example.com into api.example.com,
    # and example.net / example.org from the same certificates are dropped.
    assert result["subdomains"] == ["api.example.com", "example.com", "mail.example.com"]
    assert result["total_certs"] == 2


def test_fallback_certificates_use_the_crtsh_shape(monkeypatch):
    _route(monkeypatch, _Response(503), _Response(200, CERTSPOTTER_OK))

    certs = CertTransparency().search("example.com")["certificates"]

    assert set(certs[0]) == {"id", "logged_at", "not_before", "not_after", "common_name", "issuer"}
    assert certs[0]["issuer"] == "Sectigo"
    # No friendly name: fall back to the full issuer name rather than nothing.
    assert certs[1]["issuer"] == "C=US, O=DigiCert Inc, CN=DigiCert Global G2"


def test_fallback_goes_through_the_module_proxy(monkeypatch):
    monkeypatch.setenv("MODULE_PROXY", "http://proxy.local:3128")
    calls = _route(monkeypatch, _Response(503), _Response(200, CERTSPOTTER_OK))

    CertTransparency().search("example.com")

    fallback_kwargs = dict(calls)["certspotter"]
    assert fallback_kwargs["proxies"] == {
        "http": "http://proxy.local:3128",
        "https": "http://proxy.local:3128",
    }


def test_both_sources_down_reports_both_errors(monkeypatch):
    _route(monkeypatch, _Response(502), _Response(429))

    result = CertTransparency().search("example.com")

    assert result["subdomains"] == []
    assert result["source"] is None
    assert "crt.sh returned status 502" in result["error"]
    assert "certspotter returned status 429" in result["error"]


def test_empty_crtsh_answer_is_not_a_failure(monkeypatch):
    # Zero certificates is an answer, not an outage, so the quota is not spent.
    calls = _route(monkeypatch, _Response(200, []), _Response(200, CERTSPOTTER_OK))

    result = CertTransparency().search("example.com")

    assert result["error"] is None
    assert result["subdomains"] == []
    assert [source for source, _ in calls] == ["crt.sh"]
