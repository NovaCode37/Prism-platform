import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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

        def fake_post(url, json=None, headers=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers

        monkeypatch.setattr(app_mod._requests, "post", fake_post)
        monkeypatch.setattr(app_mod, "_resolve_all_public", lambda h: None)
        monkeypatch.setattr(app_mod, "WEBHOOK_SECRET", "shh")
        payload = {"scan_id": "abc", "status": "completed"}
        app_mod._send_webhook("https://hooks.example.com/prism", payload)

        assert captured["url"] == "https://hooks.example.com/prism"
        assert captured["json"] == payload
        assert captured["headers"]["X-Prism-Secret"] == "shh"
        assert captured["headers"]["Content-Type"] == "application/json"

    def test_swallows_post_errors(self, monkeypatch):
        from web import app as app_mod

        def boom(*a, **kw):
            raise RuntimeError("network down")

        monkeypatch.setattr(app_mod._requests, "post", boom)
        monkeypatch.setattr(app_mod, "_resolve_all_public", lambda h: None)
                        
        app_mod._send_webhook("https://hooks.example.com/prism", {"x": 1})


class TestTestWebhookEndpoint:
    """Tests for POST /api/watchlist/test-webhook"""

    def _client(self, monkeypatch, fake_post=None):
        from web import app as app_mod
        from web import security
        from fastapi.testclient import TestClient

        monkeypatch.setattr(security, "_API_KEYS", ["test-key"])
        monkeypatch.setattr("socket.gethostbyname", lambda h: "93.184.216.34")
        monkeypatch.setattr(
            app_mod._requests, "head",
            lambda *a, **kw: (_ for _ in ()).throw(Exception("skip"))
        )
        if fake_post is not None:
            monkeypatch.setattr(app_mod._requests, "post", fake_post)
        return TestClient(app_mod.app, raise_server_exceptions=True)

    def test_returns_ok_on_success(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
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

        def fake_post(url, json=None, headers=None, timeout=None):
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
