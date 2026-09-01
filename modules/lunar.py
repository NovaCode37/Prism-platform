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
    return os.getenv("LUNAR_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


class LunarLookup:
    """Domain exposure lookup against Lunar's free Domain Exposure API.

    Reports how often a domain shows up in infostealer logs and breach data over
    a rolling year, split by employees and clients, with a monthly timeline and
    breakdowns by malware family, operating system and affected service.

    Hudson Rock answers a similar question but returns a current snapshot; this
    endpoint is where the trend and the attribution detail come from.

    The endpoint needs no API key, but it is a third-party service, so the module
    is opt-in via LUNAR_ENABLED and returns `skipped` otherwise. Only aggregates
    are returned; the API exposes no credentials.
    """

    BASE_URL = "https://api.lunarcyber.com/domain-exposure"
    TIMEOUT = 25
    TOP_N = 8

    def _headers(self) -> Dict[str, str]:
        return {"Accept": "application/json", "User-Agent": "PRISM-OSINT"}

    def _proxies(self) -> Optional[Dict[str, str]]:
        proxy = os.getenv("MODULE_PROXY", "").strip()
        return {"http": proxy, "https": proxy} if proxy else None

    def _request(self, domain: str, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(
                self.BASE_URL,
                params={"domain": domain},
                headers=self._headers(),
                timeout=self.TIMEOUT,
                proxies=self._proxies(),
            )
        except requests.Timeout:
            annotate(result, ERROR, f"Lunar did not respond within {self.TIMEOUT}s")
            return None
        except Exception as e:
            annotate(result, ERROR, str(e)[:200])
            return None

        if r.status_code == 429:
            annotate(result, RATE_LIMITED, "Lunar rate limit reached")
            return None
        if r.status_code == 404:
            annotate(result, ERROR, "Domain not found in Lunar data")
            return None
        if r.status_code != 200:
            annotate(result, ERROR, f"Lunar returned {r.status_code}")
            return None

        try:
            return r.json()
        except ValueError:
            annotate(result, ERROR, "Lunar returned a non-JSON response")
            return None

    @staticmethod
    def _top(items: Any, key: str, count_key: str, limit: int) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []
        cleaned = [i for i in items if isinstance(i, dict) and i.get(key)]
        cleaned.sort(key=lambda i: i.get(count_key) or 0, reverse=True)
        return [{key: i[key], count_key: i.get(count_key)} for i in cleaned[:limit]]

    def search_domain(self, domain: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "target": domain,
            "target_type": "domain",
            "report_status": None,
            "period": None,
            "total_events": None,
            "infostealer_events": None,
            "data_breach_events": None,
            "employee_events": None,
            "client_events": None,
            "first_seen": None,
            "last_seen": None,
            "malware_families": [],
            "services": [],
            "countries": [],
            "monthly_timeline": [],
            "error": None,
        }

        if not is_enabled():
            return annotate(result, SKIPPED, "LUNAR_ENABLED is not set")
        if not domain:
            return annotate(result, ERROR, "No domain provided")

        data = self._request(domain, result)
        if data is None:
            return result

        status = data.get("status")
        result["report_status"] = status
        if status == "GENERATING_REPORT":
            return annotate(result, SKIPPED, "Lunar is still generating the report for this domain")
        if status == "NOT_AUTHORIZED":
            return annotate(result, SKIPPED, "Lunar does not serve a report for this domain")

        report = data.get("report")
        if not isinstance(report, dict):
            return annotate(result, ERROR, "Lunar returned no report body")

        period = report.get("period")
        if isinstance(period, dict):
            result["period"] = {"from": period.get("from"), "to": period.get("to")}

        summary = report.get("summary")
        if isinstance(summary, dict):
            result["total_events"] = summary.get("total_events")
            result["infostealer_events"] = summary.get("infostealer_events")
            result["data_breach_events"] = summary.get("data_breach_events")
            result["employee_events"] = summary.get("employee_events")
            result["client_events"] = summary.get("client_events")
            result["first_seen"] = summary.get("first_seen")
            result["last_seen"] = summary.get("last_seen")

        result["malware_families"] = self._top(
            report.get("malware_family_breakdown"), "family", "events", self.TOP_N
        )
        result["services"] = self._top(
            report.get("service_classification_breakdown"), "service", "events", self.TOP_N
        )
        result["countries"] = self._top(
            report.get("country_breakdown"), "country", "events", self.TOP_N
        )

        timeline = report.get("monthly_timeline")
        if isinstance(timeline, list):
            result["monthly_timeline"] = [
                {
                    "month": m.get("month"),
                    "total_events": m.get("total_events"),
                    "infostealer_events": m.get("infostealer_events"),
                    "data_breach_events": m.get("data_breach_events"),
                }
                for m in timeline[-12:]
                if isinstance(m, dict) and m.get("month")
            ]

        result["status"] = OK
        return result

    def print_result(self, result: Dict[str, Any]) -> None:
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}Domain exposure: {result.get('target')}{Colors.RESET}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}")

        if print_status_notice(result):
            return

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        period = result.get("period") or {}
        if period.get("from"):
            print(f"  Period            : {period.get('from')} to {period.get('to')}")
        print(f"  Total events      : {result.get('total_events')}")
        print(f"  Infostealer       : {result.get('infostealer_events')}")
        print(f"  Data breach       : {result.get('data_breach_events')}")
        print(f"  Employees / users : {result.get('employee_events')} / {result.get('client_events')}")

        families = result.get("malware_families") or []
        if families:
            print(f"\n{Colors.BOLD}Malware families:{Colors.RESET}")
            for entry in families:
                print(f"    {entry['events']:>6}x  {entry['family']}")

        services = result.get("services") or []
        if services:
            print(f"\n{Colors.BOLD}Affected services:{Colors.RESET}")
            for entry in services:
                print(f"    {entry['events']:>6}x  {entry['service']}")


def run_lunar_domain(domain: str) -> Dict[str, Any]:
    lookup = LunarLookup()
    result = lookup.search_domain(domain)
    lookup.print_result(result)
    return result
