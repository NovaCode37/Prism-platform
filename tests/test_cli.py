import pytest
import sys

import cli


def test_modules_constants():
    assert len(cli.MODULES_BY_TARGET_TYPE) == 6
    assert "domain" in cli.MODULES_BY_TARGET_TYPE
    assert "ip" in cli.MODULES_BY_TARGET_TYPE
    assert "email" in cli.MODULES_BY_TARGET_TYPE
    assert "whois" in cli.MODULES_BY_TARGET_TYPE["domain"]
    assert "whois" not in cli.MODULES_BY_TARGET_TYPE["email"]
    assert "whos" not in cli.ALL_MODULES

    # Check ALL_MODULES contains every module from MODULES_BY_TARGET_TYPE
    flattened = [m for mods in cli.MODULES_BY_TARGET_TYPE.values() for m in mods]
    assert set(cli.ALL_MODULES) == set(flattened)
    assert len(cli.ALL_MODULES) == len(set(flattened))


def test_scan_unknown_module_exits_2(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["scan", "example.com", "-m", "whos"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "whos" in captured.err
    assert "Unknown module(s): whos" in captured.err
    assert "Valid modules for domain:" in captured.err
    assert "whois" in captured.err


def test_scan_multiple_unknown_modules_exits_2(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["scan", "example.com", "-m", "whos,badmod"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "whos" in captured.err
    assert "badmod" in captured.err
    assert "Unknown module(s): whos, badmod" in captured.err


def test_scan_valid_module_succeeds(monkeypatch):
    called = {}

    async def fake_run_scan(target, scan_type, modules, verbose=False):
        called.update(target=target, scan_type=scan_type, modules=modules)
        return {"opsec_score": {"score": 100}}

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)
    monkeypatch.setattr(cli, "output_json", lambda results, path=None: None)

    with pytest.raises(SystemExit) as exc:
        cli.main(["scan", "example.com", "-m", "whois", "--quiet"])

    assert exc.value.code == 0
    assert called["modules"] == ["whois"]
    assert called["scan_type"] == "domain"


def test_scan_inapplicable_module_emits_warning(monkeypatch, capsys):
    called = {}

    async def fake_run_scan(target, scan_type, modules, verbose=False):
        called.update(target=target, scan_type=scan_type, modules=modules)
        return {"opsec_score": {"score": 100}}

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)
    monkeypatch.setattr(cli, "output_json", lambda results, path=None: None)

    with pytest.raises(SystemExit) as exc:
        cli.main(["scan", "user@example.com", "-m", "whois,smtp", "--quiet"])

    assert exc.value.code == 0
    assert called["modules"] == ["whois", "smtp"]
    assert called["scan_type"] == "email"

    captured = capsys.readouterr()
    assert "Warning: module(s) whois do not apply to target type 'email'" in captured.err


def test_run_scan_respects_applicable_modules(monkeypatch):
    import asyncio
    whois_called = []

    class FakeWhois:
        def lookup(self, target):
            whois_called.append(target)
            return {"registrar": "test"}

    monkeypatch.setattr("modules.extra_tools.WhoisLookup", FakeWhois)
    monkeypatch.setattr("modules.opsec_score.score_from_results", lambda res: {"score": 100})
    monkeypatch.setattr("modules.graph_builder.build_graph", lambda t, st, res: {})

    # whois passed to email target should NOT invoke WhoisLookup
    results = asyncio.run(cli.run_scan("user@example.com", "email", modules=["whois"]))
    assert "whois" not in results
    assert whois_called == []
