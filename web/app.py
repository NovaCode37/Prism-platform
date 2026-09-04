"""
PRISM - Open Source Intelligence Platform
FastAPI backend with WebSocket scan engine.
"""

import asyncio
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from modules.cert_transparency import CertTransparency
from modules.darkweb_search import DarkWebSearch
from modules.gravatar import GravatarRecon
from modules.onion_checker import OnionChecker
from modules.rdap import RDAPLookup
from modules.shodan_lookup import ShodanLookup
from modules.virustotal_lookup import VirusTotalLookup
from modules.abuseipdb_lookup import AbuseIPDBLookup
from modules.github_recon import GitHubRecon
from modules.breach_check import BreachCheck
from modules.whois_lookup import WhoisLookup
from modules.dns_lookup import DNSLookup
from modules.geoip import GeoIP
from modules.wayback import Wayback
from modules.report_generator import generate_html_report, generate_pdf_report
from modules.graph_export import to_graphml, to_gexf
from web.security import (
    validate_api_key,
    validate_public_target,
    client_ip,
    check_rate_limit,
    check_scan_quota,
    record_scan,
    get_usage,
)
from web.watchlist import (
    create_watchlist,
    list_watchlists,
    get_watchlist,
    delete_watchlist,
    set_paused,
    get_watchlist_status,
    due_watchlists,
    record_run,
    mark_error,
    WATCHLIST_SCHEDULER,
)

# Import config
from config import (
    ALLOW_ANON_API,
    API_KEYS,
    PRISM_UI_API_KEY,
    PRISM_FRONTEND_DIR,
    PRISM_BASE_PATH,
    ALLOWED_ORIGINS,
    DISABLE_DOCS,
    MAX_STORED_SCANS,
)

# LLM imports
from web.llm import llm_providers, _llm_complete

# Initialize FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if WATCHLIST_SCHEDULER:
        import asyncio
        asyncio.create_task(run_watchlist_scheduler())
    yield
    # Shutdown

app = FastAPI(
    title="PRISM OSINT API",
    description="Self-hosted OSINT platform API",
    version="2.8.0",
    lifespan=lifespan,
)

# CORS configuration
origins = []
if ALLOWED_ORIGINS == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Disable docs if configured
if DISABLE_DOCS:
    app.docs_url = None
    app.redoc_url = None

# Static files for frontend
frontend_dir = PRISM_FRONTEND_DIR or os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "out")
if os.path.exists(frontend_dir):
    app.mount("/_next", StaticFiles(directory=os.path.join(frontend_dir, "_next")), name="_next")
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "static")), name="static")


# Scan state management
class ScanState:
    def __init__(self):
        self.scans: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def create(self, target: str, scan_type: str, principal: str) -> str:
        scan_id = str(uuid.uuid4())
        async with self.lock:
            self.scans[scan_id] = {
                "id": scan_id,
                "target": target,
                "scan_type": scan_type,
                "principal": principal,
                "status": "pending",
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "results": {},
                "log": [],
                "module_status": {},
            }
            # Clean up old scans
            self._cleanup()
        return scan_id

    async def update(self, scan_id: str, data: Dict[str, Any]) -> None:
        async with self.lock:
            if scan_id in self.scans:
                self.scans[scan_id].update(data)

    async def add_log(self, scan_id: str, message: str) -> None:
        async with self.lock:
            if scan_id in self.scans:
                self.scans[scan_id]["log"].append(message)

    async def get(self, scan_id: str, principal: str) -> Optional[Dict[str, Any]]:
        async with self.lock:
            scan = self.scans.get(scan_id)
            if scan and scan.get("principal") == principal:
                # Return a copy without sensitive data
                return {k: v for k, v in scan.items() if k != "principal"}
            return None

    async def list_scans(self, principal: str, limit: int = 20) -> List[Dict[str, Any]]:
        async with self.lock:
            scans = [v for v in self.scans.values() if v.get("principal") == principal]
            scans.sort(key=lambda x: x.get("started_at", ""), reverse=True)
            return [{k: v for k, v in s.items() if k != "principal"} for s in scans[:limit]]

    def _cleanup(self):
        """Remove old scans beyond MAX_STORED_SCANS."""
        if len(self.scans) > MAX_STORED_SCANS * 2:
            # Sort by started_at and remove oldest
            items = sorted(
                [(k, v) for k, v in self.scans.items()],
                key=lambda x: x[1].get("started_at", ""),
                reverse=True,
            )
            keep = {k: v for k, v in items[:MAX_STORED_SCANS]}
            self.scans.clear()
            self.scans.update(keep)


scan_state = ScanState()


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}

    async def connect(self, scan_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[scan_id] = websocket

    def disconnect(self, scan_id: str):
        if scan_id in self.connections:
            del self.connections[scan_id]

    async def send(self, scan_id: str, message: Any):
        if scan_id in self.connections:
            try:
                await self.connections[scan_id].send_json(message)
            except Exception:
                self.disconnect(scan_id)


manager = ConnectionManager()


# Helper functions
def normalize_target(target: str) -> str:
    """Normalize a target string."""
    if not target:
        return target
    target = target.strip()
    if target.startswith(("http://", "https://")):
        target = target.split("://", 1)[1]
    target = target.rstrip("/")
    return target


def detect_scan_type(target: str) -> str:
    """Detect the type of target."""
    target = target.strip()
    import re

    # Email
    if "@" in target and "." in target.split("@")[-1]:
        return "email"

    # IPv4
    if re.match(r"^(\d{1,3}\.){3}\d{1,3}$", target):
        return "ip"

    # IPv6 (simplified)
    if re.match(r"^[0-9a-fA-F:]+:[0-9a-fA-F:]+$", target):
        return "ip"

    # Phone (simplified)
    if re.match(r"^\+?[\d][\d\s().-]{6,}$", target):
        return "phone"

    # Username
    if target.startswith("@"):
        return "username"

    # Domain
    if "." in target and " " not in target:
        return "domain"

    return "username"


async def run_scan_task(scan_id: str, target: str, scan_type: str, principal: str):
    """Background task to run the scan."""
    try:
        await scan_state.update(scan_id, {"status": "running"})

        # Start with the common modules
        all_modules: Dict[str, Any] = {}

        # Type-specific modules
        if scan_type == "domain":
            all_modules.update({
                "whois": WhoisLookup,
                "dns": DNSLookup,
                "cert_transparency": CertTransparency,
                "rdap": RDAPLookup,
                "wayback": Wayback,
            })
            # GeoIP for domain too
            all_modules["geoip"] = GeoIP
            # Conditionally add keyed modules
            if os.getenv("VIRUSTOTAL_API_KEY"):
                all_modules["virustotal"] = VirusTotalLookup
            if os.getenv("SHODAN_API_KEY"):
                all_modules["shodan"] = ShodanLookup
            if os.getenv("ABUSEIPDB_API_KEY"):
                all_modules["abuseipdb"] = AbuseIPDBLookup

        elif scan_type == "email":
            all_modules.update({
                "gravatar": GravatarRecon,
                "breach": BreachCheck,
            })

        elif scan_type == "username":
            all_modules.update({
                "github": GitHubRecon,
            })

        elif scan_type == "ip":
            all_modules["geoip"] = GeoIP
            if os.getenv("VIRUSTOTAL_API_KEY"):
                all_modules["virustotal"] = VirusTotalLookup
            if os.getenv("SHODAN_API_KEY"):
                all_modules["shodan"] = ShodanLookup
            if os.getenv("ABUSEIPDB_API_KEY"):
                all_modules["abuseipdb"] = AbuseIPDBLookup

        elif scan_type == "phone":
            pass  # No modules yet

        # Dark web search for all types (if enabled)
        # Only run for domain/username/email
        if scan_type in ("domain", "username", "email"):
            all_modules["darkweb"] = DarkWebSearch

        # Onion checker for domain/email/username
        if scan_type in ("domain", "email", "username"):
            all_modules["onion"] = OnionChecker

        total_modules = len(all_modules)
        completed = 0

        # Run each module
        results: Dict[str, Any] = {}
        module_status: Dict[str, str] = {}

        for name, handler in all_modules.items():
            await scan_state.add_log(scan_id, f"Running module: {name}")
            await manager.send(scan_id, {"type": "module_start", "module": name})

            try:
                instance = handler()
                if hasattr(instance, "lookup"):
                    result = instance.lookup(target)
                elif hasattr(instance, "search"):
                    result = instance.search(target)
                elif hasattr(instance, "check"):
                    result = instance.check(target)
                elif hasattr(instance, "run"):
                    result = instance.run(target)
                else:
                    result = {"error": f"Module {name} has no main method"}

                results[name] = result

                # Determine status
                if isinstance(result, dict):
                    status = result.get("status")
                    if status not in ("ok", "skipped", "rate_limited", "error"):
                        if result.get("error"):
                            status = "error"
                        else:
                            status = "ok"
                else:
                    status = "ok"

                module_status[name] = status

                # Update scan state
                await scan_state.update(scan_id, {
                    "results": results,
                    "module_status": module_status,
                })

                # Send update
                await manager.send(scan_id, {
                    "type": "module_complete",
                    "module": name,
                    "status": status,
                    "progress": {"completed": completed + 1, "total": total_modules},
                })

            except Exception as e:
                results[name] = {"error": str(e)}
                module_status[name] = "error"
                await scan_state.add_log(scan_id, f"Error in {name}: {e}")
                await manager.send(scan_id, {
                    "type": "module_error",
                    "module": name,
                    "error": str(e),
                })

            completed += 1

        # Run OPSEC scoring
        try:
            from modules.opsec_scorer import score_results
            opsec_result = score_results(results)
            results["opsec"] = opsec_result
        except Exception as e:
            results["opsec"] = {"error": str(e)}
            await scan_state.add_log(scan_id, f"Error in OPSEC scoring: {e}")

        # Update final state
        await scan_state.update(scan_id, {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "results": results,
            "module_status": module_status,
        })

        await manager.send(scan_id, {"type": "complete", "results": results})

        # Also update watchlist if this is a domain scan
        if scan_type == "domain":
            # This is a scan, not a watchlist run, but we might want to record it
            pass

    except Exception as e:
        await scan_state.add_log(scan_id, f"Fatal error: {e}")
        await scan_state.update(scan_id, {"status": "error"})
        await manager.send(scan_id, {"type": "error", "error": str(e)})


# Watchlist scheduler
async def run_watchlist_scheduler():
    """Background task to run watchlist scans."""
    while True:
        try:
            due = due_watchlists()
            for entry in due:
                scan_id = await scan_state.create(entry["target"], "domain", f"watchlist-{entry['owner']}")
                # Run the scan
                asyncio.create_task(run_scan_task(scan_id, entry["target"], "domain", f"watchlist-{entry['owner']}"))
                # Record the run in watchlist
                # We need to wait for completion, but this is simplified
                record_run(entry["id"], {})
        except Exception as e:
            print(f"Watchlist scheduler error: {e}")
        await asyncio.sleep(60)


# API Routes
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/api/scan")
async def start_scan(request: Request):
    """Start a new scan."""
    # Get principal from API key
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # Get request body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    target = body.get("target", "").strip()
    scan_type = body.get("type") or detect_scan_type(target)

    if not target:
        raise HTTPException(status_code=400, detail="Target is required")

    # Normalize target
    target = normalize_target(target)

    # Validate target is public (if configured)
    try:
        validate_public_target(target, scan_type)
    except HTTPException as e:
        raise e

    # Check scan quota
    try:
        check_scan_quota(principal)
    except HTTPException as e:
        raise e

    # Create scan
    scan_id = await scan_state.create(target, scan_type, principal)

    # Record the scan for quota
    record_scan(principal)

    # Start the scan in the background
    asyncio.create_task(run_scan_task(scan_id, target, scan_type, principal))

    return {"scan_id": scan_id}


@app.websocket("/ws/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: str):
    """WebSocket endpoint for real-time scan updates."""
    # Check API key via query param
    api_key = websocket.query_params.get("api_key")
    if api_key:
        # Verify the key
        if not API_KEYS or api_key not in API_KEYS.split(","):
            await websocket.close(code=1008, reason="Invalid API key")
            return
        principal = api_key
    else:
        principal = "anonymous"

    # Check if the scan exists and belongs to this principal
    scan = await scan_state.get(scan_id, principal)
    if not scan:
        await websocket.close(code=1000, reason="Scan not found")
        return

    await manager.connect(scan_id, websocket)

    try:
        # Send initial state
        await websocket.send_json({"type": "init", "scan": scan})

        # Keep the connection alive and forward updates
        while True:
            # Ping to keep connection alive
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(30)

    except WebSocketDisconnect:
        manager.disconnect(scan_id)
    except Exception as e:
        manager.disconnect(scan_id)


@app.get("/api/scans")
async def list_scans(request: Request):
    """List scans for the authenticated principal."""
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    limit = request.query_params.get("limit", 20)
    try:
        limit = int(limit)
    except ValueError:
        limit = 20

    scans = await scan_state.list_scans(principal, limit)
    return {"scans": scans}


@app.get("/api/scan/{scan_id}")
async def get_scan(request: Request, scan_id: str):
    """Get scan details."""
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    scan = await scan_state.get(scan_id, principal)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return {"scan": scan}


@app.get("/api/scan/{scan_id}/report.{format}")
async def get_report(request: Request, scan_id: str, format: str):
    """Get a report for a scan."""
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    scan = await scan_state.get(scan_id, principal)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    results = scan.get("results", {})
    target = scan.get("target", "unknown")
    scan_type = scan.get("scan_type", "unknown")

    if format == "html":
        try:
            html = generate_html_report(target, scan_type, results)
            return HTMLResponse(content=html, headers={"Content-Type": "text/html"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate HTML report: {e}")

    elif format == "pdf":
        try:
            pdf = generate_pdf_report(target, scan_type, results)
            return FileResponse(
                pdf, media_type="application/pdf",
                filename=f"{target}_report.pdf"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {e}")

    elif format == "json":
        return JSONResponse(results)

    elif format == "graphml":
        try:
            graph = results.get("graph", {})
            if not graph:
                raise HTTPException(status_code=400, detail="No graph data available")
            graphml = to_graphml(graph)
            return HTMLResponse(content=graphml, headers={"Content-Type": "application/xml"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate GraphML: {e}")

    elif format == "gexf":
        try:
            graph = results.get("graph", {})
            if not graph:
                raise HTTPException(status_code=400, detail="No graph data available")
            gexf = to_gexf(graph)
            return HTMLResponse(content=gexf, headers={"Content-Type": "application/xml"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate GEXF: {e}")

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


# Watchlist API endpoints
@app.post("/api/watchlist")
async def create_watchlist_endpoint(request: Request):
    """Create a new watchlist."""
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    body = await request.json()
    target = body.get("target", "").strip()
    scan_type = body.get("type") or detect_scan_type(target)

    if not target:
        raise HTTPException(status_code=400, detail="Target is required")

    if scan_type != "domain":
        raise HTTPException(status_code=400, detail="Only domain watchlists are supported")

    modules = body.get("modules", [])
    interval_hours = body.get("interval_hours", 24)

    entry = create_watchlist(principal, target, scan_type, modules, interval_hours)
    return {"watchlist": entry}


@app.get("/api/watchlist")
async def list_watchlists_endpoint(request: Request):
    """List watchlists for the authenticated principal."""
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    entries = list_watchlists(principal)
    return {"watchlists": entries}


@app.get("/api/watchlist/{watchlist_id}")
async def get_watchlist_endpoint(request: Request, watchlist_id: str):
    """Get a watchlist entry."""
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    entry = get_watchlist(watchlist_id)
    if not entry or entry.get("owner") != principal:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    # Remove owner from response
    entry = {k: v for k, v in entry.items() if k != "owner"}
    return {"watchlist": entry}


@app.delete("/api/watchlist/{watchlist_id}")
async def delete_watchlist_endpoint(request: Request, watchlist_id: str):
    """Delete a watchlist."""
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    deleted = delete_watchlist(watchlist_id, principal)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    return {"success": True}


@app.patch("/api/watchlist/{watchlist_id}/pause")
async def pause_watchlist_endpoint(request: Request, watchlist_id: str):
    """Pause or unpause a watchlist."""
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    body = await request.json()
    paused = body.get("paused", True)

    entry = set_paused(watchlist_id, principal, paused)
    if entry is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    return {"watchlist": entry}


@app.get("/api/watchlist/{watchlist_id}/status")
async def watchlist_status_endpoint(request: Request, watchlist_id: str):
    """Get the current status of a watchlist."""
    principal = validate_api_key(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    status = get_watchlist_status(watchlist_id, principal)
    if status is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    return {"status": status}


# Frontend route
@app.get("/")
async def serve_frontend(request: Request):
    """Serve the frontend."""
    # Check if we have frontend files
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    # Check if we're in development mode
    if os.getenv("NEXT_PUBLIC_API_URL"):
        return HTMLResponse("""
            <!DOCTYPE html>
            <html>
                <head><title>PRISM OSINT</title></head>
                <body>
                    <h1>PRISM OSINT</h1>
                    <p>Frontend not found. Please build the frontend or set PRISM_FRONTEND_DIR.</p>
                    <p>API is running at <a href="/docs">/docs</a></p>
                </body>
            </html>
        """)

    raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        no_proxy_headers=True,
    )