import importlib
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ORIGIN = "https://console.example.com"

CORS_ENV = (
    "ALLOWED_ORIGINS",
    "ALLOW_ANON_API",
    "API_KEY",
    "API_KEYS",
    "TRUSTED_HOSTS",
    "TRUST_PROXY_HEADERS",
)


def _load_app(monkeypatch):
    for key in CORS_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ALLOWED_ORIGINS", ORIGIN)
    monkeypatch.setenv("ALLOW_ANON_API", "true")
    for module in ("web.app", "web.security"):
        sys.modules.pop(module, None)
    return importlib.import_module("web.app")


def test_rate_limited_responses_still_carry_cors_headers(monkeypatch):
    app = _load_app(monkeypatch).app
    client = TestClient(app)
    headers = {"Origin": ORIGIN}

    limited = None
    for _ in range(400):
        response = client.get("/api/scans", headers=headers)
        if response.status_code == 429:
            limited = response
            break

    assert limited is not None
    assert limited.headers.get("access-control-allow-origin") == ORIGIN


def test_cors_middleware_is_the_outermost_one(monkeypatch):
    from fastapi.middleware.cors import CORSMiddleware

    app = _load_app(monkeypatch).app
    assert app.user_middleware[0].cls is CORSMiddleware
