import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.github_recon import GitHubRecon
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
    assert r["commit_emails_checked"] is True
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


def _profile_then(repos_resp, events_resp):
    def fake_get(url, **kwargs):
        if url.endswith("/users/octocat"):
            return _Resp(200, {"login": "octocat", "name": "The Octocat",
                               "email": "octo@example.com", "public_repos": 42})
        if "/repos" in url:
            return repos_resp
        if "/events/public" in url:
            return events_resp
        return _Resp(404, {})
    return fake_get


def test_lookup_repos_rate_limited_keeps_profile(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _profile_then(
        _Resp(403, {}),
        _Resp(200, [{"payload": {"commits": [{"author": {"email": "dev@example.com"}}]}}]),
    ))
    r = GitHubRecon().lookup("octocat")

    assert classify(r) == RATE_LIMITED
    assert "GITHUB_TOKEN" in r["status_reason"]
    assert r["error"] is None
    assert r["profile"]["name"] == "The Octocat"
    assert r["profile"]["public_repos"] == 42
    assert r["repo_count"] is None
    assert r["emails"] == ["octo@example.com", "dev@example.com"]


def test_lookup_events_rate_limited_preserves_profile_email_and_marks_unchecked(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _profile_then(
        _Resp(200, [{"language": "Go", "stargazers_count": 2}]),
        _Resp(403, {}),
    ))
    r = GitHubRecon().lookup("octocat")

    assert classify(r) == RATE_LIMITED
    assert "GITHUB_TOKEN" in r["status_reason"]
    assert r["profile"]["public_repos"] == 42
    assert r["repo_count"] == 1
    assert r["total_stars"] == 2
    assert r["emails"] == ["octo@example.com"]
    assert r["commit_emails_checked"] is False


def test_lookup_followup_error_keeps_profile(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _profile_then(_Resp(500, {}), _Resp(200, [])))
    r = GitHubRecon().lookup("octocat")

    assert classify(r) == ERROR
    assert r["error"] == "GitHub API returned 500"
    assert r["profile"]["public_repos"] == 42
    assert r["repo_count"] is None
    assert r["emails"] == ["octo@example.com"]


def test_lookup_followup_exception_is_an_error(monkeypatch):
    import requests

    def fake_get(url, **kwargs):
        if url.endswith("/users/octocat"):
            return _Resp(200, {"login": "octocat", "public_repos": 42})
        raise requests.ConnectionError("connection reset")

    monkeypatch.setattr(requests, "get", fake_get)
    r = GitHubRecon().lookup("octocat")

    assert classify(r) == ERROR
    assert "connection reset" in r["error"]
    assert r["profile"]["public_repos"] == 42
    assert r["repo_count"] is None
    assert r["emails"] == []
    assert r["commit_emails_checked"] is False


def test_lookup_no_emails_found_is_ok_and_empty(monkeypatch):
    import requests

    def fake_get(url, **kwargs):
        if url.endswith("/users/octocat"):
            return _Resp(200, {"login": "octocat", "public_repos": 0})
        return _Resp(200, [])

    monkeypatch.setattr(requests, "get", fake_get)
    r = GitHubRecon().lookup("octocat")

    assert classify(r) == OK
    assert r["repo_count"] == 0
    assert r["emails"] == []
