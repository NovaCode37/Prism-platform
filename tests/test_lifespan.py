"""Startup runs through a lifespan handler, not the deprecated on_event (#361)."""

import importlib
import os
import sys
import threading
import warnings

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SCHEDULER_THREAD = "prism-watchlist-scheduler"


def _fresh_app_module(monkeypatch, scheduler="true"):
    """Import web.app from scratch, the same way test_reverse_proxy does."""
    monkeypatch.setenv("WATCHLIST_SCHEDULER", scheduler)
    # Keep a started scheduler asleep instead of polling during the test run.
    monkeypatch.setenv("WATCHLIST_POLL_SECONDS", "3600")
    for module in ("web.app", "web.security"):
        sys.modules.pop(module, None)
    return importlib.import_module("web.app")


def _live_threads(name):
    return [t for t in threading.enumerate() if t.name == name and t.is_alive()]


def test_importing_the_app_emits_no_on_event_deprecation(monkeypatch):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _fresh_app_module(monkeypatch)

    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert not [m for m in messages if "on_event" in m], messages


def test_no_on_event_startup_handlers_remain(monkeypatch):
    app_mod = _fresh_app_module(monkeypatch)

    assert app_mod.app.router.on_startup == []
    assert app_mod.app.router.lifespan_context is not None


def test_startup_still_prints_the_banner(monkeypatch, capsys):
    monkeypatch.setenv("PRISM_BASE_PATH", "/prism")
    app_mod = _fresh_app_module(monkeypatch)

    with TestClient(app_mod.app):
        pass

    out = capsys.readouterr().out
    assert "PRISM is running on http://localhost:8080 (public base path: /prism)" in out
    assert "https://github.com/NovaCode37/Prism-platform" in out


def test_startup_starts_the_watchlist_scheduler(monkeypatch):
    app_mod = _fresh_app_module(monkeypatch)

    with TestClient(app_mod.app):
        assert len(_live_threads(SCHEDULER_THREAD)) == 1


def test_reimporting_the_app_does_not_start_a_second_scheduler(monkeypatch):
    """A module-level "already started" flag is reset by every fresh import, so
    each startup after one used to add a thread next to the one still looping."""
    for _ in range(3):
        app_mod = _fresh_app_module(monkeypatch)
        with TestClient(app_mod.app):
            pass

    assert len(_live_threads(SCHEDULER_THREAD)) == 1


def test_scheduler_stays_off_when_disabled(monkeypatch):
    app_mod = _fresh_app_module(monkeypatch, scheduler="false")
    # A name no other test uses, so a thread left running by an earlier test
    # cannot make this pass.
    monkeypatch.setattr(app_mod, "_WATCHLIST_THREAD_NAME", "prism-watchlist-scheduler-disabled")

    with TestClient(app_mod.app):
        pass

    assert _live_threads("prism-watchlist-scheduler-disabled") == []
