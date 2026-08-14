import os
import sys
from typing import Any, Dict, List, Optional

import requests

sys.path.append("..")

from config import Colors
from modules.module_status import (
    annotate,
    print_status_notice,
    OK,
    SKIPPED,
    RATE_LIMITED,
    ERROR,
)


def is_enabled() -> bool:
    return os.getenv("HUDSONROCK_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


class HudsonRockLookup:
    """Infostealer exposure lookup against Hudson Rock's free OSINT endpoints.

    Reports how many machines carrying a target's credentials were infected by
    infostealer malware. This is distinct from breach data: a breach dump comes
    from a compromised service, while these records come from infected endpoints.

    The endpoints need no API key, but they are a third-party service, so the
    module is opt-in via HUDSONROCK_ENABLED and returns `skipped` otherwise.
    Only aggregate statistics are returned by the free tier; no credentials.
    """

    BASE_URL = "https://cavalier.hudsonrock.com/api/json/v2/osint-tools"
    TIMEOUT = 25

    def _headers(self) -> Dict[str, str]:
        return {"Accept": "application/json", "User-Agent": "PRISM-OSINT"}

    def _proxies(self) -> Optional[Dict[str, str]]:
        proxy = os.getenv("MODULE_PROXY", "").strip()
        return {"http": proxy, "https": proxy} if proxy else None

    def _request(self, path: str, params: Dict[str, str], result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(
                f"{self.BASE_URL}/{path}",
                params=params,
                headers=self._headers(),
                timeout=self.TIMEOUT,
                proxies=self._proxies(),
            )
        except requests.Timeout:
            annotate(result, ERROR, f"Hudson Rock did not respond within {self.TIMEOUT}s")
            return None
        except Exception as e:
            annotate(result, ERROR, str(e)[:200])
            return None

        if r.status_code == 429:
            annotate(result, RATE_LIMITED, "Hudson Rock rate limit reached")
            return None
        if r.status_code == 404:
            annotate(result, ERROR, "Target not found in Hudson Rock data")
            return None
        if r.status_code != 200:
            annotate(result, ERROR, f"Hudson Rock returned {r.status_code}")
            return None

        try:
            return r.json()
        except ValueError:
            annotate(result, ERROR, "Hudson Rock returned a non-JSON response")
            return None

    @staticmethod
    def _top(items: Any, key: str, limit: int = 8) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []
        cleaned = [i for i in items if isinstance(i, dict) and i.get(key)]
        cleaned.sort(key=lambda i: i.get("occurrence") or 0, reverse=True)
        return [{key: i[key], "occurrence": i.get("occurrence")} for i in cleaned[:limit]]

    @staticmethod
    def _password_stats(block: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(block, dict) or not block.get("has_stats"):
            return None
        stats = {"total": block.get("totalPass")}
        for level in ("too_weak", "weak", "medium", "strong"):
            entry = block.get(level)
            if isinstance(entry, dict):
                stats[level] = entry.get("perc")
        return stats

    def search_domain(self, domain: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "target": domain,
            "target_type": "domain",
            "total_compromised": None,
            "employees": None,
            "users": None,
            "third_parties": None,
            "employee_urls": [],
            "stealer_families": {},
            "employee_password_stats": None,
            "user_password_stats": None,
            "error": None,
        }

        if not is_enabled():
            return annotate(result, SKIPPED, "HUDSONROCK_ENABLED is not set")
        if not domain:
            return annotate(result, ERROR, "No domain provided")

        data = self._request("search-by-domain", {"domain": domain}, result)
        if data is None:
            return result

        result["total_compromised"] = data.get("total")
        result["employees"] = data.get("employees")
        result["users"] = data.get("users")
        result["third_parties"] = data.get("third_parties")
        result["employee_urls"] = self._top((data.get("data") or {}).get("employees_urls"), "url")
        result["employee_password_stats"] = self._password_stats(data.get("employeePasswords"))
        result["user_password_stats"] = self._password_stats(data.get("userPasswords"))

        families = data.get("stealerFamilies")
        if isinstance(families, dict):
            ranked = sorted(
                ((k, v) for k, v in families.items() if k != "total" and isinstance(v, int)),
                key=lambda kv: kv[1],
                reverse=True,
            )
            result["stealer_families"] = dict(ranked[:6])

        result["status"] = OK
        return result

    def _search_identity(self, kind: str, value: str, path: str, param: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "target": value,
            "target_type": kind,
            "stealers_found": None,
            "compromised": False,
            "corporate_services": None,
            "user_services": None,
            "error": None,
        }

        if not is_enabled():
            return annotate(result, SKIPPED, "HUDSONROCK_ENABLED is not set")
        if not value:
            return annotate(result, ERROR, f"No {kind} provided")

        data = self._request(path, {param: value}, result)
        if data is None:
            return result

        stealers = data.get("stealers")
        count = len(stealers) if isinstance(stealers, list) else data.get("total")
        result["stealers_found"] = count
        result["compromised"] = bool(count)
        result["corporate_services"] = data.get("total_corporate_services")
        result["user_services"] = data.get("total_user_services")
        result["status"] = OK
        return result

    def search_email(self, email: str) -> Dict[str, Any]:
        return self._search_identity("email", (email or "").strip().lower(), "search-by-email", "email")

    def search_username(self, username: str) -> Dict[str, Any]:
        return self._search_identity("username", (username or "").lstrip("@").strip(), "search-by-username", "username")

    def print_result(self, result: Dict[str, Any]) -> None:
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}Infostealer exposure: {result.get('target')}{Colors.RESET}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}")

        if print_status_notice(result):
            return

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        if result.get("target_type") == "domain":
            print(f"  Total compromised : {result.get('total_compromised')}")
            print(f"  Employees         : {result.get('employees')}")
            print(f"  Users             : {result.get('users')}")
            for entry in result.get("employee_urls") or []:
                print(f"    {entry['occurrence']:>5}x  {entry['url']}")
        else:
            found = result.get("stealers_found")
            colour = Colors.RED if result.get("compromised") else Colors.GREEN
            print(f"  Records found     : {colour}{found}{Colors.RESET}")


def run_hudsonrock_domain(domain: str) -> Dict[str, Any]:
    lookup = HudsonRockLookup()
    result = lookup.search_domain(domain)
    lookup.print_result(result)
    return result


def run_hudsonrock_email(email: str) -> Dict[str, Any]:
    lookup = HudsonRockLookup()
    result = lookup.search_email(email)
    lookup.print_result(result)
    return result


def run_hudsonrock_username(username: str) -> Dict[str, Any]:
    lookup = HudsonRockLookup()
    result = lookup.search_username(username)
    lookup.print_result(result)
    return result
