import requests
from typing import Dict, Any, List
from modules import get_proxies
from modules.module_status import ERROR, OK, RATE_LIMITED, annotate


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
        failures: List[str] = []
        rate_limited = 0
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for backend in self.BACKENDS:
            try:
                proxies = get_proxies()
                r = requests.get(
                    backend["url"],
                    params=backend["params"](query),
                    headers=headers,
                    timeout=15,
                    proxies=proxies,  
                )
                if r.status_code == 429:
                    failures.append(f'{backend["name"]}: rate limited')
                    rate_limited += 1
                    continue
                if r.status_code != 200:
                    failures.append(f'{backend["name"]}: HTTP {r.status_code}')
                    continue

                if backend["parse"] is None:
                    failures.append(f'{backend["name"]}: requires JavaScript rendering')
                    continue

                raw = backend["parse"](r.json())
                entries: List[Dict] = [backend["map"](i) for i in raw if i.get("title")][:limit]
                result["results"] = entries
                result["source"] = backend["name"]
                result["total"] = len(entries)
                reason = "; ".join(failures) if failures else None
                return annotate(result, OK, reason)

            except requests.exceptions.ConnectionError:
                failures.append(f'{backend["name"]}: unreachable (DNS/network error)')
            except Exception as e:
                failures.append(f'{backend["name"]}: {str(e)[:100]}')

        status = RATE_LIMITED if rate_limited and rate_limited == len(failures) else ERROR
        return annotate(
            result,
            status,
            f"Dark web search is unavailable: {'; '.join(failures)}. "
            "Most Tor search indexes require JavaScript or direct Tor access. "
            "Use Tor Browser with Ahmia (ahmia.fi) or DuckDuckGo onion for manual searches.",
        )
