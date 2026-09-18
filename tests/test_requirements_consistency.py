"""The two requirements files must not drift apart on the packages they share.

``requirements.txt`` is the full install (CI, source installs);
``requirements-web.txt`` is what the Docker image installs. A package that
appears in both must carry the same version specifier in both, or an install
from one file silently differs from the other - ``requests[socks]`` had to be
changed in both in #380.

The files are allowed to differ in *which* packages they list: test tooling and
maigret only belong to the full install, and xhtml2pdf belongs to both because
PDF export needs it in either install (#394).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "requirements.txt"
WEB = ROOT / "requirements-web.txt"

_LINE = re.compile(r"^(?P<name>[A-Za-z0-9_.\-]+)(?P<extras>\[[^\]]*\])?\s*(?P<specifier>.*)$")


def _parse(path: Path) -> dict:
    """Return {lowercased package name: (extras, specifier)} for one file."""
    packages = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        match = _LINE.match(line)
        assert match, f"unrecognised requirement line in {path.name}: {line}"
        packages[match.group("name").lower()] = (
            match.group("extras") or "",
            match.group("specifier").strip(),
        )
    return packages


def test_shared_packages_use_identical_specifiers():
    full = _parse(FULL)
    web = _parse(WEB)

    shared = set(full) & set(web)
    assert shared, "the two requirements files no longer share any package"

    mismatches = {
        name: (full[name], web[name]) for name in shared if full[name] != web[name]
    }
    assert mismatches == {}, f"shared packages drifted between the two files: {mismatches}"


def test_xhtml2pdf_is_installed_by_both_requirement_files():
    """PDF export needs xhtml2pdf; a source install (requirements.txt) must get
    it too, or PDF export fails outside the Docker image (#394)."""
    assert "xhtml2pdf" in _parse(FULL)
    assert "xhtml2pdf" in _parse(WEB)
