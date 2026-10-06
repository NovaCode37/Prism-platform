import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import modules.darkweb_search as darkweb_mod
from modules.darkweb_search import DarkWebSearch
from modules.module_status import ERROR, OK, RATE_LIMITED, classify

TOR_LINK = "https://tor.link/api/search"
AHMIA = "https://ahmia.fi/search/"


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


def tor_link_hit(n):
    return {
        "title": f"Market {n}",
        "url": f"http://market{n}.onion/",
        "description": f"listing {n}",
        "onion": f"market{n}.onion",
        "rank": n,
    }


def stub(monkeypatch, answers):
    """Answer each backend URL with a FakeResponse or raise the given exception."""
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        answer = answers[url]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(darkweb_mod.requests, "get", fake_get)
    return calls


def test_tor_link_results_are_mapped_to_module_shape(monkeypatch):
    stub(monkeypatch, {TOR_LINK: FakeResponse(payload={"results": [tor_link_hit(1), tor_link_hit(2)]})})

    result = DarkWebSearch().search("example")

    assert result["source"] == "Tor.link"
    assert result["total"] == 2
    assert result["results"][0] == {
        "title": "Market 1",
        "url": "http://market1.onion/",
        "description": "listing 1",
        "onion": "market1.onion",
    }
    assert classify(result) == OK
    assert result["error"] is None


def test_limit_caps_the_results(monkeypatch):
    hits = [tor_link_hit(n) for n in range(25)]
    stub(monkeypatch, {TOR_LINK: FakeResponse(payload={"results": hits})})

    result = DarkWebSearch().search("example", limit=3)

    assert [r["title"] for r in result["results"]] == ["Market 0", "Market 1", "Market 2"]
    assert result["total"] == 3


def test_limit_counts_only_entries_that_are_kept(monkeypatch):
    hits = [{"url": "http://untitled.onion/"}] + [tor_link_hit(n) for n in range(5)]
    stub(monkeypatch, {TOR_LINK: FakeResponse(payload={"results": hits})})

    result = DarkWebSearch().search("example", limit=3)

    assert result["total"] == 3


def test_empty_result_is_an_answer_not_an_error(monkeypatch):
    calls = stub(monkeypatch, {TOR_LINK: FakeResponse(payload={"results": []})})

    result = DarkWebSearch().search("nothing-matches-this")

    assert result["results"] == []
    assert result["total"] == 0
    assert result["source"] == "Tor.link"
    assert classify(result) == OK
    assert calls == [TOR_LINK]


def test_tor_link_answer_is_not_lost_to_an_ahmia_outage(monkeypatch):
    stub(monkeypatch, {
        TOR_LINK: FakeResponse(payload={"results": [tor_link_hit(1)]}),
        AHMIA: FakeResponse(status_code=503),
    })

    result = DarkWebSearch().search("example")

    assert result["total"] == 1
    assert result["source"] == "Tor.link"
    assert classify(result) == OK


def test_tor_link_failure_is_reported_with_the_source_name(monkeypatch):
    stub(monkeypatch, {
        TOR_LINK: FakeResponse(status_code=503),
        AHMIA: FakeResponse(status_code=200),
    })

    result = DarkWebSearch().search("example")

    assert result["results"] == []
    assert classify(result) == ERROR
    assert "Tor.link: HTTP 503" in result["error"]
    assert "Ahmia.fi: requires JavaScript rendering" in result["error"]


def test_every_source_says_what_happened(monkeypatch):
    stub(monkeypatch, {
        TOR_LINK: requests.exceptions.ConnectionError("dns"),
        AHMIA: FakeResponse(status_code=503),
    })

    result = DarkWebSearch().search("example")

    assert classify(result) == ERROR
    assert "Tor.link: unreachable" in result["status_reason"]
    assert "Ahmia.fi: HTTP 503" in result["status_reason"]


def test_all_sources_rate_limited_is_rate_limited(monkeypatch):
    stub(monkeypatch, {
        TOR_LINK: FakeResponse(status_code=429),
        AHMIA: FakeResponse(status_code=429),
    })

    result = DarkWebSearch().search("example")

    assert classify(result) == RATE_LIMITED
    assert "Tor.link: rate limited" in result["status_reason"]


def test_malformed_json_is_an_error_not_a_crash(monkeypatch):
    class BadJson(FakeResponse):
        def json(self):
            raise ValueError("Expecting value")

    stub(monkeypatch, {TOR_LINK: BadJson(), AHMIA: FakeResponse(status_code=503)})

    result = DarkWebSearch().search("example")

    assert classify(result) == ERROR
    assert "Tor.link: Expecting value" in result["error"]


def test_query_is_sent_as_q_param(monkeypatch):
    seen = {}

    def fake_get(url, params=None, **kwargs):
        seen["params"] = params
        return FakeResponse(payload={"results": []})

    monkeypatch.setattr(darkweb_mod.requests, "get", fake_get)

    DarkWebSearch().search("acme corp")

    assert seen["params"] == {"q": "acme corp"}
