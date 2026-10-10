from __future__ import annotations
from config import USER_AGENT

import re
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from modules import get_proxies
from modules.module_status import ERROR, OK, annotate


_ONION_RE = re.compile(r"https?://[a-z2-7]{16,56}\.onion[/\w\-\.]*", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_HIDDEN_INPUT_RE = re.compile(r"<input[^>]+type=[\"']hidden[\"'][^>]*>", re.IGNORECASE)
_NAME_RE = re.compile(r"name=[\"']([^\"']+)[\"']", re.IGNORECASE)
_VALUE_RE = re.compile(r"value=[\"']([^\"']+)[\"']", re.IGNORECASE)


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

    def _extract_hidden_token(self, html: str) -> Optional[Tuple[str, str]]:
        match = _HIDDEN_INPUT_RE.search(html or "")
        if not match:
            return None
        tag = match.group(0)
        name_m = _NAME_RE.search(tag)
        val_m = _VALUE_RE.search(tag)
        if name_m and val_m:
            return name_m.group(1), val_m.group(1)
        return None

    def _search_ahmia(
        self, query: str, session: Optional[requests.Session] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Search Ahmia for onion mirrors using a token from the home page.

        Returns (results, error_reason).
        """
        s = session or requests.Session()
        headers = {"User-Agent": USER_AGENT}
        proxies = get_proxies()
        try:
            r_home = s.get(
                "https://ahmia.fi/",
                timeout=self.timeout,
                proxies=proxies,
                headers=headers,
            )
            if r_home.status_code != 200:
                return [], f"Ahmia home page HTTP {r_home.status_code}"

            token_pair = self._extract_hidden_token(r_home.text)
            if not token_pair:
                return [], "Ahmia verification token not found on home page"

            token_name, token_value = token_pair
            params = {"q": query, token_name: token_value}

            r_search = s.get(
                "https://ahmia.fi/search/",
                params=params,
                timeout=self.timeout,
                proxies=proxies,
                headers=headers,
            )
            if r_search.status_code != 200:
                return [], f"Ahmia search HTTP {r_search.status_code}"

            html = r_search.text or ""
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
            return out[:25], None
        except Exception as e:
            return [], f"Ahmia request failed: {e}"

    def check(self, target: str) -> Dict[str, Any]:
        target = (target or "").strip()
        if not target:
            res: Dict[str, Any] = {"target": target, "total_found": 0, "results": [], "sources": {"ahmia": 0}}
            return annotate(res, ERROR, "empty target")

        tokens = self._tokens(target)
        session = requests.Session()
        ahmia, error = self._search_ahmia(target, session=session)

        base_res: Dict[str, Any] = {
            "target": target,
            "total_found": 0,
            "results": [],
            "sources": {
                "ahmia": len(ahmia),
            },
        }

        if error:
            return annotate(base_res, ERROR, error)

        seen: Set[str] = set()
        merged: List[Dict[str, Any]] = []
        for item in ahmia:
            url = item.get("url", "")
            if not url or url in seen:
                continue
            if not self._relevant(item, tokens):
                continue
            seen.add(url)
            item.pop("snippet", None)
            merged.append(item)

        base_res["total_found"] = len(merged)
        base_res["results"] = merged
        return annotate(base_res, OK)
