import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.blackbird import Blackbird, CONTROL_USERNAME

TEMPLATE = "https://example.com/{}"
STATUS_CONFIG = (TEMPLATE, "status", 404)
TEXT_CONFIG = (TEMPLATE, "text", "no such user")


def _run(bb, username, config=STATUS_CONFIG, site="Example"):
    return asyncio.run(bb.check_site(None, username, site, config))


def _wire(bb, monkeypatch, pages):
    async def fake_fetch(self, session, url):
        name = url.rsplit("/", 1)[-1]
        page = pages[name]
        return {
            "status": page.get("status", 200),
            "final_url": url.lower(),
            "redirected": page.get("redirected", False),
            "body": page.get("body", ""),
            "elapsed": 0.1,
        }
    monkeypatch.setattr(Blackbird, "_fetch", fake_fetch)


def test_soft_404_is_not_reported_as_found(monkeypatch):
    bb = Blackbird()
    _wire(bb, monkeypatch, {
        "ghost": {"body": "<html>generic shell</html>"},
        CONTROL_USERNAME: {"body": "<html>generic shell</html>"},
    })
    assert _run(bb, "ghost").status == "not_found"


def test_real_profile_is_found_when_the_page_names_it(monkeypatch):
    bb = Blackbird()
    _wire(bb, monkeypatch, {
        "torvalds": {"body": "<title>torvalds profile</title>"},
        CONTROL_USERNAME: {"body": "<html>generic shell</html>"},
    })
    assert _run(bb, "torvalds").status == "found"


def test_site_that_echoes_any_username_never_reports_found(monkeypatch):
    bb = Blackbird()
    _wire(bb, monkeypatch, {
        "realuser": {"body": "<title>realuser</title>"},
        CONTROL_USERNAME: {"body": f"<title>{CONTROL_USERNAME}</title>"},
    })
    assert _run(bb, "realuser").status == "not_found"


def test_hard_404_needs_no_control_request(monkeypatch):
    bb = Blackbird()
    _wire(bb, monkeypatch, {"ghost": {"status": 404, "body": ""}})
    assert _run(bb, "ghost").status == "not_found"
    assert bb._controls == {}


def test_site_that_rejects_the_control_treats_200_as_found(monkeypatch):
    bb = Blackbird()
    _wire(bb, monkeypatch, {
        "someone": {"body": "profile"},
        CONTROL_USERNAME: {"status": 404, "body": ""},
    })
    assert _run(bb, "someone").status == "found"


@pytest.mark.parametrize("code", [401, 403, 429, 500, 503])
def test_blocked_responses_are_unknown_not_absent(monkeypatch, code):
    bb = Blackbird()
    _wire(bb, monkeypatch, {"someone": {"status": code, "body": ""}})
    assert _run(bb, "someone").status == "unknown"


def test_redirect_away_is_not_found(monkeypatch):
    bb = Blackbird()

    async def fake_fetch(self, session, url):
        return {"status": 200, "final_url": "https://example.com/login",
                "redirected": True, "body": "login", "elapsed": 0.1}
    monkeypatch.setattr(Blackbird, "_fetch", fake_fetch)
    assert _run(bb, "someone").status == "not_found"


def test_working_text_indicator_still_decides(monkeypatch):
    bb = Blackbird()
    _wire(bb, monkeypatch, {
        "missing": {"body": "sorry, no such user here"},
        "present": {"body": "welcome to the profile"},
        CONTROL_USERNAME: {"body": "sorry, no such user here"},
    })
    assert _run(bb, "missing", TEXT_CONFIG).status == "not_found"
    assert _run(bb, "present", TEXT_CONFIG).status == "found"


def test_stale_text_indicator_falls_back_to_the_name_test(monkeypatch):
    bb = Blackbird()
    _wire(bb, monkeypatch, {
        "ghost": {"body": "<html>generic shell</html>"},
        "realuser": {"body": "<title>realuser</title>"},
        CONTROL_USERNAME: {"body": "<html>generic shell</html>"},
    })
    assert _run(bb, "ghost", TEXT_CONFIG).status == "not_found"
    assert _run(bb, "realuser", TEXT_CONFIG).status == "found"


def test_control_is_fetched_once_per_site(monkeypatch):
    bb = Blackbird()
    calls = []

    async def counting_fetch(self, session, url):
        calls.append(url)
        name = url.rsplit("/", 1)[-1]
        body = "shell" if name == CONTROL_USERNAME else f"{name} profile"
        return {"status": 200, "final_url": url, "redirected": False, "body": body, "elapsed": 0.1}
    monkeypatch.setattr(Blackbird, "_fetch", counting_fetch)

    async def go():
        await bb.check_site(None, "alice", "Example", STATUS_CONFIG)
        await bb.check_site(None, "bob", "Example", STATUS_CONFIG)
    asyncio.run(go())

    assert calls.count(TEMPLATE.format(CONTROL_USERNAME)) == 1


def test_unknown_is_not_counted_as_found(monkeypatch):
    from modules.blackbird import SiteResult
    bb = Blackbird()
    bb.results = [
        SiteResult("A", "u", "found", 200, 0.1),
        SiteResult("B", "u", "unknown", 403, 0.1),
        SiteResult("C", "u", "not_found", 404, 0.1),
    ]
    assert [r.site for r in bb.get_found()] == ["A"]
