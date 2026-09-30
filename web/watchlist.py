import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WATCHLIST_DIR = os.path.join(_ROOT, "watchlist_data")
os.makedirs(_WATCHLIST_DIR, exist_ok=True)

ANONYMOUS = "anonymous"
MAX_ALERTS = 50
MAX_LEAVES = 800

_VOLATILE_KEYS = {
    "response_time", "started_at", "completed_at", "timestamp", "generated_at",
    "duration", "scan_id", "report_path", "graph", "last_snapshot", "first_snapshot",
    "status_reason", "total_urls", "scanned_at", "elapsed", "took",
}


def _path(watch_id: str) -> str:
    return os.path.join(_WATCHLIST_DIR, f"{watch_id}.json")


def _save(entry: Dict[str, Any]) -> None:
    try:
        with open(_path(entry["id"]), "w", encoding="utf-8") as f:
            json.dump(entry, f, default=str)
    except Exception:
        pass


def get_watchlist(watch_id: str) -> Optional[Dict[str, Any]]:
    p = _path(watch_id)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _all() -> List[Dict[str, Any]]:
    out = []
    try:
        for fname in os.listdir(_WATCHLIST_DIR):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(_WATCHLIST_DIR, fname), "r", encoding="utf-8") as f:
                    out.append(json.load(f))
            except Exception:
                continue
    except Exception:
        pass
    return out


def _public(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in entry.items() if k not in ("owner", "fingerprint")}


def list_watchlists(principal: str) -> List[Dict[str, Any]]:
    items = [e for e in _all() if (e.get("owner") or ANONYMOUS) == principal]
    items.sort(key=lambda e: e.get("created_at") or "", reverse=True)
    return [_public(e) for e in items]


def create_watchlist(principal: str, target: str, scan_type: str,
                     modules: Optional[List[str]], interval_hours: float,
                     webhook_url: Optional[str] = None) -> Dict[str, Any]:
    watch_id = str(uuid.uuid4())
    now = time.time()
    entry = {
        "id": watch_id,
        "owner": principal,
        "target": target,
        "scan_type": scan_type,
        "modules": modules or [],
        "interval_hours": float(interval_hours),
        "webhook_url": webhook_url,
        "created_at": now,
        "last_run": None,
        "next_run": now,
        "last_status": "pending",
        "run_count": 0,
        "fingerprint": None,
        "alerts": [],
        "paused": False,
    }
    _save(entry)
    return _public(entry)


def delete_watchlist(watch_id: str, principal: str) -> bool:
    entry = get_watchlist(watch_id)
    if not entry or (entry.get("owner") or ANONYMOUS) != principal:
        return False
    try:
        os.remove(_path(watch_id))
        return True
    except Exception:
        return False


def set_paused(watch_id: str, principal: str, paused: bool) -> Optional[Dict[str, Any]]:
    entry = get_watchlist(watch_id)
    if not entry or (entry.get("owner") or ANONYMOUS) != principal:
        return None
    entry["paused"] = bool(paused)
    _save(entry)
    return _public(entry)


def due_watchlists() -> List[Dict[str, Any]]:
    now = time.time()
    return [e for e in _all() if not e.get("paused") and (e.get("next_run") or 0) <= now]


def _flatten(obj: Any, prefix: str, out: Set[str]) -> None:
    if len(out) >= MAX_LEAVES:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _VOLATILE_KEYS:
                continue
            _flatten(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _flatten(item, f"{prefix}[]", out)
            else:
                out.add(f"{prefix}[]={item}")
    elif obj is not None:
        out.add(f"{prefix}={obj}")


def fingerprint(results: Dict[str, Any]) -> List[str]:
    out: Set[str] = set()
    _flatten(results, "", out)
    return sorted(out)


def diff(old: Optional[List[str]], new: List[str]) -> Tuple[List[str], List[str]]:
    old_set = set(old or [])
    new_set = set(new)
    added = sorted(new_set - old_set)
    removed = sorted(old_set - new_set)
    return added, removed


def mark_error(watch_id: str) -> None:
    entry = get_watchlist(watch_id)
    if not entry:
        return
    now = time.time()
    entry["last_run"] = now
    entry["last_status"] = "error"
    entry["next_run"] = now + entry.get("interval_hours", 24) * 3600
    _save(entry)


def record_run(watch_id: str, results: Dict[str, Any], status: str = "completed") -> Optional[Dict[str, Any]]:
    entry = get_watchlist(watch_id)
    if not entry:
        return None
    now = time.time()
    new_fp = fingerprint(results)
    old_fp = entry.get("fingerprint")

    alert = None
    if old_fp is not None:
        added, removed = diff(old_fp, new_fp)
        if added or removed:
            alert = {
                "at": now,
                "added": added[:40],
                "removed": removed[:40],
                "added_count": len(added),
                "removed_count": len(removed),
            }
            entry["alerts"] = ([alert] + entry.get("alerts", []))[:MAX_ALERTS]

    entry["fingerprint"] = new_fp
    entry["last_run"] = now
    entry["last_status"] = status
    entry["run_count"] = int(entry.get("run_count", 0)) + 1
    entry["next_run"] = now + entry.get("interval_hours", 24) * 3600
    _save(entry)
    return alert
