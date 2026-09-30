import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.maigret_wrapper import MaigretWrapper


class _HangingProcess:
    def __init__(self):
        self._stopped = threading.Event()
        self.returncode = None
        self.stdout = self

    def readline(self):
        self._stopped.wait(30)
        return ''

    def kill(self):
        self._stopped.set()
        self.returncode = -9

    def wait(self, timeout=None):
        self._stopped.wait(30)
        return self.returncode

    def poll(self):
        return self.returncode


def _wrapper(monkeypatch):
    monkeypatch.setattr(MaigretWrapper, "_find_maigret", lambda self: "maigret")
    return MaigretWrapper()


def test_missing_maigret_is_skipped_without_installing(monkeypatch):
    """A missing binary is reported as skipped (#394): scans never pip-install
    maigret into the project (or the read-only image) at scan time."""
    import modules.maigret_wrapper as mw
    from modules.module_status import classify, SKIPPED

    monkeypatch.setattr(MaigretWrapper, "_find_maigret", lambda self: None)
    monkeypatch.setattr(
        mw.subprocess, "Popen",
        lambda *a, **k: pytest.fail("maigret must not be started when it is missing"),
    )

    result = MaigretWrapper().search("testuser")

    assert classify(result) == SKIPPED
    assert result["accounts"] == []
    assert "not installed" in (result.get("status_reason") or "")


def test_search_stops_a_hanging_maigret(monkeypatch):
    import modules.maigret_wrapper as mw

    monkeypatch.setenv("MAIGRET_MAX_RUNTIME", "1")
    monkeypatch.setattr(mw.subprocess, "Popen", lambda *a, **k: _HangingProcess())
    wrapper = _wrapper(monkeypatch)

    started = time.time()
    result = wrapper.search("testuser")
    elapsed = time.time() - started

    assert elapsed < 10
    assert result["error"]
    assert "1s" in result["error"]
    assert result["accounts"] == []


def test_search_reads_output_when_maigret_finishes(monkeypatch):
    import modules.maigret_wrapper as mw

    class _QuickProcess:
        def __init__(self):
            self.returncode = 0
            self._lines = iter(["[+] github: found\n", ""])
            self.stdout = self

        def readline(self):
            return next(self._lines, '')

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

        def kill(self):
            pass

    monkeypatch.setenv("MAIGRET_MAX_RUNTIME", "30")
    monkeypatch.setattr(mw.subprocess, "Popen", lambda *a, **k: _QuickProcess())
    wrapper = _wrapper(monkeypatch)

    result = wrapper.search("testuser")

    assert result["error"] is None
    assert result["total_found"] == 0


# --- MODULE_PROXY reaches maigret (#344) ---

class _RecordingProcess:
    """Finishes at once and remembers how Popen was called."""

    calls = []

    def __init__(self, cmd, **kwargs):
        _RecordingProcess.calls.append((cmd, kwargs))
        self.returncode = 0
        self.stdout = self

    def readline(self):
        return ''

    def wait(self, timeout=None):
        return 0

    def poll(self):
        return 0

    def kill(self):
        pass


def _run_search(monkeypatch, proxy=None):
    import modules.maigret_wrapper as mw

    _RecordingProcess.calls = []
    if proxy is None:
        monkeypatch.delenv("MODULE_PROXY", raising=False)
    else:
        monkeypatch.setenv("MODULE_PROXY", proxy)
    monkeypatch.setenv("MAIGRET_MAX_RUNTIME", "30")
    monkeypatch.setattr(mw.subprocess, "Popen", _RecordingProcess)
    _wrapper(monkeypatch).search("testuser")
    assert len(_RecordingProcess.calls) == 1
    return _RecordingProcess.calls[0]


def test_module_proxy_is_passed_as_proxy_flag(monkeypatch):
    cmd, _ = _run_search(monkeypatch, proxy="socks5://127.0.0.1:1080")

    assert "--proxy" in cmd
    assert cmd[cmd.index("--proxy") + 1] == "socks5://127.0.0.1:1080"


def test_proxy_flag_comes_before_the_username_separator(monkeypatch):
    """Anything after `--` is a username to maigret, not an option."""
    cmd, _ = _run_search(monkeypatch, proxy="http://proxy.local:3128")

    assert cmd.index("--proxy") < cmd.index("--")
    assert cmd[-1] == "testuser"


def test_no_proxy_flag_without_module_proxy(monkeypatch):
    cmd, kwargs = _run_search(monkeypatch)

    assert "--proxy" not in cmd
    # The environment is inherited untouched, so no proxy is injected.
    assert kwargs.get("env") is None


def test_blank_module_proxy_counts_as_unset(monkeypatch):
    cmd, kwargs = _run_search(monkeypatch, proxy="   ")

    assert "--proxy" not in cmd
    assert kwargs.get("env") is None


def test_module_proxy_is_also_exported_for_maigrets_db_update(monkeypatch):
    """maigret's database auto-update uses plain `requests` and ignores --proxy,
    so the proxy has to reach it through the environment as well."""
    monkeypatch.setenv("PRISM_TEST_MARKER", "kept")
    _, kwargs = _run_search(monkeypatch, proxy="http://proxy.local:3128")

    env = kwargs["env"]
    assert env["HTTPS_PROXY"] == "http://proxy.local:3128"
    assert env["HTTP_PROXY"] == "http://proxy.local:3128"
    # The rest of the environment still reaches maigret.
    assert env["PRISM_TEST_MARKER"] == "kept"


def test_maigret_db_update_honours_https_proxy_env(monkeypatch):
    """Pins the reason for the env variables above against the installed maigret:
    its update check must arrive at the proxy, not go straight to GitHub."""
    import socket
    import pytest

    db_updater = pytest.importorskip("maigret.db_updater")
    if not hasattr(db_updater, "_fetch_meta"):
        pytest.skip("maigret no longer exposes _fetch_meta")

    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(5)
    port = listener.getsockname()[1]

    received = []

    def _accept():
        try:
            conn, _ = listener.accept()
            conn.settimeout(5)
            received.append(conn.recv(256).decode(errors="replace"))
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=_accept, daemon=True)
    thread.start()
    monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{port}")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)

    db_updater._fetch_meta("https://raw.githubusercontent.com/soxoj/maigret/main/maigret/resources/db_meta.json", timeout=3)
    thread.join(6)
    listener.close()

    assert received, "maigret's update check did not go through HTTPS_PROXY"
    assert received[0].startswith("CONNECT raw.githubusercontent.com:443")
