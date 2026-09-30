"""MODULE_PROXY and LLM_PROXY accept socks5:// URLs, so SOCKS support must ship (#377).

``requests`` only speaks SOCKS when PySocks is installed. It used to arrive by
accident, as a dependency of maigret in requirements.txt, and was missing from
requirements-web.txt, which is what the Docker image installs.
"""

import os
import re
import socket
import struct
import sys
import threading

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules import get_proxies  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
# TEST-NET-3 address: never routed, so a request can only succeed via the stub proxy.
TARGET = "http://203.0.113.10/check"


@pytest.mark.parametrize("requirements_file", ["requirements.txt", "requirements-web.txt"])
def test_requirements_install_socks_support_explicitly(requirements_file):
    with open(os.path.join(ROOT, requirements_file), encoding="utf-8") as handle:
        lines = [line.strip() for line in handle]

    assert any(re.match(r"^requests\[[^\]]*\bsocks\b[^\]]*\]", line) for line in lines), (
        f"{requirements_file} must depend on requests[socks], not rely on another "
        "package pulling PySocks in"
    )


class _StubProxy:
    """One-connection proxy on localhost that records what it was asked to reach."""

    def __init__(self, handler):
        self._listener = socket.socket()
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self._listener.settimeout(5)
        self.port = self._listener.getsockname()[1]
        self.seen = []
        self._handler = handler
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        try:
            conn, _ = self._listener.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(5)
            try:
                self._handler(conn, self.seen)
            except OSError:
                pass

    def close(self):
        self._listener.close()
        self._thread.join(5)


def _recv_exact(conn, size):
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise OSError("connection closed")
        data += chunk
    return data


_OK = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"


def _socks5_handler(conn, seen):
    version, method_count = _recv_exact(conn, 2)
    assert version == 5
    _recv_exact(conn, method_count)
    conn.sendall(b"\x05\x00")  # no authentication

    version, command, _reserved, address_type = _recv_exact(conn, 4)
    assert (version, command) == (5, 1)  # CONNECT
    if address_type == 1:
        host = socket.inet_ntoa(_recv_exact(conn, 4))
    elif address_type == 3:
        host = _recv_exact(conn, _recv_exact(conn, 1)[0]).decode()
    else:
        raise OSError(f"unexpected address type {address_type}")
    (port,) = struct.unpack("!H", _recv_exact(conn, 2))
    seen.append(("CONNECT", host, port))
    conn.sendall(b"\x05\x00\x00\x01" + socket.inet_aton("0.0.0.0") + b"\x00\x00")

    request = b""
    while b"\r\n\r\n" not in request:
        request += conn.recv(1024)
    seen.append(("REQUEST", request.split(b"\r\n", 1)[0].decode()))
    conn.sendall(_OK)


def _http_proxy_handler(conn, seen):
    request = b""
    while b"\r\n\r\n" not in request:
        request += conn.recv(1024)
    seen.append(("REQUEST", request.split(b"\r\n", 1)[0].decode()))
    conn.sendall(_OK)


def test_socks5_module_proxy_routes_the_request_through_the_proxy(monkeypatch):
    proxy = _StubProxy(_socks5_handler)
    monkeypatch.setenv("MODULE_PROXY", f"socks5://127.0.0.1:{proxy.port}")
    try:
        # Without PySocks this raises InvalidSchema: "Missing dependencies for SOCKS support".
        response = requests.get(TARGET, proxies=get_proxies(), timeout=5)
    finally:
        proxy.close()

    assert response.status_code == 200
    assert response.text == "ok"
    assert ("CONNECT", "203.0.113.10", 80) in proxy.seen
    assert ("REQUEST", "GET /check HTTP/1.1") in proxy.seen


def test_http_module_proxy_still_works(monkeypatch):
    proxy = _StubProxy(_http_proxy_handler)
    monkeypatch.setenv("MODULE_PROXY", f"http://127.0.0.1:{proxy.port}")
    try:
        response = requests.get(TARGET, proxies=get_proxies(), timeout=5)
    finally:
        proxy.close()

    assert response.status_code == 200
    assert proxy.seen == [("REQUEST", f"GET {TARGET} HTTP/1.1")]
