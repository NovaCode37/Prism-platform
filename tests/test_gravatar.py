import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.gravatar import GravatarRecon
from modules.module_status import classify, OK, RATE_LIMITED, ERROR


class _Resp:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


def test_lookup_success(monkeypatch):
    import requests

    def fake_get(url, **kwargs):
        return _Resp(
            200,
            {
                "entry": [
                    {
                        "displayName": "Beau Lebens",
                        "thumbnailUrl": "https://0.gravatar.com/avatar/example",
                        "accounts": [
                            {
                                "name": "GitHub",
                                "display": "beaulebens",
                                "url": "https://github.com/beaulebens",
                            },
                            {
                                "name": "X",
                                "display": "@beaulebens",
                                "url": "https://x.com/beaulebens",
                            },
                        ],
                    }
                ]
            },
        )

    monkeypatch.setattr(requests, "get", fake_get)

    r = GravatarRecon().lookup("beau@automattic.com")

    assert classify(r) == OK
    assert r["email"] == "beau@automattic.com"
    assert r["display_name"] == "Beau Lebens"
    assert r["avatar_url"] == "https://0.gravatar.com/avatar/example"
    assert len(r["accounts"]) == 2
    assert r["accounts"][0]["name"] == "GitHub"
    assert r["error"] is None


def test_lookup_not_found(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "get", lambda url, **kw: _Resp(404, {}))

    r = GravatarRecon().lookup("missing@example.com")

    assert r["error"] == "Gravatar profile not found"
    assert r["display_name"] is None
    assert r["avatar_url"] is None
    assert r["accounts"] == []


def test_lookup_rate_limited(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "get", lambda url, **kw: _Resp(429, {}))

    r = GravatarRecon().lookup("beau@automattic.com")

    assert classify(r) == RATE_LIMITED
    assert r["error"] is None


def test_lookup_empty_email():
    r = GravatarRecon().lookup("")

    assert classify(r) == ERROR
    assert r["error"] == "No email provided"


def test_lookup_empty_entry(monkeypatch):
    import requests

    monkeypatch.setattr(
        requests,
        "get",
        lambda url, **kw: _Resp(200, {"entry": []}),
    )

    r = GravatarRecon().lookup("beau@automattic.com")

    assert r["error"] == "Gravatar profile not found"
    assert r["accounts"] == []


def test_lookup_server_error(monkeypatch):
    import requests

    monkeypatch.setattr(
        requests,
        "get",
        lambda url, **kw: _Resp(500, {}),
    )

    r = GravatarRecon().lookup("beau@automattic.com")

    assert classify(r) == ERROR
    assert "Gravatar API returned 500" in r["error"]