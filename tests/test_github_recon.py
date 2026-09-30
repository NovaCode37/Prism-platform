import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.github_recon import GitHubRecon
from modules.module_status import classify, OK, RATE_LIMITED


class _Resp:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


def test_lookup_success(monkeypatch):
    import requests

    def fake_get(url, **kwargs):
        if url.endswith("/users/octocat"):
            return _Resp(200, {
                "login": "octocat", "name": "The Octocat", "location": "San Francisco",
                "email": "octo@example.com", "followers": 100, "following": 5,
                "public_repos": 8, "type": "User",
                "created_at": "2011-01-25T18:44:36Z", "html_url": "https://github.com/octocat",
            })
        if "/repos" in url:
            return _Resp(200, [
                {"language": "Python", "stargazers_count": 5},
                {"language": "Python", "stargazers_count": 3},
                {"language": "Go", "stargazers_count": 1},
            ])
        if "/events/public" in url:
            return _Resp(200, [
                {"payload": {"commits": [
                    {"author": {"email": "dev@example.com"}},
                    {"author": {"email": "123+octocat@users.noreply.github.com"}},
                ]}},
            ])
        return _Resp(404, {})

    monkeypatch.setattr(requests, "get", fake_get)
    r = GitHubRecon().lookup("@octocat")

    assert classify(r) == OK
    assert r["profile"]["name"] == "The Octocat"
    assert r["repo_count"] == 3
    assert r["total_stars"] == 9
    assert r["top_languages"][0]["language"] == "Python"
    assert "octo@example.com" in r["emails"]
    assert "dev@example.com" in r["emails"]
    # noreply emails are filtered out
    assert all("noreply" not in e for e in r["emails"])


def test_lookup_not_found(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda url, **kw: _Resp(404, {}))
    r = GitHubRecon().lookup("definitely-not-a-real-user-xyz")
    assert r["error"] == "GitHub user not found"


def test_lookup_rate_limited(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda url, **kw: _Resp(403, {}))
    r = GitHubRecon().lookup("octocat")
    assert classify(r) == RATE_LIMITED
    assert r["error"] is None


def test_lookup_empty_username():
    r = GitHubRecon().lookup("")
    assert classify(r) == "error"
