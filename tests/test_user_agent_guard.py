"""Guard: no hardcoded User-Agent strings outside the deliberate browser ones.

Issue #320 unified ten UA strings into config.USER_AGENT. This test keeps it
that way: any new module must import USER_AGENT instead of inlining a string.
The Mozilla/5.0 literals are intentional (some scraped sites block tool UAs)
and are whitelisted below.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent

# Full browser strings that must stay as-is. Matched by exact literal.
ALLOWED_LITERALS = {
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

UA_RE = re.compile(r'"User-Agent"\s*:\s*"([^"]+)"')


def test_no_hardcoded_user_agents():
    offenders = []
    for py in list((ROOT / "modules").rglob("*.py")) + list((ROOT / "web").rglob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        for match in UA_RE.finditer(text):
            literal = match.group(1)
            if literal not in ALLOWED_LITERALS:
                offenders.append(f"{py.relative_to(ROOT)}: {literal}")
    assert not offenders, "Hardcoded User-Agent found (import USER_AGENT from config):\n" + "\n".join(
        offenders
    )


def test_user_agent_tracks_version():
    from config import PRISM_VERSION, USER_AGENT

    assert PRISM_VERSION in USER_AGENT
    import cli

    assert cli.__version__ == PRISM_VERSION, "cli.__version__ drifted from config.PRISM_VERSION"
