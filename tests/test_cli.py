import os
import glob
from unittest.mock import patch, AsyncMock
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


@patch("cli.run_scan", new_callable=AsyncMock)
def test_cli_graphml_export(mock_run_scan, tmp_path):
    mock_run_scan.return_value = {
        "graph": {
            "nodes": [{"id": "1", "label": "example.com", "type": "domain", "color": "#a29bfe"}],
            "edges": []
        }
    }
    
    out_file = tmp_path / "out.graphml"
    
    with pytest.raises(SystemExit) as e:
        cli.main(["scan", "example.com", "--graphml", "-o", str(out_file), "--quiet"])
    
    assert e.value.code == 0
    assert out_file.exists()
    
    content = out_file.read_text(encoding="utf-8")
    assert "<graphml" in content
    assert "example.com" in content


@patch("cli.run_scan", new_callable=AsyncMock)
def test_cli_gexf_export(mock_run_scan, tmp_path):
    mock_run_scan.return_value = {
        "graph": {
            "nodes": [{"id": "1", "label": "example.com", "type": "domain", "color": "#a29bfe"}],
            "edges": []
        }
    }
    
    out_file = tmp_path / "out.gexf"
    
    with pytest.raises(SystemExit) as e:
        cli.main(["scan", "example.com", "--gexf", "-o", str(out_file), "--quiet"])
    
    assert e.value.code == 0
    assert out_file.exists()
    
    content = out_file.read_text(encoding="utf-8")
    assert "<gexf" in content
    assert "example.com" in content


@patch("cli.run_scan", new_callable=AsyncMock)
def test_cli_multiple_exports_overwrite_prevention(mock_run_scan, tmp_path):
    mock_run_scan.return_value = {
        "graph": {
            "nodes": [{"id": "1", "label": "example.com", "type": "domain", "color": "#a29bfe"}],
            "edges": []
        }
    }
    
    out_file = tmp_path / "out.json" # user specifies generic out file
    
    with pytest.raises(SystemExit) as e:
        cli.main(["scan", "example.com", "--graphml", "--gexf", "--html", "-o", str(out_file), "--quiet"])
    
    assert e.value.code == 0
    assert (tmp_path / "out.graphml").exists()
    assert (tmp_path / "out.gexf").exists()
    assert (tmp_path / "out.html").exists()


def _want_names():
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(cli.run_scan)))
    return {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "want"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }


def test_every_module_run_scan_can_run_is_listed():
    names = _want_names()
    assert names, "found no want(...) calls in run_scan"
    assert names - set(cli.ALL_MODULES) == set()


def test_listing_has_nothing_run_scan_cannot_run():
    assert set(cli.ALL_MODULES) - _want_names() == set()


def test_key_tables_only_name_known_modules():
    assert set(cli.REQUIRED_ENV) <= set(cli.ALL_MODULES)
    assert set(cli.OPTIONAL_ENV) <= set(cli.ALL_MODULES)
    assert not set(cli.REQUIRED_ENV) & set(cli.OPTIONAL_ENV)


def _clear_key_env(monkeypatch):
    for env in list(cli.REQUIRED_ENV.values()) + list(cli.OPTIONAL_ENV.values()):
        for name in env:
            monkeypatch.delenv(name, raising=False)


def test_modules_lists_every_type(monkeypatch, capsys):
    _clear_key_env(monkeypatch)

    with pytest.raises(SystemExit) as exc:
        cli.main(["modules"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    for scan_type, mods in cli.MODULES_BY_TARGET_TYPE.items():
        assert f"\n{scan_type}\n" in f"\n{out}"
        for name in mods:
            assert f"  {name}" in out
    assert "VIRUSTOTAL_API_KEY" in out
    assert "required, not set, skipped at scan time" in out


def test_modules_type_filter(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["modules", "--type", "email"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("email\n")
    assert "whois" not in out


def test_modules_json_matches_constants(monkeypatch, capsys):
    import json

    _clear_key_env(monkeypatch)
    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "x")

    with pytest.raises(SystemExit) as exc:
        cli.main(["modules", "--json"])

    assert exc.value.code == 0
    data = json.loads(capsys.readouterr().out)
    assert list(data) == list(cli.MODULES_BY_TARGET_TYPE)
    for scan_type, mods in cli.MODULES_BY_TARGET_TYPE.items():
        assert [row["name"] for row in data[scan_type]] == list(mods)

    by_name = {row["name"]: row for row in data["domain"]}
    assert by_name["whois"] == {"name": "whois", "env": [], "key": None, "configured": None}
    assert by_name["virustotal"]["key"] == "required"
    assert by_name["virustotal"]["configured"] is True
    assert by_name["censys"]["configured"] is False
    assert by_name["shodan"]["key"] == "optional"


def test_modules_alias_key_counts_as_configured(monkeypatch):
    _clear_key_env(monkeypatch)
    monkeypatch.setenv("CENSYS_API_KEY", "x")

    rows = {row["name"]: row for row in cli.describe_modules("ip")["ip"]}

    assert rows["censys"]["configured"] is True


def test_modules_enabled_flag_needs_a_truthy_value(monkeypatch):
    _clear_key_env(monkeypatch)
    monkeypatch.setenv("HUDSONROCK_ENABLED", "false")

    rows = {row["name"]: row for row in cli.describe_modules("email")["email"]}

    assert rows["hudsonrock"]["configured"] is False