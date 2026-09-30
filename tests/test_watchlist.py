import importlib

import pytest


@pytest.fixture
def wl(tmp_path, monkeypatch):
    monkeypatch.setenv("WATCHLIST_SCHEDULER", "false")
    import web.watchlist as watchlist
    importlib.reload(watchlist)
    monkeypatch.setattr(watchlist, "_WATCHLIST_DIR", str(tmp_path))
    return watchlist


def test_create_and_list_scoped_by_owner(wl):
    wl.create_watchlist("alice", "example.com", "domain", ["dns"], 24)
    wl.create_watchlist("bob", "other.com", "domain", ["dns"], 24)
    assert len(wl.list_watchlists("alice")) == 1
    assert len(wl.list_watchlists("bob")) == 1
    assert "owner" not in wl.list_watchlists("alice")[0]
    assert "fingerprint" not in wl.list_watchlists("alice")[0]


def test_baseline_run_has_no_alert(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["shodan"], 24)
    alert = wl.record_run(entry["id"], {"shodan": {"open_ports": [80, 443]}})
    assert alert is None


def test_change_produces_alert(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["shodan"], 24)
    wl.record_run(entry["id"], {"shodan": {"open_ports": [80, 443]}})
    alert = wl.record_run(entry["id"], {"shodan": {"open_ports": [80, 443, 22]}})
    assert alert is not None
    assert any("22" in a for a in alert["added"])
    assert alert["removed"] == []


def test_no_change_no_alert(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["shodan"], 24)
    payload = {"shodan": {"open_ports": [80, 443]}}
    wl.record_run(entry["id"], payload)
    assert wl.record_run(entry["id"], payload) is None


def test_volatile_fields_ignored_in_diff(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["dns"], 24)
    wl.record_run(entry["id"], {"dns": {"records": {"A": ["1.2.3.4"]}}, "started_at": "t1"})
    alert = wl.record_run(entry["id"], {"dns": {"records": {"A": ["1.2.3.4"]}}, "started_at": "t2"})
    assert alert is None


def test_delete_requires_owner(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["dns"], 24)
    assert wl.delete_watchlist(entry["id"], "bob") is False
    assert wl.delete_watchlist(entry["id"], "alice") is True


def test_mark_error_keeps_fingerprint(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["shodan"], 24)
    wl.record_run(entry["id"], {"shodan": {"open_ports": [80]}})
    wl.mark_error(entry["id"])
    stored = wl.get_watchlist(entry["id"])
    assert stored["last_status"] == "error"
    assert stored["fingerprint"] is not None


def test_new_watchlist_is_not_paused(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["dns"], 24)
    assert entry["paused"] is False


def test_set_paused_requires_owner(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["dns"], 24)
    assert wl.set_paused(entry["id"], "bob", True) is None
    updated = wl.set_paused(entry["id"], "alice", True)
    assert updated is not None
    assert updated["paused"] is True


def test_set_paused_missing_watchlist(wl):
    assert wl.set_paused("does-not-exist", "alice", True) is None


def test_set_paused_preserves_history_and_baseline(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["shodan"], 24)
    wl.record_run(entry["id"], {"shodan": {"open_ports": [80, 443]}})
    wl.set_paused(entry["id"], "alice", True)
    stored = wl.get_watchlist(entry["id"])
    assert stored["paused"] is True
    assert stored["fingerprint"] is not None
    assert stored["run_count"] == 1

    wl.set_paused(entry["id"], "alice", False)
    stored = wl.get_watchlist(entry["id"])
    assert stored["paused"] is False
    assert stored["run_count"] == 1


def test_due_watchlists_skips_paused(wl):
    entry = wl.create_watchlist("alice", "example.com", "domain", ["dns"], 24)
    other = wl.create_watchlist("alice", "other.com", "domain", ["dns"], 24)
    wl.set_paused(entry["id"], "alice", True)
    due_ids = {e["id"] for e in wl.due_watchlists()}
    assert entry["id"] not in due_ids
    assert other["id"] in due_ids
