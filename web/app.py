import asyncio
import json
import os
import sys
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import requests as _requests

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Depends, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

from modules.graph_builder import build_graph
from modules.module_status import classify, reason_for, OK, ERROR
from modules.opsec_score import score_from_results
from modules.report_generator import generate_html_report, generate_pdf_report
from modules.webhook_formatters import format_slack, format_discord

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
_LLM_KEY = OPENROUTER_API_KEY or GROQ_API_KEY
_LLM_URL = "https://openrouter.ai/api/v1/chat/completions" if OPENROUTER_API_KEY else "https://api.groq.com/openai/v1/chat/completions"
_LLM_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free" if OPENROUTER_API_KEY else "llama-3.1-8b-instant"

from web.security import (
    require_api_key, validate_target, check_upload_size, get_allowed_origins,
    limiter, validate_scan_id, validate_url_not_private,
    get_principal, principal_for_key, ANONYMOUS_PRINCIPAL,
    env_flag, normalize_base_path, parse_csv_env,
)

_disable_docs = os.getenv("DISABLE_DOCS", "").lower() in ("1", "true", "yes")
_BASE_PATH = normalize_base_path(os.getenv("PRISM_BASE_PATH", ""))
_TRUST_PROXY_HEADERS = env_flag("TRUST_PROXY_HEADERS")
_FORWARDED_ALLOW_IPS = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1,::1").strip() or "127.0.0.1,::1"
_TRUSTED_HOSTS = parse_csv_env("TRUSTED_HOSTS")
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_FRONTEND_DIR = Path(os.getenv("PRISM_FRONTEND_DIR") or (_PROJECT_ROOT / "frontend" / "out")).resolve()
_RESERVED_FRONTEND_PATHS = {"api", "ws", "healthz", "docs", "redoc", "openapi.json"}

app = FastAPI(
    title="OSINT Toolkit",
    version="2.4.0",
    root_path=_BASE_PATH,
    docs_url=None if _disable_docs else "/docs",
    redoc_url=None if _disable_docs else "/redoc",
    openapi_url=None if _disable_docs else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    allow_credentials=False,
)
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response

if _TRUSTED_HOSTS and _TRUSTED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_TRUSTED_HOSTS)

if _TRUST_PROXY_HEADERS:
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=_FORWARDED_ALLOW_IPS)

@app.on_event("startup")
async def _startup_banner() -> None:
    base_note = f" (public base path: {_BASE_PATH})" if _BASE_PATH else ""
    print(
        f"\n  PRISM is running on http://localhost:8080{base_note}\n"
        "  ⭐ If you find it useful, star the repo: "
        "https://github.com/NovaCode37/Prism-platform\n",
        flush=True,
    )

_scans: Dict[str, Dict] = {}
_queues: Dict[str, asyncio.Queue] = {}
MAX_STORED_SCANS = int(os.getenv("MAX_STORED_SCANS") or "200")

_SCANS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scan_data")
os.makedirs(_SCANS_DIR, exist_ok=True)

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "module_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)
_CACHE_TTL = int(os.getenv("CACHE_TTL_HOURS") or "24") * 3600

def _cache_key(module: str, target: str) -> str:
    import hashlib
    h = hashlib.md5(f"{module}:{target.lower().strip()}".encode()).hexdigest()
    return os.path.join(_CACHE_DIR, f"{module}_{h}.json")

def _get_cached(module: str, target: str) -> Optional[Dict]:
    path = _cache_key(module, target)
    if not os.path.exists(path):
        return None
    try:
        age = time.time() - os.path.getmtime(path)
        if age > _CACHE_TTL:
            os.remove(path)
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _set_cache(module: str, target: str, data: Any) -> None:
    try:
        with open(_cache_key(module, target), "w", encoding="utf-8") as f:
            json.dump(data, f, default=str)
    except Exception:
        pass

def _geocode_place(query: str) -> Optional[Dict]:
    import hashlib
    cache_path = os.path.join(_CACHE_DIR, "geocode_" + hashlib.md5(query.lower().encode()).hexdigest() + ".json")
    try:
        if os.path.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < 30 * 86400:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    place = None
    try:
        r = _requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "PRISM-OSINT/2.3 (https://github.com/NovaCode37/Prism-platform)"},
            timeout=8,
        )
        arr = r.json()
        if arr:
            bb = arr[0].get("boundingbox")
            bbox = [float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])] if bb and len(bb) == 4 else None
            place = {"lat": float(arr[0]["lat"]), "lng": float(arr[0]["lon"]), "bbox": bbox}
    except Exception:
        return None
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(place, f)
    except Exception:
        pass
    return place

def _scan_path(scan_id: str) -> str:
    return os.path.join(_SCANS_DIR, f"{scan_id}.json")

def _save_scan(scan_id: str, data: Dict) -> None:
    safe = {k: v for k, v in data.items() if k != "results" or v is not None}
    try:
        with open(_scan_path(scan_id), "w", encoding="utf-8") as f:
            json.dump(safe, f, default=str)
    except Exception:
        pass

def _load_scan(scan_id: str) -> Optional[Dict]:
    if scan_id in _scans:
        return _scans[scan_id]
    p = _scan_path(scan_id)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def _list_scans_from_disk(principal: Optional[str] = None) -> List[Dict]:
    result = []
    try:
        for fname in os.listdir(_SCANS_DIR):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(_SCANS_DIR, fname), "r", encoding="utf-8") as f:
                    s = json.load(f)
            except Exception:
                continue
            if principal is not None:
                if (s.get("owner") or ANONYMOUS_PRINCIPAL) != principal:
                    continue
            result.append(s)
    except Exception:
        pass
    result.sort(key=lambda s: s.get("started_at") or "", reverse=True)
    return result[:50]

def _scan_visible_to(scan: Dict, principal: str) -> bool:
    return (scan.get("owner") or ANONYMOUS_PRINCIPAL) == principal

def _evict_old_scans() -> None:
    if len(_scans) <= MAX_STORED_SCANS:
        return
    completed = sorted(
        ((k, v) for k, v in _scans.items() if v.get("status") in ("completed", "error")),
        key=lambda x: x[1].get("started_at", ""),
    )
    to_remove = len(_scans) - MAX_STORED_SCANS
    for k, _ in completed[:to_remove]:
        _scans.pop(k, None)
        _queues.pop(k, None)

class ScanRequest(BaseModel):
    target: str
    scan_type: str = "auto"
    modules: List[str] = []
    webhook_url: Optional[str] = None
    force_refresh: bool = False

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

def _is_public_ip(addr) -> bool:
    return not (
        addr.is_private or addr.is_loopback or addr.is_reserved
        or addr.is_link_local or addr.is_multicast or addr.is_unspecified
    )

def _resolve_all_public(hostname: str) -> None:
    import ipaddress
    import socket
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        try:
            fallback_ip = socket.gethostbyname(hostname)
        except socket.gaierror:
            raise ValueError("webhook_url hostname cannot be resolved")
        try:
            addr = ipaddress.ip_address(fallback_ip)
        except ValueError:
            raise ValueError("webhook_url resolved to an invalid address")
        if not _is_public_ip(addr):
            raise ValueError("webhook_url resolves to a private/internal address")
        return
    seen = set()
    for fam, _t, _p, _c, sa in infos:
        ip_str = sa[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("webhook_url resolved to an invalid address")
        if not _is_public_ip(addr):
            raise ValueError("webhook_url resolves to a private/internal address")
    if not seen:
        raise ValueError("webhook_url hostname did not resolve")

def _validate_webhook_url(url: str) -> str:
    from urllib.parse import urlparse
    if not url or len(url) > 2048:
        raise ValueError("webhook_url is empty or too long")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("webhook_url must be http(s) with a hostname")
    _resolve_all_public(parsed.hostname)
    try:
                                                                            
                                                              
        _requests.head(url, timeout=3, allow_redirects=False)
    except Exception:
                                                                       
        pass
    return url

def _send_webhook(url: str, payload: Dict[str, Any]) -> None:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return
    try:
        _resolve_all_public(parsed.hostname)
    except ValueError as e:
        msg = str(e)
        if "cannot be resolved" not in msg and "did not resolve" not in msg:
            return

    webhook_format = os.environ.get("WEBHOOK_FORMAT", "raw")
    if webhook_format == "slack":
        payload = format_slack(payload)
    elif webhook_format == "discord":
        payload = format_discord(payload)

    headers = {"Content-Type": "application/json", "User-Agent": "PRISM-Webhook/2.1.2"}
    if WEBHOOK_SECRET:
        headers["X-Prism-Secret"] = WEBHOOK_SECRET
    try:
        _requests.post(
            url, json=payload, headers=headers,
            timeout=10, allow_redirects=False,
        )
    except TypeError:
        try:
            _requests.post(
                url, json=payload, headers=headers,
                timeout=10,
            )
        except Exception:
            pass
    except Exception:
        pass

def _detect_type(target: str) -> str:
    if "@" in target:
        return "email"
    parts = target.replace("+", "").replace("-", "").replace(" ", "")
    if parts.isdigit():
        return "phone"
    t = target.lstrip("@")
    if t.startswith("t.me/") or t.startswith("telegram.me/"):
        return "telegram"
    if "." in target:
        segs = target.split(".")
        if len(segs) == 4 and all(s.isdigit() for s in segs):
            return "ip"
        return "domain"
    return "username"

async def _push(scan_id: str, msg: Dict) -> None:
    scan = _scans.get(scan_id)
    if scan is not None:
        if "progress" not in scan:
            scan["progress"] = []
        scan["progress"].append(msg)
        _save_scan(scan_id, scan)
    q = _queues.get(scan_id)
    if q:
        await q.put(msg)

_CACHED_MODULES = {"shodan", "hlr", "virustotal", "abuseipdb", "geoip"}

def _done_message(name: str, result: Any, cached: bool = False) -> Dict[str, Any]:
    status = classify(result)
    msg: Dict[str, Any] = {"type": "module_done", "module": name, "status": status}
    if cached:
        msg["cached"] = True
    reason = reason_for(result)
    if reason and status != OK:
        msg["reason"] = reason
        if status == ERROR:
            msg["error"] = reason
    return msg


async def _run_module(scan_id: str, name: str, coro_or_func, *args, **kwargs) -> Any:
    await _push(scan_id, {"type": "module_start", "module": name})
    cache_target = args[0] if args else None
    force_refresh = bool(_scans.get(scan_id, {}).get("force_refresh"))
    if not force_refresh and name in _CACHED_MODULES and cache_target:
        cached = _get_cached(name, str(cache_target))
        # Ignore legacy non-OK cache entries so the module can re-run.
        if cached is not None and classify(cached) == OK:
            await _push(scan_id, _done_message(name, cached, cached=True))
            return cached
    try:
        if asyncio.iscoroutinefunction(coro_or_func):
            result = await coro_or_func(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: coro_or_func(*args, **kwargs))
        status = classify(result)
        if isinstance(result, dict) and "status" not in result:
            result["status"] = status
        # Cache only successful results so a missing key is not frozen in cache.
        if name in _CACHED_MODULES and cache_target and status == OK:
            _set_cache(name, str(cache_target), result)
        await _push(scan_id, _done_message(name, result))
        return result
    except Exception as exc:
        await _push(scan_id, {"type": "module_done", "module": name, "status": ERROR, "error": str(exc)})
        return {"error": str(exc), "status": ERROR}

async def _execute_scan(scan_id: str, target: str, scan_type: str, modules: list, webhook_url: Optional[str] = None) -> None:
    results: Dict[str, Any] = {}
    all_modules = not modules

    def want(name: str) -> bool:
        return all_modules or name in modules

    try:
        if scan_type in ("domain", "ip"):
            if want("whois") and scan_type == "domain":
                from modules.extra_tools import WhoisLookup
                results["whois"] = await _run_module(scan_id, "whois", WhoisLookup().lookup, target)

            if want("dns") and scan_type == "domain":
                from modules.extra_tools import DNSLookup
                results["dns"] = await _run_module(scan_id, "dns", DNSLookup().lookup, target)

            if want("geoip"):
                from modules.extra_tools import GeoIPLookup
                results["geoip"] = await _run_module(scan_id, "geoip", GeoIPLookup().lookup, target)

            if want("cert_transparency") and scan_type == "domain":
                from modules.cert_transparency import CertTransparency
                results["cert_transparency"] = await _run_module(
                    scan_id, "cert_transparency", CertTransparency().search, target
                )

            if want("website") and scan_type == "domain":
                from modules.extra_tools import WebsiteAnalyzer
                results["website"] = await _run_module(
                    scan_id, "website", WebsiteAnalyzer().analyze, target
                )

            if want("wayback") and scan_type == "domain":
                                                                            
                                                                              
                                                                            
                                                            
                from modules.wayback import WaybackMachine
                wb = WaybackMachine()
                wayback_snap = await _run_module(
                    scan_id, "wayback", wb.get_snapshots, target, 15
                )
                wayback_urls = await _run_module(
                    scan_id, "wayback_urls", wb.get_all_urls, target, 200
                )
                merged = dict(wayback_snap) if isinstance(wayback_snap, dict) else {}
                if isinstance(wayback_urls, dict):
                    merged["urls"] = wayback_urls.get("urls", [])
                    merged["total_urls"] = wayback_urls.get("total", 0)
                    merged["interesting"] = wayback_urls.get("interesting", [])
                                                                          
                                                                           
                    if wayback_urls.get("error") and not merged.get("error"):
                        merged["urls_error"] = wayback_urls["error"]
                results["wayback"] = merged

            if want("shodan"):
                from modules.shodan_lookup import ShodanLookup
                ip = target
                if scan_type == "domain":
                    import socket
                    try:
                        ip = socket.gethostbyname(target)
                    except Exception:
                        ip = target
                results["shodan"] = await _run_module(scan_id, "shodan", ShodanLookup().host_info, ip)

            if want("virustotal"):
                from modules.threat_intel import VirusTotal
                vt = VirusTotal()
                if scan_type == "ip":
                    results["virustotal"] = await _run_module(scan_id, "virustotal", vt.check_ip, target)
                else:
                    results["virustotal"] = await _run_module(scan_id, "virustotal", vt.check_domain, target)

            if want("abuseipdb") and scan_type == "ip":
                from modules.threat_intel import AbuseIPDB
                results["abuseipdb"] = await _run_module(scan_id, "abuseipdb", AbuseIPDB().check_ip, target)

            if want("onion") and scan_type == "domain":
                from modules.onion_checker import OnionChecker
                results["onion"] = await _run_module(scan_id, "onion", OnionChecker().check, target)

            if want("censys"):
                from modules.censys_lookup import CensysLookup
                cl = CensysLookup()
                if scan_type == "domain":
                    results["censys"] = await _run_module(scan_id, "censys", cl.search_domain, target)
                else:
                    results["censys"] = await _run_module(scan_id, "censys", cl.search_ip, target)

        elif scan_type == "email":
            if want("smtp"):
                from modules.smtp_verify import SMTPVerifier
                results["smtp"] = await _run_module(scan_id, "smtp", SMTPVerifier().verify_email, target)

            if want("leaks"):
                from modules.leak_lookup import LeakLookup
                results["breaches"] = await _run_module(
                    scan_id, "leaks", LeakLookup().check_email_full, target
                )

            if want("emailrep"):
                from modules.hunter import EmailRepLookup
                results["emailrep"] = await _run_module(
                    scan_id, "emailrep", EmailRepLookup().lookup, target
                )

        elif scan_type == "phone":
            if want("hlr"):
                from modules.hlr_lookup import HLRLookup
                hlr_obj = HLRLookup()
                hlr = await _run_module(scan_id, "hlr", hlr_obj.validate_phone, target)
                results["hlr"] = hlr
                owner = await _run_module(
                    scan_id, "phone_owner", hlr_obj.reverse_lookup,
                    hlr.get("formatted") or target
                )
                results["phone_owner"] = owner
                results["phone"] = {
                    "valid": hlr.get("valid"),
                    "country_name": hlr.get("country_name") or hlr.get("country"),
                    "country_code": hlr.get("country_code"),
                    "carrier": hlr.get("carrier"),
                    "line_type": hlr.get("line_type"),
                    "region": hlr.get("region"),
                    "timezones": hlr.get("timezones"),
                    "reverse": {
                        "name": ", ".join(owner.get("names", [])) or None,
                        "address": owner.get("city"),
                        "source": ", ".join(owner.get("sources", [])) or None,
                    } if owner else None,
                }

        elif scan_type == "telegram":
            from modules.telegram_lookup import TelegramLookup
            from config import TELEGRAM_BOT_TOKEN
            tg = TelegramLookup()
            tg_target = target.lstrip("@").replace("t.me/", "").replace("telegram.me/", "").strip()
            results["telegram"] = await _run_module(
                scan_id, "telegram", tg.run_lookup, tg_target, TELEGRAM_BOT_TOKEN or None
            )

        elif scan_type == "username":
            if want("blackbird"):
                from modules.blackbird import Blackbird
                bb = Blackbird(timeout=10, max_concurrent=25)
                await _run_module(scan_id, "blackbird", bb.search, target)
                results["blackbird"] = [
                    {"site": r.site, "url": r.url, "status": r.status, "response_time": r.response_time}
                    for r in bb.results
                ]

            if want("maigret"):
                from modules.maigret_wrapper import MaigretWrapper
                results["maigret"] = await _run_module(
                    scan_id, "maigret", MaigretWrapper().search, target
                )

            if want("github"):
                from modules.github_recon import GitHubRecon
                results["github"] = await _run_module(
                    scan_id, "github", GitHubRecon().lookup, target
                )

        await _push(scan_id, {"type": "module_start", "module": "opsec_score"})
        opsec = score_from_results(results)
        results["opsec_score"] = opsec
        await _push(scan_id, {"type": "module_done", "module": "opsec_score", "status": OK})

        graph = build_graph(target, scan_type, results)
        results["graph"] = graph

        report_path = generate_html_report(target, scan_type, results, opsec)
        results["report_path"] = report_path

        _scans[scan_id].update(
            {
                "status": "completed",
                "results": results,
                "completed_at": datetime.now().isoformat(),
            }
        )
        _save_scan(scan_id, _scans[scan_id])
        await _push(scan_id, {"type": "scan_complete", "scan_id": scan_id})

    except Exception as exc:
        safe_err = str(exc).split("\n")[0][:200]
        _scans[scan_id].update({"status": "error", "error": safe_err})
        _save_scan(scan_id, _scans[scan_id])
        await _push(scan_id, {"type": "scan_error", "error": safe_err})
    finally:
        await _push(scan_id, {"type": "_done"})
        if webhook_url:
            scan_snapshot = _scans.get(scan_id, {})
            payload = {
                "scan_id": scan_id,
                "target": target,
                "scan_type": scan_type,
                "status": scan_snapshot.get("status"),
                "started_at": scan_snapshot.get("started_at"),
                "completed_at": scan_snapshot.get("completed_at"),
                "error": scan_snapshot.get("error"),
                "results": {
                    k: v for k, v in (scan_snapshot.get("results") or {}).items()
                    if k not in ("graph", "report_path")
                },
            }
            threading.Thread(target=_send_webhook, args=(webhook_url, payload), daemon=True).start()

@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}

@app.post("/api/scan", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def start_scan(request: Request, req: ScanRequest):
    target = validate_target(req.target)

    webhook_url = None
    if req.webhook_url:
        try:
            webhook_url = _validate_webhook_url(req.webhook_url.strip())
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    scan_type = req.scan_type if req.scan_type != "auto" else _detect_type(target)
    scan_id = str(uuid.uuid4())

    _evict_old_scans()
    _scans[scan_id] = {
        "scan_id": scan_id,
        "target": target,
        "scan_type": scan_type,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "owner": get_principal(request),
        "results": None,
        "progress": [],
        "force_refresh": req.force_refresh,
    }
    _save_scan(scan_id, _scans[scan_id])
    _queues[scan_id] = asyncio.Queue()

    def _run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_execute_scan(scan_id, target, scan_type, req.modules, webhook_url))
        finally:
            loop.close()

    threading.Thread(target=_run_in_thread, daemon=True).start()

    return {"scan_id": scan_id, "scan_type": scan_type}

@app.get("/api/scan/{scan_id}", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def get_scan(request: Request, scan_id: str):
    validate_scan_id(scan_id)
    scan = _load_scan(scan_id)
    if not scan or not _scan_visible_to(scan, get_principal(request)):
        return JSONResponse({"error": "Scan not found"}, status_code=404)
    safe = {k: v for k, v in scan.items() if k not in ("results", "owner")}
    if scan.get("results"):
        res_copy = {k: v for k, v in scan["results"].items() if k not in ("graph", "report_path")}
        safe["results"] = res_copy
    safe["progress"] = scan.get("progress", [])
    return safe

@app.get("/api/scan/{scan_id}/graph", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def get_graph(request: Request, scan_id: str):
    validate_scan_id(scan_id)
    scan = _load_scan(scan_id)
    if not scan or not _scan_visible_to(scan, get_principal(request)) or not scan.get("results"):
        return JSONResponse({"error": "Scan not found or not completed"}, status_code=404)
    return scan["results"].get("graph", {"nodes": [], "edges": []})

                                                                       
                                                                        
                                                                   

@app.get("/api/scan/{scan_id}/map", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def get_map_data(request: Request, scan_id: str):
    validate_scan_id(scan_id)
    scan = _load_scan(scan_id)
    if not scan or not _scan_visible_to(scan, get_principal(request)) or not scan.get("results"):
        return JSONResponse({"error": "Scan not found or not completed"}, status_code=404)

    results = scan["results"]
    markers = []

    geoip = results.get("geoip", {})
    if geoip and geoip.get("loc") and not geoip.get("error"):
        try:
            lat, lng = map(float, geoip["loc"].split(","))
            markers.append({
                "lat": lat, "lng": lng,
                "ip": geoip.get("ip"),
                "label": geoip.get("ip", scan["target"]),
                "city": geoip.get("city"),
                "region": geoip.get("region"),
                "country": geoip.get("country_name") or geoip.get("country"),
                "org": geoip.get("org"),
                "timezone": geoip.get("timezone"),
                "type": "host",
            })
        except (ValueError, AttributeError):
            pass

    shodan = results.get("shodan", {})
    if shodan and not shodan.get("error"):
        sloc = shodan.get("location", {})
        if sloc and sloc.get("latitude") and sloc.get("longitude"):
            lat, lng = sloc["latitude"], sloc["longitude"]
            if not any(abs(m["lat"] - lat) < 0.01 and abs(m["lng"] - lng) < 0.01 for m in markers):
                markers.append({
                    "lat": lat, "lng": lng,
                    "ip": shodan.get("ip_str"),
                    "label": shodan.get("ip_str", scan["target"]),
                    "city": sloc.get("city"),
                    "region": sloc.get("region_code"),
                    "country": sloc.get("country_name"),
                    "org": shodan.get("org"),
                    "type": "shodan",
                })

    hlr = results.get("hlr", {})
    if hlr and not hlr.get("error"):
        country_str = hlr.get("country_name") or hlr.get("country") or ""
        region_str = hlr.get("location") or hlr.get("region") or ""
        phone_label = hlr.get("formatted") or hlr.get("phone")
        raw_lat = hlr.get("lat", hlr.get("latitude"))
        raw_lng = hlr.get("lng", hlr.get("longitude"))
        lat = None
        lng = None
        try:
            if raw_lat is not None and raw_lng is not None:
                lat = float(raw_lat)
                lng = float(raw_lng)
        except (TypeError, ValueError):
            lat = None
            lng = None

        if lat is not None and lng is not None:
            approx = bool(hlr.get("approximate", False))
            markers.append({
                "lat": lat, "lng": lng,
                "ip": phone_label,
                "label": phone_label,
                "city": region_str or None,
                "country": country_str or None,
                "org": hlr.get("carrier"),
                "timezone": (hlr.get("timezones") or [None])[0],
                "type": "phone",
                "valid": hlr.get("valid"),
                "line_type": hlr.get("line_type"),
                "approximate": approx,
                "precision": hlr.get("precision") or ("approximate" if approx else "exact"),
            })

    center = markers[0] if markers else None
    zoom = 5 if (markers and markers[0].get("type") == "phone") else None

    info = None
    if not markers:
        hlr = results.get("hlr") or {}
        phone = results.get("phone") or {}
        country = hlr.get("country_name") or hlr.get("country") or phone.get("country_name")
        carrier = hlr.get("carrier") or phone.get("carrier")
        region = hlr.get("location") or hlr.get("region") or phone.get("region")
        phone_label = hlr.get("formatted") or hlr.get("phone") or scan["target"]

        place = None
        if region or country:
            place = _geocode_place(", ".join(p for p in (region, country) if p))

        if place:
            bbox = place.get("bbox")
            if bbox:
                clat, clng = (bbox[0] + bbox[1]) / 2, (bbox[2] + bbox[3]) / 2
            else:
                clat, clng = place["lat"], place["lng"]
            markers.append({
                "lat": clat, "lng": clng,
                "bbox": bbox,
                "ip": phone_label, "label": phone_label,
                "city": region or None, "country": country or None,
                "org": carrier, "type": "phone",
                "approximate": True,
                "precision": "region" if region else "country",
            })
            center = markers[0]
            zoom = 7 if region else 4
        elif country or carrier or region:
            info = {
                "reason": "Phone numbers don't expose precise GPS coordinates.",
                "country": country or None,
                "carrier": carrier or None,
                "region": region or None,
            }

    return {"markers": markers, "center": center, "zoom": zoom, "info": info}

def _normalize_lang(raw: Optional[str]) -> str:
    from modules.report_i18n import SUPPORTED_LANGS
    if not raw:
        return "en"
    key = raw.lower().split("-")[0].strip()
    return key if key in SUPPORTED_LANGS else "en"

@app.get("/api/scan/{scan_id}/report", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def download_report(request: Request, scan_id: str, lang: str = "en"):
    validate_scan_id(scan_id)
    scan = _load_scan(scan_id)
    if not scan or not _scan_visible_to(scan, get_principal(request)) or not scan.get("results"):
        return JSONResponse({"error": "Scan not found or not completed"}, status_code=404)
    results = scan["results"]
    opsec = results.get("opsec_score")
    lang = _normalize_lang(lang)
    loop = asyncio.get_event_loop()
    report_path = await loop.run_in_executor(
        None,
        lambda: generate_html_report(scan["target"], scan["scan_type"], results, opsec, lang=lang),
    )
    scan["results"]["report_path"] = report_path
    return FileResponse(
        report_path,
        media_type="text/html",
        filename=os.path.basename(report_path),
    )

@app.get("/api/scan/{scan_id}/report/pdf", dependencies=[Depends(require_api_key)])
@limiter.limit("5/minute")
async def download_report_pdf(request: Request, scan_id: str, lang: str = "en"):
    validate_scan_id(scan_id)
    scan = _load_scan(scan_id)
    if not scan or not _scan_visible_to(scan, get_principal(request)) or not scan.get("results"):
        return JSONResponse({"error": "Scan not found or not completed"}, status_code=404)
    results = scan["results"]
    opsec = results.get("opsec_score")
    lang = _normalize_lang(lang)
    loop = asyncio.get_event_loop()
    try:
        pdf_path = await loop.run_in_executor(
            None,
            lambda: generate_pdf_report(scan["target"], scan["scan_type"], results, opsec, lang=lang),
        )
    except ImportError as e:
        return JSONResponse({"error": str(e)}, status_code=501)
    except Exception as e:
        return JSONResponse({"error": f"PDF generation failed: {str(e)[:200]}"}, status_code=500)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path),
    )

@app.post("/api/url-scan", dependencies=[Depends(require_api_key)])
@limiter.limit("20/minute")
async def scan_url(request: Request, req: dict):
    url = req.get("url", "").strip()
    if not url or len(url) > 2048:
        return JSONResponse({"error": "No URL provided or URL too long"}, status_code=400)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    validate_url_not_private(url)
    from modules.url_scanner import URLScanner
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, URLScanner().scan, url)
    return result

_OUI_DATA: Optional[Dict[str, str]] = None

def _get_oui_data() -> Dict[str, str]:
    global _OUI_DATA
    if _OUI_DATA is None:
        oui_path = os.path.join(os.path.dirname(__file__), "oui_data.json")
        try:
            with open(oui_path, "r", encoding="utf-8") as f:
                _OUI_DATA = json.load(f)
        except Exception:
            _OUI_DATA = {}
    return _OUI_DATA

def _lookup_local_oui(mac: str) -> Optional[str]:
    oui_data = _get_oui_data()
    prefix = mac.upper().replace("-", ":")
    first_three = ":".join(prefix.split(":")[:3])
    return oui_data.get(first_three)

@app.post("/api/mac-lookup", dependencies=[Depends(require_api_key)])
@limiter.limit("20/minute")
async def mac_lookup(request: Request, req: dict):
    mac = req.get("mac", "").strip()
    if not mac or len(mac) > 17:
        return JSONResponse({"error": "No MAC address provided or format too long"}, status_code=400)
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    if not mac_pattern.match(mac):
        return JSONResponse({"error": "Invalid MAC address format. Expected: 00:00:5e:00:53:af"}, status_code=400)

    normalized_mac = mac.upper().replace("-", ":")
    cached = _get_cached("mac", normalized_mac)
    if cached:
        return cached

    vendor = _lookup_local_oui(normalized_mac)
    if vendor:
        result = {"mac": normalized_mac, "vendor": vendor, "source": "local"}
        _set_cache("mac", normalized_mac, result)
        return result

    try:
        loop = asyncio.get_event_loop()
        def _fetch():
            resp = _requests.get(f"https://api.macvendors.com/{mac}", timeout=10)
            if resp.status_code == 200:
                return {"mac": normalized_mac, "vendor": resp.text.strip(), "source": "api"}
            elif resp.status_code == 404:
                return {"mac": normalized_mac, "vendor": None, "error": "Not found", "source": "api"}
            else:
                return {"mac": normalized_mac, "vendor": None, "error": f"API returned status {resp.status_code}", "source": "api"}
        result = await loop.run_in_executor(None, _fetch)
        if result.get("vendor") and not result.get("error"):
            _set_cache("mac", normalized_mac, result)
        return result
    except Exception as e:
        local_vendor = _lookup_local_oui(normalized_mac)
        if local_vendor:
            result = {"mac": normalized_mac, "vendor": local_vendor, "source": "local_fallback"}
            _set_cache("mac", normalized_mac, result)
            return result
        return JSONResponse({"error": str(e), "mac": normalized_mac, "vendor": None}, status_code=500)

@app.post("/api/crypto", dependencies=[Depends(require_api_key)])
@limiter.limit("20/minute")
async def crypto_lookup(request: Request, req: dict):
    address = req.get("address", "").strip()
    if not address or len(address) > 256:
        return JSONResponse({"error": "No address provided or address too long"}, status_code=400)
    from modules.crypto_lookup import CryptoLookup
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, CryptoLookup().lookup, address)
    return result

@app.post("/api/darkweb", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def darkweb_search(request: Request, req: dict):
    query = req.get("query", "").strip()
    if not query or len(query) > 512:
        return JSONResponse({"error": "No query provided or query too long"}, status_code=400)
    from modules.darkweb_search import DarkWebSearch
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, DarkWebSearch().search, query)
    return result

@app.post("/api/qr-decode", dependencies=[Depends(require_api_key), Depends(check_upload_size)])
@limiter.limit("20/minute")
async def decode_qr(request: Request, file: UploadFile = File(...)):
    from web.security import MAX_UPLOAD_BYTES
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "File too large"}, status_code=413)
    from modules.qr_decoder import QRDecoder
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, QRDecoder().decode, data, file.filename)
    return result

@app.post("/api/email-headers", dependencies=[Depends(require_api_key)])
@limiter.limit("20/minute")
async def analyze_email_headers(request: Request, req: dict):
    raw = req.get("headers", "").strip()
    if not raw or len(raw) > 50000:
        return JSONResponse({"error": "No headers provided or input too large"}, status_code=400)
    from modules.email_header_analyzer import analyze_headers
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, analyze_headers, raw)
    return result

@app.post("/api/metadata", dependencies=[Depends(require_api_key), Depends(check_upload_size)])
@limiter.limit("20/minute")
async def extract_metadata_endpoint(request: Request, file: UploadFile = File(...)):
    import tempfile, shutil
    ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic", ".heif", ".webp", ".pdf", ".docx", ".docm"}
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in ALLOWED_EXTS:
        return JSONResponse({"error": f"Unsupported file type: {suffix}"}, status_code=400)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        from modules.metadata_extractor import extract_metadata
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, extract_metadata, tmp_path)
        result["filename"] = file.filename
        result["file_type"] = result.pop("format", None)
        result["file_size"] = result.pop("size_bytes", None)
        result["exif"] = result.pop("raw_exif", {})
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

@app.post("/api/ai/summary", dependencies=[Depends(require_api_key)])
@limiter.limit("5/minute")
async def ai_summary(request: Request, req: dict):
    if not _LLM_KEY:
        return JSONResponse({"error": "OPENROUTER_API_KEY or GROQ_API_KEY not set in .env"}, status_code=400)
    scan_id = req.get("scan_id")
    scan = _load_scan(scan_id) if scan_id else None
    if not scan or not _scan_visible_to(scan, get_principal(request)) or not scan.get("results"):
        return JSONResponse({"error": "Scan not found"}, status_code=404)

    results = scan["results"]
    summary_data = {k: v for k, v in results.items()
                    if k not in ("graph", "report_path") and v and not (isinstance(v, dict) and v.get("error"))}

    prompt = (
        f"You are a professional OSINT analyst. Analyze the following reconnaissance results for target '{scan['target']}' "
        f"(type: {scan['scan_type']}) and provide:\n"
        "1. A concise executive summary (3-4 sentences)\n"
        "2. Key findings (bullet points)\n"
        "3. Risk assessment (Low/Medium/High with reasoning)\n"
        "4. Recommended next investigation steps\n\n"
        f"Data:\n{json.dumps(summary_data, indent=2, default=str)[:6000]}"
    )

    try:
        loop = asyncio.get_event_loop()
        def _llm_call():
            r = _requests.post(
                _LLM_URL,
                headers={"Authorization": f"Bearer {_LLM_KEY}", "Content-Type": "application/json",
                         "HTTP-Referer": "https://getprism.su", "X-Title": "PRISM OSINT"},
                json={"model": _LLM_MODEL, "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.3, "max_tokens": 1024},
                timeout=30,
            )
            return r.json()
        data = await loop.run_in_executor(None, _llm_call)
        if "error" in data:
            return JSONResponse({"error": data["error"].get("message", str(data["error"]))}, status_code=400)
        if not data.get("choices"):
            return JSONResponse({"error": f"Unexpected response: {json.dumps(data)[:300]}"}, status_code=500)
        text = data["choices"][0]["message"]["content"]
        return {"summary": text, "model": data.get("model", _LLM_MODEL)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/ai/chat", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def ai_chat(request: Request, req: dict):
    if not _LLM_KEY:
        return JSONResponse({"error": "OPENROUTER_API_KEY or GROQ_API_KEY not set in .env"}, status_code=400)
    scan_id = req.get("scan_id")
    message = req.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "No message provided"}, status_code=400)
    scan = _load_scan(scan_id) if scan_id else None
    if scan and not _scan_visible_to(scan, get_principal(request)):
                                                                             
        scan = None
    context = ""
    if scan and scan.get("results"):
        results = scan["results"]
        summary_data = {k: v for k, v in results.items()
                        if k not in ("graph", "report_path") and v
                        and not (isinstance(v, dict) and v.get("error"))}
        context = (f"OSINT scan of '{scan['target']}' (type: {scan['scan_type']}):\n"
                   f"{json.dumps(summary_data, indent=2, default=str)[:4000]}\n\n")
    try:
        loop = asyncio.get_event_loop()
        def _llm_chat():
            r = _requests.post(
                _LLM_URL,
                headers={"Authorization": f"Bearer {_LLM_KEY}", "Content-Type": "application/json",
                         "HTTP-Referer": "https://getprism.su", "X-Title": "PRISM OSINT"},
                json={
                    "model": _LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": (
                            "You are a professional OSINT analyst assistant. "
                            + (f"Context:\n{context}" if context else "Answer general OSINT questions concisely.")
                        )},
                        {"role": "user", "content": message},
                    ],
                    "temperature": 0.5,
                    "max_tokens": 512,
                },
                timeout=30,
            )
            return r.json()
        data = await loop.run_in_executor(None, _llm_chat)
        if "error" in data:
            return JSONResponse({"error": data["error"].get("message", str(data["error"]))}, status_code=400)
        if not data.get("choices"):
            return JSONResponse({"error": f"Unexpected response: {json.dumps(data)[:200]}"}, status_code=500)
        reply = data["choices"][0]["message"]["content"]
        return {"reply": reply, "model": data.get("model", "")}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/scans", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def list_scans(request: Request):
    all_scans = _list_scans_from_disk(principal=get_principal(request))
    return [
        {
            "scan_id": s.get("scan_id", ""),
            "target": s.get("target", ""),
            "scan_type": s.get("scan_type", ""),
            "status": s.get("status", ""),
            "started_at": s.get("started_at", ""),
        }
        for s in all_scans
    ]

@app.delete("/api/scans", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def clear_scans(request: Request):
    principal = get_principal(request)
    deleted = 0

    try:
        for fname in os.listdir(_SCANS_DIR):
            if not fname.endswith(".json"):
                continue

            path = os.path.join(_SCANS_DIR, fname)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    scan = json.load(f)
            except Exception:
                continue

            if (scan.get("owner") or ANONYMOUS_PRINCIPAL) != principal:
                continue

            try:
                os.remove(path)
                deleted += 1
            except Exception:
                pass

        return {"deleted": deleted}

    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )




@app.websocket("/ws/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: str):
    try:
        validate_scan_id(scan_id)
    except Exception:
        await websocket.close(code=1008)
        return
    token = websocket.query_params.get("api_key", "")
    principal = principal_for_key(token)
    if principal is None:
        await websocket.close(code=1008)
        return
                                                                              
    scan = _scans.get(scan_id) or _load_scan(scan_id)
    if scan and not _scan_visible_to(scan, principal):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    q = _queues.get(scan_id)
    if not q:
        await websocket.send_json({"type": "error", "error": "Unknown scan ID"})
        await websocket.close()
        return

    try:
        while True:
            msg = await asyncio.wait_for(q.get(), timeout=120)
            await websocket.send_json(msg)
            if msg.get("type") == "_done":
                break
    except asyncio.TimeoutError:
        await websocket.send_json({"type": "error", "error": "Scan timed out"})
    except WebSocketDisconnect:
        pass
    finally:
        _queues.pop(scan_id, None)
        try:
            await websocket.close()
        except Exception:
            pass

def _frontend_config_script() -> str:
    config = {
        "apiUrl": os.getenv("NEXT_PUBLIC_API_URL", ""),
        "apiKey": os.getenv("PRISM_UI_API_KEY", os.getenv("NEXT_PUBLIC_API_KEY", "")),
        "basePath": _BASE_PATH,
        "demoMode": env_flag("PRISM_DEMO_MODE"),
    }
    payload = json.dumps(config, separators=(",", ":")).replace("</", "<\\/")
    return f'<script id="prism-runtime-config">window.__PRISM_CONFIG__={payload};</script>'

def _frontend_not_found() -> JSONResponse:
    return JSONResponse({"detail": "Frontend build not found"}, status_code=404)

def _is_reserved_frontend_path(path: str) -> bool:
    first_segment = path.strip("/").split("/", 1)[0]
    return first_segment in _RESERVED_FRONTEND_PATHS

def _safe_frontend_file(path: str) -> Optional[Path]:
    if not _FRONTEND_DIR.is_dir():
        return None
    root = _FRONTEND_DIR.resolve()
    try:
        candidate = (root / path).resolve()
        candidate.relative_to(root)
    except ValueError:
        return None
    if candidate.is_dir():
        index = candidate / "index.html"
        return index if index.is_file() else None
    return candidate if candidate.is_file() else None

def _serve_frontend_index(index_path: Path) -> Response:
    html = index_path.read_text(encoding="utf-8")
    script = _frontend_config_script()
    if "</head>" in html:
        html = html.replace("</head>", f"{script}</head>", 1)
    else:
        html = f"{script}{html}"
    return Response(html, media_type="text/html")

def _serve_frontend_path(path: str):
    normalized = path.strip("/")
    if normalized and _is_reserved_frontend_path(normalized):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    file_path = _safe_frontend_file(normalized or "index.html")
    if file_path:
        if file_path.name == "index.html":
            return _serve_frontend_index(file_path)
        return FileResponse(file_path)

    index_path = _safe_frontend_file("index.html")
    if index_path:
        return _serve_frontend_index(index_path)
    return _frontend_not_found()

@app.get("/", include_in_schema=False)
async def frontend_root():
    return _serve_frontend_path("")

@app.get("/{full_path:path}", include_in_schema=False)
async def frontend_fallback(full_path: str):
    return _serve_frontend_path(full_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8080, reload=True, proxy_headers=False)
