"""Dark web / .onion mirror checker.

Searches public Tor search engines (Ahmia, DarkSearch) for any
.onion hidden services that mention the given domain or organization.
This does not connect to Tor directly — only public clearnet APIs.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

import requests


_ONION_RE = re.compile(r"https?://[a-z2-7]{16,56}\.onion[/\w\-\.]*", re.IGNORECASE)


class OnionChecker:
    """Lookup possible .onion mirrors / dark-web mentions of a target."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _search_ahmia(self, query: str) -> List[Dict[str, Any]]:
        """Ahmia exposes a clearnet search HTML page; parse onion links from it."""
        try:
            r = requests.get(
                "https://ahmia.fi/search/",
                params={"q": query},
                timeout=self.timeout,
                headers={"User-Agent": "PRISM-OSINT/2.1"},
            )
            if r.status_code != 200:
                return []
            urls = sorted(set(_ONION_RE.findall(r.text or "")))
            return [{"source": "ahmia", "url": u} for u in urls[:25]]
        except Exception:
            return []

    def _search_darksearch(self, query: str) -> List[Dict[str, Any]]:
        """DarkSearch.io public API (free, no key required)."""
        try:
            r = requests.get(
                "https://darksearch.io/api/search",
                params={"query": query, "page": 1},
                timeout=self.timeout,
                headers={"User-Agent": "PRISM-OSINT/2.1"},
            )
            if r.status_code != 200:
                return []
            data = r.json()
            items = data.get("data") or []
            out: List[Dict[str, Any]] = []
            for it in items[:25]:
                link = it.get("link") or ""
                if ".onion" not in link:
                    continue
                out.append({
                    "source": "darksearch",
                    "url": link,
                    "title": (it.get("title") or "").strip()[:200] or None,
                    "description": (it.get("description") or "").strip()[:300] or None,
                })
            return out
        except Exception:
            return []

    def check(self, target: str) -> Dict[str, Any]:
        """Aggregate results for a domain / organization.

        Returns dict with onion mirrors found and counts per source.
        """
        target = (target or "").strip()
        if not target:
            return {"target": target, "error": "empty target"}

        ahmia = self._search_ahmia(target)
        darksearch = self._search_darksearch(target)

        seen = set()
        merged: List[Dict[str, Any]] = []
        for item in ahmia + darksearch:
            url = item.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            merged.append(item)

        return {
            "target": target,
            "total_found": len(merged),
            "results": merged,
            "sources": {
                "ahmia": len(ahmia),
                "darksearch": len(darksearch),
            },
            "error": None,
        }
