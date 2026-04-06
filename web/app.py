import asyncio
import json
import os
import sys
import uuid
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import requests as _requests

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config  

from modules.graph_builder import build_graph
from modules.opsec_score import score_from_results
from modules.report_generator import generate_html_report

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
_LLM_KEY = OPENROUTER_API_KEY or GROQ_API_KEY
_LLM_URL = "https://openrouter.ai/api/v1/chat/completions" if OPENROUTER_API_KEY else "https://api.groq.com/openai/v1/chat/completions"
_LLM_MODEL = "qwen/qwen3.6-plus:free" if OPENROUTER_API_KEY else "llama-3.1-8b-instant"

from web.security import require_api_key, validate_target, check_upload_size, get_allowed_origins, limiter, validate_scan_id, validate_url_not_private

_disable_docs = os.getenv("DISABLE_DOCS", "").lower() in ("1", "true", "yes")
app = FastAPI(
    title="OSINT Toolkit",
    version="2.0",
    docs_url=None if _disable_docs else "/docs",
    redoc_url=None if _disable_docs else "/redoc",
    openapi_url=None if _disable_docs else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda req, exc: JSONResponse({"error": "Rate limit exceeded. Slow down."}, status_code=429))

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

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

_scans: Dict[str, Dict] = {}
_queues: Dict[str, asyncio.Queue] = {}
MAX_STORED_SCANS = int(os.getenv("MAX_STORED_SCANS", "200"))

_SCANS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scan_data")
os.makedirs(_SCANS_DIR, exist_ok=True)

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

def _list_scans_from_disk() -> List[Dict]:
    result = []
    try:
        for fname in sorted(os.listdir(_SCANS_DIR), reverse=True):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(_SCANS_DIR, fname), "r", encoding="utf-8") as f:
                        s = json.load(f)
                        result.append(s)
                except Exception:
                    pass
            if len(result) >= 50:
                break
    except Exception:
        pass
    return result

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

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

class ScanRequest(BaseModel):
    target: str
    scan_type: str = "auto"
    modules: List[str] = []

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

async def _run_module(scan_id: str, name: str, coro_or_func, *args, **kwargs) -> Any:
    await _push(scan_id, {"type": "module_start", "module": name})
    try:
        if asyncio.iscoroutinefunction(coro_or_func):
            result = await coro_or_func(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: coro_or_func(*args, **kwargs))
        await _push(scan_id, {"type": "module_done", "module": name, "status": "ok"})
        return result
    except Exception as exc:
        await _push(scan_id, {"type": "module_done", "module": name, "status": "error", "error": str(exc)})
        return {"error": str(exc)}

async def _execute_scan(scan_id: str, target: str, scan_type: str, modules: list) -> None:
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
                results["wayback"] = await _run_module(
                    scan_id, "wayback", WaybackMachine().get_snapshots, target, 15
                )


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

        await _push(scan_id, {"type": "module_start", "module": "opsec_score"})
        opsec = score_from_results(results)
        results["opsec_score"] = opsec
        await _push(scan_id, {"type": "module_done", "module": "opsec_score", "status": "ok"})

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

@app.get("/", response_class=HTMLResponse)
async def index():
    path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(path, encoding="utf-8") as f:
        return f.read()

@app.post("/api/scan", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def start_scan(request: Request, req: ScanRequest):
    target = validate_target(req.target)

    scan_type = req.scan_type if req.scan_type != "auto" else _detect_type(target)
    scan_id = str(uuid.uuid4())

    _evict_old_scans()
    _scans[scan_id] = {
        "scan_id": scan_id,
        "target": target,
        "scan_type": scan_type,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "results": None,
        "progress": [],
    }
    _save_scan(scan_id, _scans[scan_id])
    _queues[scan_id] = asyncio.Queue()

    def _run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_execute_scan(scan_id, target, scan_type, req.modules))
        finally:
            loop.close()

    threading.Thread(target=_run_in_thread, daemon=True).start()

    return {"scan_id": scan_id, "scan_type": scan_type}

@app.get("/api/scan/{scan_id}", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def get_scan(request: Request, scan_id: str):
    validate_scan_id(scan_id)
    scan = _load_scan(scan_id)
    if not scan:
        return JSONResponse({"error": "Scan not found"}, status_code=404)
    safe = {k: v for k, v in scan.items() if k not in ("results",)}
    if scan.get("results"):
        res_copy = {k: v for k, v in scan["results"].items() if k not in ("graph", "report_path")}
        safe["results"] = res_copy
    safe["progress"] = scan.get("progress", [])
    return safe

def _geocode_sync(query: str) -> Optional[Tuple[float, float]]:
    try:
        r = _requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "OSINT-Toolkit/2.0"},
            timeout=8,
        )
        data = r.json()
        if data:
            return (float(data[0]["lat"]), float(data[0]["lon"]))
    except Exception:
        pass
    return None


@app.get("/api/scan/{scan_id}/graph", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def get_graph(request: Request, scan_id: str):
    validate_scan_id(scan_id)
    scan = _load_scan(scan_id)
    if not scan or not scan.get("results"):
        return JSONResponse({"error": "Scan not found or not completed"}, status_code=404)
    return scan["results"].get("graph", {"nodes": [], "edges": []})


_COUNTRY_COORDS: Dict[str, tuple] = {
    "RU": (55.7558, 37.6173), "US": (38.8951, -77.0364), "GB": (51.5074, -0.1278),
    "DE": (52.5200, 13.4050), "FR": (48.8566,  2.3522), "CN": (39.9042, 116.4074),
    "JP": (35.6762, 139.6503),"IN": (28.6139, 77.2090), "BR": (-15.7975,-47.8919),
    "CA": (45.4215,-75.6972), "AU": (-35.2809,149.1300), "UA": (50.4501, 30.5234),
    "PL": (52.2297, 21.0122), "NL": (52.3676,  4.9041), "IT": (41.9028, 12.4964),
    "ES": (40.4168, -3.7038), "SE": (59.3293, 18.0686), "NO": (59.9139, 10.7522),
    "FI": (60.1699, 24.9384), "DK": (55.6761, 12.5683), "CH": (46.9480,  7.4474),
    "AT": (48.2082, 16.3738), "BE": (50.8503,  4.3517), "TR": (39.9334, 32.8597),
    "MX": (19.4326,-99.1332), "AR": (-34.6037,-58.3816),"ZA": (-25.7479, 28.2293),
    "NG": ( 9.0765,  7.3986), "EG": (30.0444, 31.2357), "SA": (24.7136, 46.6753),
    "IR": (35.6892, 51.3890), "PK": (33.7294, 73.0931), "BD": (23.8103, 90.4125),
    "ID": (-6.2088,106.8456), "TH": (13.7563,100.5018), "VN": (21.0285,105.8542),
    "PH": (14.5995,120.9842), "MY": ( 3.1390,101.6869), "SG": ( 1.3521,103.8198),
    "KR": (37.5665,126.9780), "KZ": (51.1811, 71.4460), "UZ": (41.2995, 69.2401),
    "GE": (41.7151, 44.8271), "AZ": (40.4093, 49.8671), "AM": (40.1872, 44.5152),
    "BY": (53.9045, 27.5615), "MD": (47.0105, 28.8638), "RO": (44.4268, 26.1025),
    "BG": (42.6977, 23.3219), "RS": (44.8176, 20.4633), "HR": (45.8150, 15.9819),
    "SK": (48.1486, 17.1077), "CZ": (50.0755, 14.4378), "HU": (47.4979, 19.0402),
    "IL": (31.7683, 35.2137), "AE": (24.4539, 54.3773), "QA": (25.2854, 51.5310),
    "KW": (29.3759, 47.9774), "IQ": (33.3152, 44.3661), "LT": (54.6872, 25.2797),
    "LV": (56.9460, 24.1059), "EE": (59.4370, 24.7536), "PT": (38.7169, -9.1395),
    "GR": (37.9838, 23.7275), "CY": (35.1264, 33.4299), "LU": (49.6117,  6.1319),
    "IE": (53.3498, -6.2603), "NZ": (-41.2865,174.7762), "CL": (-33.4489,-70.6693),
    "CO": ( 4.7110,-74.0721), "PE": (-12.0464,-77.0428), "VE": (10.4806,-66.9036),
    "MM": (19.7633, 96.0785), "LK": ( 6.9271, 79.8612), "NP": (27.7172, 85.3240),
    "AF": (34.5553, 69.2075), "TZ": (-6.3690, 34.8888), "KE": (-1.2921, 36.8219),
    "ET": ( 8.9806, 38.7578), "MA": (33.9716, -6.8498), "DZ": (36.7372,  3.0865),
    "TN": (36.8189,  9.8253), "LY": (32.9022, 13.1805), "GH": ( 5.6037, -0.1870),
    "CI": ( 5.3600, -4.0083), "CM": ( 3.8480, 11.5021), "AO": (-8.8390, 13.2894),
    "MZ": (-25.9692, 32.5732),"ZW": (-17.8292, 31.0522),"SN": (14.7167,-17.4677),
    "UG": ( 0.3476, 32.5825), "RW": (-1.9403, 29.8739),
}

@app.get("/api/scan/{scan_id}/map", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def get_map_data(request: Request, scan_id: str):
    validate_scan_id(scan_id)
    scan = _load_scan(scan_id)
    if not scan or not scan.get("results"):
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
        coords: Optional[Tuple[float, float]] = None
        country_str = hlr.get("country_name") or hlr.get("country") or ""
        region_str  = hlr.get("location") or hlr.get("region") or ""

        if region_str and country_str:
            loop = asyncio.get_event_loop()
            coords = await loop.run_in_executor(
                None, _geocode_sync, f"{region_str}, {country_str}"
            )
        if not coords and country_str:
            loop = asyncio.get_event_loop()
            coords = await loop.run_in_executor(None, _geocode_sync, country_str)
        if not coords:
            cc = (hlr.get("country_code") or "").upper()
            raw = _COUNTRY_COORDS.get(cc)
            coords = raw if raw else None

        if coords:
            markers.append({
                "lat": coords[0], "lng": coords[1],
                "ip": hlr.get("formatted") or hlr.get("phone"),
                "label": hlr.get("formatted") or hlr.get("phone"),
                "city": region_str or None,
                "country": country_str or None,
                "org": hlr.get("carrier"),
                "timezone": (hlr.get("timezones") or [None])[0],
                "type": "phone",
                "valid": hlr.get("valid"),
                "line_type": hlr.get("line_type"),
            })

    center = markers[0] if markers else None
    zoom = 4 if (markers and markers[0].get("type") == "phone") else None
    return {"markers": markers, "center": center, "zoom": zoom}


@app.get("/api/scan/{scan_id}/report", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def download_report(request: Request, scan_id: str):
    validate_scan_id(scan_id)
    scan = _load_scan(scan_id)
    if not scan or not scan.get("results"):
        return JSONResponse({"error": "Scan not found or not completed"}, status_code=404)
    results = scan["results"]
    opsec = results.get("opsec_score")
    loop = asyncio.get_event_loop()
    report_path = await loop.run_in_executor(
        None,
        lambda: generate_html_report(scan["target"], scan["scan_type"], results, opsec),
    )
    scan["results"]["report_path"] = report_path
    return FileResponse(
        report_path,
        media_type="text/html",
        filename=os.path.basename(report_path),
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
    if not scan or not scan.get("results"):
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
    all_scans = _list_scans_from_disk()
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

@app.websocket("/ws/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: str):
    try:
        validate_scan_id(scan_id)
    except Exception:
        await websocket.close(code=1008)
        return
    import hmac as _hmac
    from web.security import API_KEY
    if API_KEY:
        token = websocket.query_params.get("api_key", "")
        if not token or not _hmac.compare_digest(token, API_KEY):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8080, reload=True)
