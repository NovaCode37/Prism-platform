"""Standard status vocabulary for module results.

Several PRISM modules depend on third-party API keys (Shodan, VirusTotal,
AbuseIPDB, Censys, ...). When a key is absent or the provider rate-limits us,
the module should report a clear, machine-readable status instead of failing
hard, so the dashboard can render a per-module badge.

Every key-dependent module attaches one of the following statuses to its
result dict via :func:`annotate`. Modules that do not set a status explicitly
are classified heuristically from their legacy ``error`` field by
:func:`classify`, keeping backwards compatibility.
"""

from typing import Any, Dict, Optional

# Module ran successfully and returned data.
OK = "ok"
# A prerequisite is missing (e.g. no API key configured) - not a failure.
SKIPPED = "skipped"
# The provider throttled the request (HTTP 429 / quota exhausted).
RATE_LIMITED = "rate_limited"
# A genuine error occurred while running the module.
ERROR = "error"

# All valid statuses, in severity order.
ALL = (OK, SKIPPED, RATE_LIMITED, ERROR)

# Substrings used to infer a status from a legacy free-text error message.
_RATE_LIMIT_HINTS = (
    "rate limit",
    "rate-limit",
    "ratelimit",
    "429",
    "too many requests",
    "quota",
    "exceeded",
)
_SKIPPED_HINTS = (
    "api key",
    "api_key",
    "not set",
    "not configured",
    "credentials",
    "no api",
    "requires",
)


def classify(result: Any) -> str:
    """Return the status for a module ``result``.

    Honours an explicit ``status`` field when present and valid; otherwise
    falls back to inspecting the ``error`` field so legacy modules keep
    reporting a sensible status.
    """
    if not isinstance(result, dict):
        return OK
    explicit = result.get("status")
    if explicit in ALL:
        return explicit
    err = result.get("error")
    if not err:
        return OK
    low = str(err).lower()
    if any(hint in low for hint in _RATE_LIMIT_HINTS):
        return RATE_LIMITED
    if any(hint in low for hint in _SKIPPED_HINTS):
        return SKIPPED
    return ERROR


def reason_for(result: Any) -> Optional[str]:
    """Return a human-readable explanation for a non-OK status, if any."""
    if not isinstance(result, dict):
        return None
    return result.get("status_reason") or result.get("error")


def status_notice(result: Any) -> Optional[str]:
    """Return a one-line notice for a ``skipped`` / ``rate_limited`` result.

    Returns ``None`` for ``ok`` and ``error`` (callers render those normally).
    """
    status = classify(result)
    if status in (SKIPPED, RATE_LIMITED):
        label = "Skipped" if status == SKIPPED else "Rate limited"
        reason = reason_for(result)
        return f"{label}: {reason}" if reason else label
    return None


def print_status_notice(result: Any) -> bool:
    """Print a CLI notice for a degraded (skipped/rate-limited) module result.

    Returns ``True`` when a notice was printed so callers can stop rendering.
    """
    notice = status_notice(result)
    if notice is None:
        return False
    try:
        from config import Colors
        print(f"{Colors.YELLOW}{notice}{Colors.RESET}")
    except Exception:
        print(notice)
    return True


def annotate(result: Dict[str, Any], status: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Attach a standard ``status`` (and optional human ``reason``) to a result.

    For a genuine ``ERROR`` the ``reason`` is also mirrored into the legacy
    ``error`` field so existing error-based consumers keep working. For any
    non-error status the ``error`` field is cleared, so "skipped" /
    "rate_limited" outcomes are not rendered as hard errors.
    """
    result["status"] = status
    if reason is not None:
        result["status_reason"] = reason
    if status == ERROR:
        if reason is not None:
            result["error"] = reason
    else:
        result["error"] = None
    return result
