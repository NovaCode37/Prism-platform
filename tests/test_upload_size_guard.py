import asyncio
import importlib
import os
import sys

from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


UPLOAD_ENV = (
    "MAX_UPLOAD_MB",
    "API_KEY",
    "API_KEYS",
    "ALLOW_ANON_API",
    "TRUSTED_HOSTS",
    "TRUST_PROXY_HEADERS",
)


def _load_app(monkeypatch):
    for key in UPLOAD_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setenv("ALLOW_ANON_API", "true")
    for module in ("web.app", "web.security"):
        sys.modules.pop(module, None)
    return importlib.import_module("web.app")


def _chunked_asgi(app, body: bytes, chunk_size: int = 1024):
    """ASGI wrapper: strips Content-Length and feeds the body in chunks,
    like a chunked-transfer-encoding upload."""

    async def wrapped(scope, receive, send):
        if scope.get("type") != "http":
            await app(scope, receive, send)
            return
        scope = {**scope, "client": ("198.51.100.1", 50000)}
        headers = [(k, v) for k, v in scope["headers"] if k != b"content-length"]
        scope = {**scope, "headers": headers}

        sent = 0

        async def chunked_receive():
            nonlocal sent
            if sent < len(body):
                piece = body[sent:sent + chunk_size]
                sent += len(piece)
                return {"type": "http.request", "body": piece, "more_body": True}
            return {"type": "http.request", "body": b"", "more_body": False}

        await app(scope, chunked_receive, send)

    return wrapped


def _multipart_body(filename: str, content: bytes) -> bytes:
    boundary = "----prism-test-boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: image/png\r\n"
        "\r\n"
    ).encode("ascii") + content + f"\r\n--{boundary}--\r\n".encode("ascii")
    return body


def test_metadata_rejects_oversized_chunked_upload_without_content_length(monkeypatch):
    import httpx

    from web import security

    app_mod = _load_app(monkeypatch)
    max_bytes = security.MAX_UPLOAD_BYTES

    content = b"x" * (max_bytes + 1024)
    body = _multipart_body("big.png", content)

    transport = httpx.ASGITransport(app=_chunked_asgi(app_mod.app, body))
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

    async def run():
        async with client:
            return await client.post(
                "/api/metadata",
                headers={
                    "content-type": "multipart/form-data; boundary=----prism-test-boundary",
                },
            )

    response = asyncio.new_event_loop().run_until_complete(run())

    assert response.status_code == 413, f"expected 413, got {response.status_code}: {response.text[:200]}"


def test_check_upload_size_rejects_non_numeric_content_length():
    from web import security

    class FakeRequest:
        headers = {"content-length": "abc"}

    try:
        asyncio.new_event_loop().run_until_complete(security.check_upload_size(FakeRequest()))
    except HTTPException as exc:
        assert exc.status_code == 400
    except ValueError:
        raise AssertionError(
            "non-numeric Content-Length raised ValueError (500) instead of HTTP 400"
        )
    else:
        raise AssertionError("non-numeric Content-Length did not raise HTTPException")
