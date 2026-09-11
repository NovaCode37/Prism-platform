import pytest

import cli


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" Example.COM ", "example.com"),
        ("https://Example.COM/", "example.com"),
        ("HTTP://Example.COM//", "example.com"),
        (" User@Example.COM ", "user@example.com"),
        ("+1 555 000 0000", "+1 555 000 0000"),
        ("@MixedCaseUser", "@MixedCaseUser"),
    ],
)
def test_normalize_target(raw, expected):
    assert cli.normalize_target(raw) == expected


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("user@example.com", "email"),
        ("+1 555 000 0000", "phone"),
        ("8.8.8.8", "ip"),
        ("example.com", "domain"),
        ("player1234567", "username"),
        ("t.me/someuser", "telegram"),
        ("@durov", "username"),
        ("@MixedCaseUser", "username"),
    ],
)
def test_detect_type(target, expected):
    assert cli.detect_type(target) == expected


def test_detect_type_after_normalization():
    normalized = cli.normalize_target(" https://Example.COM/ ")

    assert normalized == "example.com"
    assert cli.detect_type(normalized) == "domain"


def test_cli_scan_normalizes_target_before_running(monkeypatch):
    captured = {}

    async def fake_run_scan(target, scan_type, modules, verbose=False):
        captured.update(
            target=target,
            scan_type=scan_type,
            modules=modules,
            verbose=verbose,
        )
        return {"ok": True}

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)
    monkeypatch.setattr(cli, "output_json", lambda results, path=None: None)

    with pytest.raises(SystemExit) as exc:
        cli.main(["scan", " HTTPS://Example.COM/ ", "--quiet"])

    assert exc.value.code == 0
    assert captured == {
        "target": "example.com",
        "scan_type": "domain",
        "modules": None,
        "verbose": False,
    }
