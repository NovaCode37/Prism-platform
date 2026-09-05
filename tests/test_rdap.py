import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.rdap import RDAPLookup
from modules.module_status import classify, OK, SKIPPED, ERROR


class FakeResponse:
    def __init__(self, status_code=200, data=None, headers=None):
        self.status_code = status_code
        self._data = data or {}
        self.headers = headers or {}

    def json(self):
        return self._data


REGISTERED_RESPONSE = {
    "handle": "123456789_DOMAIN_COM-VRSN",
    "ldhName": "example.com",
    "registrationDate": "1995-08-14T04:00:00Z",
    "expirationDate": "2025-08-13T04:00:00Z",
    "events": [
        {"eventAction": "registration", "eventDate": "1995-08-14T04:00:00Z"},
        {"eventAction": "expiration", "eventDate": "2025-08-13T04:00:00Z"},
        {"eventAction": "last changed", "eventDate": "2023-05-01T12:00:00Z"},
    ],
    "entities": [
        {
            "handle": "REG-123",
            "fn": "Example Registrar",
            "roles": ["registrar"],
        },
        {
            "handle": "R-001",
            "fn": "Domain Owner",
            "roles": ["registrant"],
            "vcardArray": [
                "vcard",
                [
                    ["fn", {}, "Domain Owner"],
                    ["org", {}, "Example Corp"],
                    ["email", {}, "admin@example.com"],
                    ["tel", {}, "+1-555-123-4567"],
                    ["adr", {}, ["", "", "123 Main St", "Anytown", "CA", "90210", "US"]],
                ],
            ],
        },
    ],
    "nameservers": [
        {"ldhName": "ns1.example.com"},
        {"ldhName": "ns2.example.com"},
    ],
}


def test_rdap_lookup_registered_domain(monkeypatch):
    with patch("modules.rdap.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(200, REGISTERED_RESPONSE)
        rdap = RDAPLookup()
        result = rdap.lookup("example.com")
        assert classify(result) == OK
        assert result["domain"] == "example.com"
        assert result["status"] == "registered"
        assert result["created"] == "1995-08-14T04:00:00Z"
        assert result["expires"] == "2025-08-13T04:00:00Z"
        assert result["updated"] == "2023-05-01T12:00:00Z"
        assert result["registrar"] == "Example Registrar"
        assert "ns1.example.com" in result["nameservers"]
        assert "ns2.example.com" in result["nameservers"]
        assert result["registrant"] is not None
        assert result["registrant"].get("name") == "Domain Owner"
        assert result["registrant"].get("email") == "admin@example.com"
        assert result["error"] is None


def test_rdap_lookup_unregistered_domain(monkeypatch):
    with patch("modules.rdap.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(404, {})
        rdap = RDAPLookup()
        result = rdap.lookup("notarealdomain123456789.com")
        assert classify(result) == OK
        assert result["status"] == "unregistered"
        assert result["error"] is None


def test_rdap_lookup_empty_domain():
    rdap = RDAPLookup()
    result = rdap.lookup("")
    assert classify(result) == ERROR
    assert "No domain provided" in result["error"]


def test_rdap_lookup_invalid_domain():
    rdap = RDAPLookup()
    result = rdap.lookup("invalid@@domain")
    assert classify(result) == ERROR
    assert "Invalid domain format" in result["error"]


def test_rdap_lookup_tld_not_served(monkeypatch):
    with patch("modules.rdap.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(501, {})
        rdap = RDAPLookup()
        result = rdap.lookup("example.xx")
        assert classify(result) == SKIPPED
        assert "RDAP unavailable" in result["status_reason"]
        assert result["error"] is None


def test_rdap_lookup_rate_limited(monkeypatch):
    with patch("modules.rdap.requests.get") as mock_get:
        mock_get.return_value = FakeResponse(429, {})
        rdap = RDAPLookup()
        result = rdap.lookup("example.com")
        assert classify(result) == SKIPPED
        assert "rate limited" in result["status_reason"]
        assert result["error"] is None


def test_rdap_lookup_timeout(monkeypatch):
    import requests
    with patch("modules.rdap.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout()
        rdap = RDAPLookup()
        result = rdap.lookup("example.com")
        assert classify(result) == SKIPPED
        assert "timed out" in result["status_reason"]
        assert result["error"] is None


def test_rdap_lookup_connection_error(monkeypatch):
    import requests
    with patch("modules.rdap.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError()
        rdap = RDAPLookup()
        result = rdap.lookup("example.com")
        assert classify(result) == SKIPPED
        assert "connection" in result["status_reason"]
        assert result["error"] is None


def test_rdap_bootstrap_loading(monkeypatch):
    bootstrap_data = {
        "services": [
            [
                ["com", "net", "org"],
                ["https://rdap.verisign.com/com/v1/", "https://rdap.verisign.com/net/v1/"],
            ],
            [["de"], ["https://rdap.denic.de/"]],
        ]
    }
    with patch("modules.rdap.requests.get") as mock_get:
        mock_get.side_effect = [
            FakeResponse(200, bootstrap_data),
            FakeResponse(200, REGISTERED_RESPONSE),
        ]
        rdap = RDAPLookup()
        result = rdap.lookup("example.com")
        assert mock_get.call_count == 2
        first_call = mock_get.call_args_list[0]
        assert first_call[0][0] == "https://data.iana.org/rdap/dns.json"
        second_call = mock_get.call_args_list[1]
        assert "rdap.verisign.com" in second_call[0][0]
        assert "example.com" in second_call[0][0]
        assert classify(result) == OK


def test_rdap_bootstrap_fallback(monkeypatch):
    with patch("modules.rdap.requests.get") as mock_get:
        mock_get.side_effect = [
            FakeResponse(404, {}),
            FakeResponse(200, REGISTERED_RESPONSE),
        ]
        rdap = RDAPLookup()
        result = rdap.lookup("example.com")
        assert mock_get.call_count == 2
        second_call = mock_get.call_args_list[1]
        assert "rdap.org" in second_call[0][0]
        assert classify(result) == OK


def test_rdap_lookup_redirect_following(monkeypatch):
    with patch("modules.rdap.requests.get") as mock_get:
        redirect_response = FakeResponse(
            302,
            {},
            {"location": "https://rdap.verisign.com/com/v1/domain/example.com"},
        )
        mock_get.side_effect = [
            redirect_response,
            FakeResponse(200, REGISTERED_RESPONSE),
        ]
        rdap = RDAPLookup()
        result = rdap.lookup("example.com")
        assert mock_get.call_count == 2
        second_call = mock_get.call_args_list[1]
        assert "rdap.verisign.com" in second_call[0][0]
        assert classify(result) == OK