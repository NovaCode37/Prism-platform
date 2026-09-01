import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.security import client_ip

PEER = "203.0.113.7"


class FakeRequest:
    def __init__(self, headers):
        self.headers = headers
        self.client = type("Client", (), {"host": PEER})()
        self.scope = {"client": (PEER, 1234)}


@pytest.mark.parametrize("headers", [
    {},
    {"X-Forwarded-For": "1.2.3.4"},
    {"X-Real-IP": "5.6.7.8"},
    {"X-Forwarded-For": "1.2.3.4, 9.9.9.9", "X-Real-IP": "5.6.7.8"},
])
def test_forwarded_headers_are_ignored_without_the_trust_flag(monkeypatch, headers):
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    assert client_ip(FakeRequest(headers)) == PEER


def test_forwarded_header_is_used_when_proxy_headers_are_trusted(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    assert client_ip(FakeRequest({"X-Forwarded-For": "1.2.3.4"})) == "1.2.3.4"


def test_real_ip_is_used_when_proxy_headers_are_trusted(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    assert client_ip(FakeRequest({"X-Real-IP": "5.6.7.8"})) == "5.6.7.8"


def test_trusted_proxy_falls_back_to_peer_without_headers(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    assert client_ip(FakeRequest({})) == PEER


def test_spoofed_headers_cannot_split_the_rate_limit_bucket(monkeypatch):
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    keys = {client_ip(FakeRequest({"X-Forwarded-For": f"10.0.0.{i}"})) for i in range(20)}
    assert keys == {PEER}
