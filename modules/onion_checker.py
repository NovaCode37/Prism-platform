from __future__ import annotations
from config import USER_AGENT

import re
from typing import Any, Dict, List, Set

import requests

from modules import get_proxies


_ONION_RE = re.compile(r"https?://[a-z2-7]{16,56}\.onion[/\w\-\.]*", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class OnionChecker:

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _tokens(self, target: str) -> Set[str]:
        t = (target or "").lower().strip()
        tokens: Set[str] = {t}
        if "." in t and " " not in t:
            parts = [p for p in t.split(".") if p]
            if len(parts) >= 2:
                tokens.add(parts[-2])
        for word in re.split(r"[\s@/]+", t):
            if word:
                tokens.add(word)
        return {tok for tok in tokens if len(tok) >= 3}

    def _relevant(self, item: Dict[str, Any], tokens: Set[str]) -> bool:
        if not tokens:
            return False
        hay = " ".join(
            str(item.get(k) or "") for k in ("url", "title", "description", "snippet")
        ).lower()
        return any(tok in hay for tok in tokens)

    def _search_ahmia(self, query: str) -> List[Dict[str, Any]]:
        try:
            r = requests.get(
                "https://ahmia.fi/search/",
                params={"q": query},
                timeout=self.timeout,
                proxies=get_proxies(),
                headers={"User-Agent": USER_AGENT},
            )
            if r.status_code != 200:
                return []
            html = r.text or ""
            out: List[Dict[str, Any]] = []
            seen: Set[str] = set()
            for block in re.split(r'<li[^>]*class="[^"]*result', html)[1:]:
                m = _ONION_RE.search(block)
                if not m:
                    continue
                url = m.group(0)
                if url in seen:
                    continue
                seen.add(url)
                text = _WS_RE.sub(" ", _TAG_RE.sub(" ", block)).strip()
                out.append({"source": "ahmia", "url": url, "snippet": text[:400] or None})
            return out[:25]
        except Exception:
            return []

    def _search_darksearch(self, query: str) -> List[Dict[str, Any]]:
        try:
            r = requests.get(
                "https://darksearch.io/api/search",
                params={"query": query, "page": 1},
                timeout=self.timeout,
                proxies=get_proxies(),
                headers={"User-Agent": USER_AGENT},
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
        target = (target or "").strip()
        if not target:
            return {"target": target, "error": "empty target"}

        tokens = self._tokens(target)
        ahmia = self._search_ahmia(target)
        darksearch = self._search_darksearch(target)

        seen: Set[str] = set()
        merged: List[Dict[str, Any]] = []
        for item in ahmia + darksearch:
            url = item.get("url", "")
            if not url or url in seen:
                continue
            if not self._relevant(item, tokens):
                continue
            seen.add(url)
            item.pop("snippet", None)
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
