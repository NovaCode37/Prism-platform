"""Censys.io integration.

Uses Censys Search API v2 (https://search.censys.io/api) for:
  - Host info & open ports/services for IPs
  - Certificate / subdomain discovery for domains

Requires CENSYS_API_ID and CENSYS_API_SECRET environment variables.
Free tier: 250 queries/month.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

CENSYS_API_ID = os.getenv("CENSYS_API_ID", "")
CENSYS_API_SECRET = os.getenv("CENSYS_API_SECRET", "")
CENSYS_BASE = "https://search.censys.io/api"


class CensysLookup:
    """Thin wrapper over the public Censys Search API v2."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.api_id = CENSYS_API_ID
        self.api_secret = CENSYS_API_SECRET

    def _auth(self) -> tuple[str, str] | None:
        if not self.api_id or not self.api_secret:
            return None
        return (self.api_id, self.api_secret)

    def _err_no_key(self) -> Dict[str, Any]:
        return {
            "error": "CENSYS_API_ID and CENSYS_API_SECRET not set in .env",
            "results": [],
            "total": 0,
        }

    def search_ip(self, ip: str) -> Dict[str, Any]:
        """Fetch host details (services, ports, software, ASN) for an IP."""
        auth = self._auth()
        if auth is None:
            return self._err_no_key()
        try:
            r = requests.get(
                f"{CENSYS_BASE}/v2/hosts/{ip}",
                auth=auth,
                timeout=self.timeout,
                headers={"User-Agent": "PRISM-OSINT/2.1"},
            )
            if r.status_code == 401:
                return {"error": "Invalid Censys credentials", "results": [], "total": 0}
            if r.status_code == 404:
                return {"error": None, "results": [], "total": 0, "ip": ip}
            if r.status_code != 200:
                return {"error": f"Censys HTTP {r.status_code}", "results": [], "total": 0}
            data = r.json().get("result", {})
            services = data.get("services") or []
            return {
                "error": None,
                "ip": ip,
                "asn": (data.get("autonomous_system") or {}).get("asn"),
                "as_name": (data.get("autonomous_system") or {}).get("name"),
                "country": (data.get("location") or {}).get("country"),
                "city": (data.get("location") or {}).get("city"),
                "open_ports": sorted({s.get("port") for s in services if s.get("port")}),
                "services": [
                    {
                        "port": s.get("port"),
                        "service": s.get("service_name"),
                        "transport": s.get("transport_protocol"),
                        "software": (s.get("software") or [{}])[0].get("product")
                        if s.get("software") else None,
                    }
                    for s in services[:30]
                ],
                "total": len(services),
            }
        except Exception as e:
            return {"error": str(e)[:200], "results": [], "total": 0}

    def search_domain(self, domain: str) -> Dict[str, Any]:
        """Find certificates issued for a domain and extract subdomains."""
        auth = self._auth()
        if auth is None:
            return self._err_no_key()
        try:
            r = requests.post(
                f"{CENSYS_BASE}/v2/certificates/search",
                auth=auth,
                timeout=self.timeout,
                headers={"User-Agent": "PRISM-OSINT/2.1", "Content-Type": "application/json"},
                json={
                    "q": f"names: {domain}",
                    "per_page": 50,
                },
            )
            if r.status_code == 401:
                return {"error": "Invalid Censys credentials", "results": [], "total": 0}
            if r.status_code == 404:
                # Falls back gracefully if cert API tier disabled
                return {"error": None, "results": [], "total": 0, "domain": domain}
            if r.status_code != 200:
                return {"error": f"Censys HTTP {r.status_code}", "results": [], "total": 0}

            data = r.json().get("result", {})
            hits = data.get("hits") or []
            subdomains: set[str] = set()
            certs: List[Dict[str, Any]] = []
            for h in hits[:50]:
                names = h.get("names") or []
                for n in names:
                    n = (n or "").lower().lstrip("*.")
                    if n.endswith(domain.lower()):
                        subdomains.add(n)
                certs.append({
                    "fingerprint": h.get("fingerprint_sha256", "")[:24],
                    "issuer": (h.get("parsed") or {}).get("issuer_dn", "")[:200],
                    "names": names[:8],
                })
            return {
                "error": None,
                "domain": domain,
                "subdomains": sorted(subdomains),
                "certificates": certs[:25],
                "total": data.get("total", len(hits)),
            }
        except Exception as e:
            return {"error": str(e)[:200], "results": [], "total": 0}
