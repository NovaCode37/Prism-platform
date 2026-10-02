import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _stub_httpx_client(monkeypatch, app_mod, fake_post=None):
    settings = {}

    class FakeClient:
        def __init__(self, timeout, follow_redirects, **kwargs):
            settings.update(
                timeout=timeout,
                follow_redirects=follow_redirects,
                **kwargs,
            )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def build_request(self, method, url, json=None, headers=None, extensions=None):
            return {
                "method": method,
                "url": url,
                "json": json,
                "headers": headers,
                "extensions": extensions,
            }

        def send(self, request, follow_redirects=None):
            settings["request"] = request
            if fake_post is not None:
                return fake_post(
                    request["url"], json=request["json"], headers=request["headers"],
                    timeout=settings["timeout"],
                    allow_redirects=follow_redirects,
                )

    monkeypatch.setattr(app_mod.httpx, "Client", FakeClient)
    return settings


class TestWebhookValidation:
    def test_rejects_non_http_scheme(self):
        from web.app import _validate_webhook_url
        with pytest.raises(ValueError):
            _validate_webhook_url("ftp://example.com/hook")

    def test_rejects_empty(self):
        from web.app import _validate_webhook_url
        with pytest.raises(ValueError):
            _validate_webhook_url("")

    def test_rejects_loopback(self, monkeypatch):
        from web.app import _validate_webhook_url
        monkeypatch.setattr("socket.gethostbyname", lambda h: "127.0.0.1")
        with pytest.raises(ValueError):
            _validate_webhook_url("http://localhost/hook")

    def test_rejects_private_ip(self, monkeypatch):
        from web.app import _validate_webhook_url
        monkeypatch.setattr("socket.gethostbyname", lambda h: "10.0.0.5")
        with pytest.raises(ValueError):
            _validate_webhook_url("http://internal.example/hook")

    def test_accepts_public_url(self, monkeypatch):
        from web import app as app_mod
        monkeypatch.setattr("socket.gethostbyname", lambda h: "93.184.216.34")
                                                                         
        monkeypatch.setattr(app_mod._requests, "head", lambda *a, **kw: (_ for _ in ()).throw(Exception("nope")))
        result = app_mod._validate_webhook_url("https://hooks.example.com/prism")
        assert result == "https://hooks.example.com/prism"


class TestWebhookDelivery:
    def test_sends_post_with_payload(self, monkeypatch):
        from web import app as app_mod
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None, allow_redirects=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            captured["allow_redirects"] = allow_redirects

        settings = _stub_httpx_client(monkeypatch, app_mod, fake_post)
        monkeypatch.setattr(app_mod, "_resolve_all_public", lambda h: "93.184.216.34")
        monkeypatch.setattr(app_mod, "WEBHOOK_SECRET", "shh")
        payload = {"scan_id": "abc", "status": "completed"}
        app_mod._send_webhook("https://hooks.example.com/prism", payload)

        assert str(captured["url"]) == "https://93.184.216.34/prism"
        assert captured["json"] == payload
        assert captured["headers"]["X-Prism-Secret"] == "shh"
        assert captured["headers"]["Content-Type"] == "application/json"
        assert captured["headers"]["Host"] == "hooks.example.com"
        assert settings["request"]["extensions"]["sni_hostname"] == "hooks.example.com"
        assert captured["allow_redirects"] is False
        assert settings["verify"] is True
        assert settings["trust_env"] is False

    def test_swallows_post_errors(self, monkeypatch):
        from web import app as app_mod

        def boom(*a, **kw):
            raise RuntimeError("network down")

        _stub_httpx_client(monkeypatch, app_mod, boom)
        monkeypatch.setattr(app_mod, "_resolve_all_public", lambda h: "93.184.216.34")
                        
        app_mod._send_webhook("https://hooks.example.com/prism", {"x": 1})

    def test_pins_delivery_to_first_resolution(self, monkeypatch):
        from web import app as app_mod
        resolutions = []
        connected = []
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received["host"] = self.headers.get("Host")
                received["body"] = self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(204)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        original_getaddrinfo = socket.getaddrinfo

        def resolve(hostname, port, *args, **kwargs):
            if hostname == "hooks.example.com":
                resolutions.append(hostname)
                address = "93.184.216.34" if len(resolutions) == 1 else "10.0.0.1"
                return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 0))]
            return original_getaddrinfo(hostname, port, *args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", resolve)
        original_connect = socket.create_connection

        def connect(address, *args, **kwargs):
            connected.append(address)
            if address[0] == "93.184.216.34":
                address = ("127.0.0.1", address[1])
            return original_connect(address, *args, **kwargs)

        monkeypatch.setattr(socket, "create_connection", connect)

        url = f"http://hooks.example.com:{server.server_port}/prism"
        try:
            app_mod._send_webhook(url, {"x": 1})
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join()

        assert resolutions == ["hooks.example.com"]
        assert connected == [("93.184.216.34", server.server_port)]
        assert received["host"] == f"hooks.example.com:{server.server_port}"
        assert received["body"] == b'{"x":1}'


class TestTestWebhookEndpoint:
    """Tests for POST /api/watchlist/test-webhook"""

    def _client(self, monkeypatch, fake_post=None):
        from web import app as app_mod
        from web import security
        from fastapi.testclient import TestClient

        monkeypatch.setattr(security, "_API_KEYS", ["test-key"])
        monkeypatch.setattr("socket.gethostbyname", lambda h: "93.184.216.34")
        _stub_httpx_client(monkeypatch, app_mod, fake_post)
        return TestClient(app_mod.app, raise_server_exceptions=True)

    def test_returns_ok_on_success(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None, allow_redirects=None):
            captured["url"] = url
            captured["json"] = json

        client = self._client(monkeypatch, fake_post)
        resp = client.post(
            "/api/watchlist/test-webhook",
            json={"webhook_url": "https://hooks.example.com/prism"},
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert captured["json"]["event"] == "watchlist_test"

    def test_rejects_private_url(self, monkeypatch):
        from web import app as app_mod
        from web import security
        from fastapi.testclient import TestClient

        monkeypatch.setattr(security, "_API_KEYS", ["test-key"])
        monkeypatch.setattr("socket.gethostbyname", lambda h: "10.0.0.1")
        client = TestClient(app_mod.app, raise_server_exceptions=True)
        resp = client.post(
            "/api/watchlist/test-webhook",
            json={"webhook_url": "http://internal.corp/hook"},
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 400
        assert "error" in resp.json()

    def test_rejects_invalid_scheme(self, monkeypatch):
        client = self._client(monkeypatch)
        resp = client.post(
            "/api/watchlist/test-webhook",
            json={"webhook_url": "ftp://example.com/hook"},
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 400

    def test_requires_api_key(self, monkeypatch):
        from web import app as app_mod
        from web import security
        from fastapi.testclient import TestClient

        monkeypatch.setattr(security, "_API_KEYS", ["test-key"])
        client = TestClient(app_mod.app, raise_server_exceptions=True)
        resp = client.post(
            "/api/watchlist/test-webhook",
            json={"webhook_url": "https://hooks.example.com/prism"},
        )
        assert resp.status_code in (401, 403)

    def test_payload_shape(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None, allow_redirects=None):
            captured["json"] = json

        client = self._client(monkeypatch, fake_post)
        client.post(
            "/api/watchlist/test-webhook",
            json={"webhook_url": "https://hooks.example.com/prism"},
            headers={"X-API-Key": "test-key"},
        )
        payload = captured["json"]
        assert payload["event"] == "watchlist_test"
        assert "target" in payload
        assert "added" in payload
        assert "changes" in payload

    def test_delivery_failure_does_not_leak_exception_text(self, monkeypatch):
        from web import app as app_mod

        def boom(url, payload):
            raise RuntimeError("connection to internal.example failed")

        client = self._client(monkeypatch)
        monkeypatch.setattr(app_mod, "_send_webhook", boom)
        resp = client.post(
            "/api/watchlist/test-webhook",
            json={"webhook_url": "https://hooks.example.com/prism"},
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 502
        assert "internal.example" not in resp.text
        assert "could not be delivered" in resp.json()["error"]

    def test_delivery_failure_includes_http_status_when_available(self, monkeypatch):
        from web import app as app_mod

        class FakeDeliveryError(RuntimeError):
            def __init__(self):
                super().__init__("upstream refused")
                self.response = type("Response", (), {"status_code": 503})()

        def boom(url, payload):
            raise FakeDeliveryError()

        client = self._client(monkeypatch)
        monkeypatch.setattr(app_mod, "_send_webhook", boom)
        resp = client.post(
            "/api/watchlist/test-webhook",
            json={"webhook_url": "https://hooks.example.com/prism"},
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 502
        assert "(HTTP 503)" in resp.json()["error"]

class TestWebhookResolutionGuard:
    def _blocked(self, monkeypatch, error):
        from web import app as app_mod
        sent = []

        def fake_post(*a, **kw):
            sent.append(a)

        def refuse(hostname):
            raise ValueError(error)

        monkeypatch.setattr(app_mod._requests, "post", fake_post)
        monkeypatch.setattr(app_mod, "_resolve_all_public", refuse)
        app_mod._send_webhook("https://hooks.example.com/prism", {"x": 1})
        return sent

    def test_private_address_is_not_posted_to(self, monkeypatch):
        assert self._blocked(monkeypatch, "webhook_url resolves to a private/internal address") == []

    def test_unresolvable_host_is_not_posted_to(self, monkeypatch):
        assert self._blocked(monkeypatch, "webhook_url hostname cannot be resolved") == []

    def test_empty_resolution_is_not_posted_to(self, monkeypatch):
        assert self._blocked(monkeypatch, "webhook_url hostname did not resolve") == []
