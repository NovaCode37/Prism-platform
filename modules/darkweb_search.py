import requests
from typing import Dict, Any, List

class DarkWebSearch:
    BACKENDS = [
        {
            "name": "Tor.link",
            "url": "https://tor.link/api/search",
            "params": lambda q: {"q": q},
            "parse": lambda d: d.get("results", []),
            "map": lambda i: {"title": i.get("title"), "url": i.get("url"), "description": i.get("description"), "onion": i.get("onion")},
        },
        {
            "name": "Ahmia.fi",
            "url": "https://ahmia.fi/search/",
            "params": lambda q: {"q": q},
            "parse": None,
            "map": None,
        },
    ]

    def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        result = {
            "query": query,
            "results": [],
            "source": "",
            "error": None,
        }
        last_error = ""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for backend in self.BACKENDS:
            try:
                r = requests.get(
                    backend["url"],
                    params=backend["params"](query),
                    headers=headers,
                    timeout=15,
                )
                if r.status_code == 429:
                    last_error = f'{backend["name"]}: rate limited'
                    continue
                if r.status_code != 200:
                    last_error = f'{backend["name"]}: HTTP {r.status_code}'
                    continue

                if backend["parse"] is not None:
                    raw = backend["parse"](r.json())
                    entries: List[Dict] = [backend["map"](i) for i in raw[:limit] if i.get("title")]
                    if entries:
                        result["results"] = entries
                        result["source"] = backend["name"]
                        result["total"] = len(entries)
                        return result
                    last_error = f'{backend["name"]}: no results'
                else:
                    last_error = f'{backend["name"]}: requires JavaScript rendering'

            except requests.exceptions.ConnectionError:
                last_error = f'{backend["name"]}: unreachable (DNS/network error)'
            except Exception as e:
                last_error = f'{backend["name"]}: {str(e)[:100]}'

        result["error"] = (
            f"Dark web search is unavailable: {last_error}. "
            "Most Tor search indexes require JavaScript or direct Tor access. "
            "Use Tor Browser with Ahmia (ahmia.fi) or DuckDuckGo onion for manual searches."
        )
        return result
