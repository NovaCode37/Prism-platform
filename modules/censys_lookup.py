from __future__ import annotations

import os
from typing import Any, Dict

import requests

from modules.module_status import annotate, OK, SKIPPED, RATE_LIMITED, ERROR
from modules import get_proxies

CENSYS_PAT = os.getenv("CENSYS_PAT", "") or os.getenv("CENSYS_API_KEY", "")
CENSYS_ORG_ID = os.getenv("CENSYS_ORG_ID", "")
CENSYS_BASE = "https://api.platform.censys.io/v3"


class CensysLookup:

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.pat = CENSYS_PAT
        self.org_id = CENSYS_ORG_ID

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
            "User-Agent": "PRISM-OSINT/2.4",
        }

    def _params(self) -> Dict[str, str]:
        return {"organization_id": self.org_id} if self.org_id else {}

    def _err_no_key(self) -> Dict[str, Any]:
        return annotate(
            {"results": [], "total": 0},
            SKIPPED,
            "No API key configured (CENSYS_PAT)",
        )

    def search_ip(self, ip: str) -> Dict[str, Any]:
        if not self.pat:
            return self._err_no_key()
        try:
            proxies = get_proxies()
            r = requests.get(
                f"{CENSYS_BASE}/global/asset/host/{ip}",
                headers=self._headers(),
                params=self._params(),
                timeout=self.timeout,
                proxies=proxies,  
            )
            if r.status_code in (401, 403):
                return annotate({"results": [], "total": 0}, ERROR, "Invalid Censys token or organization ID")
            if r.status_code == 429:
                return annotate({"results": [], "total": 0}, RATE_LIMITED, "Censys API rate limit reached")
            if r.status_code == 404:
                return annotate({"results": [], "total": 0, "ip": ip}, OK)
            if r.status_code != 200:
                return annotate({"results": [], "total": 0}, ERROR, f"Censys HTTP {r.status_code}")

            resource = ((r.json().get("result") or {}).get("resource")) or {}
            services = resource.get("services") or []
            asys = resource.get("autonomous_system") or {}
            loc = resource.get("location") or {}
            return {
                "error": None,
                "status": OK,
                "ip": ip,
                "asn": asys.get("asn"),
                "as_name": asys.get("name") or asys.get("description"),
                "country": loc.get("country"),
                "city": loc.get("city"),
                "open_ports": sorted({s.get("port") for s in services if s.get("port")}),
                "services": [
                    {
                        "port": s.get("port"),
                        "service": s.get("protocol") or s.get("service_name"),
                        "transport": s.get("transport_protocol"),
                        "software": None,
                    }
                    for s in services[:30]
                ],
                "total": len(services),
            }
        except Exception as e:
            return annotate({"results": [], "total": 0}, ERROR, str(e)[:200])

    def search_domain(self, domain: str) -> Dict[str, Any]:
        if not self.pat:
            return self._err_no_key()
        return annotate(
            {"results": [], "total": 0, "domain": domain, "subdomains": [], "certificates": []},
            SKIPPED,
            "Certificate search is not available on the Censys Platform API; subdomains come from crt.sh",
        )
