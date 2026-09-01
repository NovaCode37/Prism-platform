import os
import sys
import threading
import time

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
