import hashlib
import hmac
import os
import re
from typing import List, Optional

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB") or "20") * 1024 * 1024
MAX_TARGET_LEN   = 512

def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")

def normalize_base_path(raw: Optional[str]) -> str:
    if not raw:
        return ""
    value = raw.strip()
    if not value or value == "/":
        return ""
    value = value.strip("/")
    return f"/{value}" if value else ""

def parse_csv_env(name: str) -> List[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]

def _parse_keys() -> List[str]:
    raw_multi = os.getenv("API_KEYS", "").strip()
    raw_single = os.getenv("API_KEY", "").strip()
    keys = []
    if raw_multi:
        keys.extend(k.strip() for k in raw_multi.split(",") if k.strip())
    if raw_single and raw_single not in keys:
        keys.append(raw_single)
    return keys

_API_KEYS: List[str] = _parse_keys()
API_KEY: Optional[str] = _API_KEYS[0] if _API_KEYS else None                               

ANONYMOUS_PRINCIPAL = "anonymous"

def _allow_anonymous_api() -> bool:
    return os.getenv("ALLOW_ANON_API", "").lower() in ("1", "true", "yes")

def _trust_proxy_headers() -> bool:
    return env_flag("TRUST_PROXY_HEADERS", False)

def client_ip(request: Request) -> str:
    if _trust_proxy_headers():
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            first = xff.split(",")[0].strip()
            if first:
                return first
        real = request.headers.get("X-Real-IP")
        if real:
            return real.strip()
    return get_remote_address(request)

limiter = Limiter(key_func=client_ip, default_limits=["200/day", "60/hour"])

def _principal_from_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

def _match_key(presented: str) -> Optional[str]:
    if not presented:
        return None
    for k in _API_KEYS:
        if hmac.compare_digest(presented, k):
            return k
    return None

def extract_api_key(request: Request) -> Optional[str]:
    x_api_key = request.headers.get("X-API-Key")
    if x_api_key:
        return x_api_key
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token or None
    return None

async def require_api_key(request: Request) -> None:
    if not _API_KEYS:
        if _allow_anonymous_api():
            request.state.principal = ANONYMOUS_PRINCIPAL
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API auth is not configured on server.",
        )
    key = extract_api_key(request)
    matched = _match_key(key or "")
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass X-API-Key header.",
        )
    request.state.principal = _principal_from_key(matched)

def get_principal(request: Request) -> str:
    return getattr(request.state, "principal", ANONYMOUS_PRINCIPAL)

import time as _time

SCAN_QUOTA_PER_DAY = int(os.getenv("SCAN_QUOTA_PER_DAY") or "0")
_WINDOW_SECONDS = 86400
_usage: dict = {}

def _usage_window(principal: str) -> dict:
    now = _time.time()
    entry = _usage.get(principal)
    if entry is None or now - entry["window_start"] >= _WINDOW_SECONDS:
        entry = {"count": 0, "window_start": now}
        _usage[principal] = entry
    return entry

def get_usage(principal: str) -> dict:
    entry = _usage_window(principal)
    limit = SCAN_QUOTA_PER_DAY
    used = entry["count"]
    resets_at = entry["window_start"] + _WINDOW_SECONDS
    return {
        "principal": principal,
        "used": used,
        "limit": limit if limit > 0 else None,
        "remaining": max(limit - used, 0) if limit > 0 else None,
        "resets_at": resets_at,
        "window_seconds": _WINDOW_SECONDS,
    }

def check_scan_quota(principal: str) -> None:
    if SCAN_QUOTA_PER_DAY <= 0:
        return
    entry = _usage_window(principal)
    if entry["count"] >= SCAN_QUOTA_PER_DAY:
        resets_at = entry["window_start"] + _WINDOW_SECONDS
        raise HTTPException(
            status_code=429,
            detail=f"Daily scan quota of {SCAN_QUOTA_PER_DAY} reached. Resets at {int(resets_at)} (unix).",
        )

def record_scan(principal: str) -> None:
    entry = _usage_window(principal)
    entry["count"] += 1

def principal_for_key(key: Optional[str]) -> Optional[str]:
    if not _API_KEYS:
        return ANONYMOUS_PRINCIPAL if _allow_anonymous_api() else None
    matched = _match_key(key or "")
    if not matched:
        return None
    return _principal_from_key(matched)

def validate_target(target: str) -> str:
    target = target.strip()
    if not target:
        raise HTTPException(status_code=400, detail="Target is empty.")
    if len(target) > MAX_TARGET_LEN:
        raise HTTPException(status_code=400, detail="Target too long.")
    forbidden = re.compile(r"[;\|`$<>{}]")
    if forbidden.search(target):
        raise HTTPException(status_code=400, detail="Target contains forbidden characters.")
    return target

async def check_upload_size(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {MAX_UPLOAD_BYTES // (1024*1024)} MB allowed.",
        )

def validate_scan_id(scan_id: str) -> str:
    import uuid
    try:
        uuid.UUID(scan_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid scan ID format.")
    return scan_id

def _is_blocked_ip(ip_str: str) -> bool:
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return (addr.is_private or addr.is_loopback or addr.is_reserved
            or addr.is_link_local or addr.is_multicast or addr.is_unspecified)

def validate_public_target(target: str, scan_type: str) -> None:
    if env_flag("ALLOW_PRIVATE_TARGETS", False):
        return
    if scan_type not in ("domain", "ip"):
        return
    import ipaddress
    import socket
    host = target.strip()
    try:
        ipaddress.ip_address(host)
        addrs = [host]
    except ValueError:
        try:
            addrs = [sa[0] for *_rest, sa in socket.getaddrinfo(host, None)]
        except socket.gaierror:
            return
    if any(_is_blocked_ip(ip_str) for ip_str in addrs):
        raise HTTPException(
            status_code=400,
            detail="Scanning private/internal addresses is disabled on this server.",
        )

def validate_url_not_private(url: str) -> str:
    import ipaddress
    import socket
    from urllib.parse import urlparse
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL.")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Cannot resolve hostname.")
    seen = set()
    for _f, _t, _p, _c, sa in infos:
        ip_str = sa[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid resolved address.")
        if (addr.is_private or addr.is_loopback or addr.is_reserved
                or addr.is_link_local or addr.is_multicast or addr.is_unspecified):
            raise HTTPException(status_code=400, detail="Requests to private/internal addresses are blocked.")
    if not seen:
        raise HTTPException(status_code=400, detail="Cannot resolve hostname.")
    return url

def get_allowed_origins() -> list:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    if not raw:
        return []
    if raw.strip() == "*":
        return []
    return [o.strip() for o in raw.split(",") if o.strip()]
