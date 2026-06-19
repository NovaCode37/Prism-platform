import importlib
import os
import sys

from fastapi import Request
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


PROXY_ENV = (
    "PRISM_BASE_PATH",
    "TRUST_PROXY_HEADERS",
    "FORWARDED_ALLOW_IPS",
    "TRUSTED_HOSTS",
    "PRISM_FRONTEND_DIR",
    "PRISM_UI_API_KEY",
    "NEXT_PUBLIC_API_URL",
    "API_KEY",
    "API_KEYS",
    "ALLOW_ANON_API",
)


def _load_app(monkeypatch, **env):
    for key in PROXY_ENV:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for module in ("web.app", "web.security"):
        sys.modules.pop(module, None)
    return importlib.import_module("web.app")


def _get(app, path, headers=None):
    with TestClient(app) as client:
        return client.get(path, headers=headers or {})


def _get_json(app, path, headers=None):
    response = _get(app, path, headers=headers)
    return response.status_code, response.json()


def _move_latest_route_before_frontend_fallback(app):
    latest = app.router.routes.pop()
    fallback_index = next(
        index for index, route in enumerate(app.router.routes)
        if getattr(route, "path", None) == "/{full_path:path}"
    )
    app.router.routes.insert(fallback_index, latest)


def test_normalize_base_path():
    from web.security import normalize_base_path

    assert normalize_base_path("") == ""
    assert normalize_base_path("/") == ""
    assert normalize_base_path("prism") == "/prism"
    assert normalize_base_path("/prism/") == "/prism"


def test_app_uses_configured_root_path(monkeypatch):
    app_mod = _load_app(monkeypatch, PRISM_BASE_PATH="/prism/")

    assert app_mod.app.root_path == "/prism"


def test_healthz_is_available_without_api_key(monkeypatch):
    app_mod = _load_app(monkeypatch)

    status, body = _get_json(app_mod.app, "/healthz")

    assert status == 200
    assert body == {"status": "ok"}


def test_crypto_route_is_registered(monkeypatch):
    app_mod = _load_app(monkeypatch)
    routes = {
        (route.path, method)
        for route in app_mod.app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("/api/crypto", "POST") in routes


def test_serves_next_index_with_runtime_config(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "out"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html><head></head><body>PRISM Next</body></html>", encoding="utf-8")
    app_mod = _load_app(
        monkeypatch,
        PRISM_FRONTEND_DIR=str(frontend_dir),
        PRISM_BASE_PATH="/prism",
        PRISM_UI_API_KEY="public-browser-key",
        NEXT_PUBLIC_API_URL="https://api.example.com",
    )

    response = _get(app_mod.app, "/")
    text = response.text

    assert response.status_code == 200
    assert "PRISM Next" in text
    assert 'window.__PRISM_CONFIG__={"apiUrl":"https://api.example.com","apiKey":"public-browser-key","basePath":"/prism"}' in text


def test_serves_next_static_asset(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "out"
    asset_dir = frontend_dir / "_next" / "static"
    asset_dir.mkdir(parents=True)
    (frontend_dir / "index.html").write_text("<html><head></head><body>PRISM Next</body></html>", encoding="utf-8")
    (asset_dir / "app.js").write_text("console.log('ok');", encoding="utf-8")
    app_mod = _load_app(monkeypatch, PRISM_FRONTEND_DIR=str(frontend_dir))

    response = _get(app_mod.app, "/_next/static/app.js")

    assert response.status_code == 200
    assert response.content == b"console.log('ok');"


def test_reserved_paths_are_not_spa_fallback(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "out"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html><head></head><body>PRISM Next</body></html>", encoding="utf-8")
    app_mod = _load_app(monkeypatch, PRISM_FRONTEND_DIR=str(frontend_dir))

    response = _get(app_mod.app, "/api/not-real")

    assert response.status_code == 404
    assert "PRISM Next" not in response.text


def test_forwarded_headers_are_ignored_by_default(monkeypatch):
    app_mod = _load_app(monkeypatch)

    @app_mod.app.get("/_proxy-probe", include_in_schema=False)
    async def proxy_probe(request: Request):
        return {
            "client": request.client.host if request.client else None,
            "scheme": request.url.scheme,
        }
    _move_latest_route_before_frontend_fallback(app_mod.app)

    _status, body = _get_json(
        app_mod.app,
        "/_proxy-probe",
        headers={
            "x-forwarded-for": "203.0.113.9",
            "x-forwarded-proto": "https",
        },
    )

    assert body == {"client": "testclient", "scheme": "http"}


def test_forwarded_headers_are_used_for_trusted_proxy(monkeypatch):
    app_mod = _load_app(
        monkeypatch,
        TRUST_PROXY_HEADERS="true",
        FORWARDED_ALLOW_IPS="testclient",
    )

    @app_mod.app.get("/_trusted-proxy-probe", include_in_schema=False)
    async def trusted_proxy_probe(request: Request):
        return {
            "client": request.client.host if request.client else None,
            "scheme": request.url.scheme,
        }
    _move_latest_route_before_frontend_fallback(app_mod.app)

    _status, body = _get_json(
        app_mod.app,
        "/_trusted-proxy-probe",
        headers={
            "x-forwarded-for": "203.0.113.9",
            "x-forwarded-proto": "https",
        },
    )

    assert body == {"client": "203.0.113.9", "scheme": "https"}


def test_forwarded_headers_require_allowed_proxy(monkeypatch):
    app_mod = _load_app(
        monkeypatch,
        TRUST_PROXY_HEADERS="true",
        FORWARDED_ALLOW_IPS="127.0.0.1",
    )

    @app_mod.app.get("/_untrusted-proxy-probe", include_in_schema=False)
    async def untrusted_proxy_probe(request: Request):
        return {
            "client": request.client.host if request.client else None,
            "scheme": request.url.scheme,
        }
    _move_latest_route_before_frontend_fallback(app_mod.app)

    _status, body = _get_json(
        app_mod.app,
        "/_untrusted-proxy-probe",
        headers={
            "x-forwarded-for": "203.0.113.9",
            "x-forwarded-proto": "https",
        },
    )

    assert body == {"client": "testclient", "scheme": "http"}
