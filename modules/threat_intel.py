import requests
from typing import Dict, Any, Optional
import sys
sys.path.append('..')
from config import Colors, VIRUSTOTAL_API_KEY, ABUSEIPDB_API_KEY

class VirusTotal:

    BASE_URL = "https://www.virustotal.com/api/v3"

    def __init__(self):
        self.api_key = VIRUSTOTAL_API_KEY
        self.headers = {"x-apikey": self.api_key} if self.api_key else {}

    def _get(self, endpoint: str) -> Dict:
        if not self.api_key:
            return {"error": "VIRUSTOTAL_API_KEY not set in .env"}
        try:
            r = requests.get(
                f"{self.BASE_URL}{endpoint}",
                headers=self.headers,
                timeout=15,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return {"error": "Not found in VirusTotal database"}
            return {"error": f"API returned {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    def check_ip(self, ip: str) -> Dict[str, Any]:
        raw = self._get(f"/ip_addresses/{ip}")
        if "error" in raw:
            return {"query": ip, "type": "ip", **raw}

        attrs = raw.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})

        return {
            "query": ip,
            "type": "ip",
            "malicious": stats.get("malicious", 0),
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "country": attrs.get("country"),
            "asn": attrs.get("asn"),
            "as_owner": attrs.get("as_owner"),
            "reputation": attrs.get("reputation", 0),
            "tags": attrs.get("tags", []),
            "error": None,
        }

    def check_domain(self, domain: str) -> Dict[str, Any]:
        raw = self._get(f"/domains/{domain}")
        if "error" in raw:
            return {"query": domain, "type": "domain", **raw}

        attrs = raw.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})

        return {
            "query": domain,
            "type": "domain",
            "malicious": stats.get("malicious", 0),
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "reputation": attrs.get("reputation", 0),
            "categories": attrs.get("categories", {}),
            "creation_date": attrs.get("creation_date"),
            "tags": attrs.get("tags", []),
            "error": None,
        }

    def check_url(self, url: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"query": url, "type": "url", "error": "VIRUSTOTAL_API_KEY not set in .env"}
        try:
            submit_r = requests.post(
                f"{self.BASE_URL}/urls",
                headers=self.headers,
                data={"url": url},
                timeout=15,
            )
            if submit_r.status_code not in (200, 201):
                return {"query": url, "type": "url", "error": f"Submit failed: {submit_r.status_code}"}

            analysis_id = submit_r.json().get("data", {}).get("id", "")
            if not analysis_id:
                return {"query": url, "type": "url", "error": "No analysis ID returned"}

            result_r = requests.get(
                f"{self.BASE_URL}/analyses/{analysis_id}",
                headers=self.headers,
                timeout=15,
            )
            if result_r.status_code != 200:
                return {"query": url, "type": "url", "error": f"Results fetch failed: {result_r.status_code}"}

            attrs = result_r.json().get("data", {}).get("attributes", {})
            stats = attrs.get("stats", {})

            return {
                "query": url,
                "type": "url",
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "harmless": stats.get("harmless", 0),
                "undetected": stats.get("undetected", 0),
                "error": None,
            }
        except Exception as e:
            return {"query": url, "type": "url", "error": str(e)}

    def print_result(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}VirusTotal: {result['query']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        malicious = result.get("malicious", 0)
        suspicious = result.get("suspicious", 0)
        color = Colors.RED if malicious > 0 else Colors.YELLOW if suspicious > 0 else Colors.GREEN
        verdict = "MALICIOUS" if malicious > 0 else "SUSPICIOUS" if suspicious > 0 else "CLEAN"

        print(f"{Colors.YELLOW}Verdict:{Colors.RESET} {color}{verdict}{Colors.RESET}")
        print(f"{Colors.YELLOW}Malicious:{Colors.RESET} {Colors.RED}{malicious}{Colors.RESET}")
        print(f"{Colors.YELLOW}Suspicious:{Colors.RESET} {Colors.YELLOW}{suspicious}{Colors.RESET}")
        print(f"{Colors.YELLOW}Harmless:{Colors.RESET} {Colors.GREEN}{result.get('harmless', 0)}{Colors.RESET}")
        print(f"{Colors.YELLOW}Undetected:{Colors.RESET} {result.get('undetected', 0)}")
        if result.get("country"):
            print(f"{Colors.YELLOW}Country:{Colors.RESET} {result['country']}")
        if result.get("as_owner"):
            print(f"{Colors.YELLOW}ASN Owner:{Colors.RESET} {result['as_owner']}")
        if result.get("tags"):
            print(f"{Colors.YELLOW}Tags:{Colors.RESET} {', '.join(result['tags'])}")
        if result.get("categories"):
            cats = list(result["categories"].values())
            print(f"{Colors.YELLOW}Categories:{Colors.RESET} {', '.join(set(cats))}")

class AbuseIPDB:

    BASE_URL = "https://api.abuseipdb.com/api/v2"

    def __init__(self):
        self.api_key = ABUSEIPDB_API_KEY
        self.headers = {
            "Key": self.api_key,
            "Accept": "application/json",
        } if self.api_key else {}

    def check_ip(self, ip: str, max_age_days: int = 90) -> Dict[str, Any]:
        result = {
            "ip": ip,
            "abuse_score": 0,
            "total_reports": 0,
            "country": None,
            "isp": None,
            "domain": None,
            "is_tor": False,
            "is_public": True,
            "usage_type": None,
            "last_reported": None,
            "categories": [],
            "error": None,
        }

        if not self.api_key:
            result["error"] = "ABUSEIPDB_API_KEY not set in .env"
            return result

        try:
            r = requests.get(
                f"{self.BASE_URL}/check",
                headers=self.headers,
                params={"ipAddress": ip, "maxAgeInDays": max_age_days, "verbose": True},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json().get("data", {})
                result.update(
                    {
                        "abuse_score": data.get("abuseConfidenceScore", 0),
                        "total_reports": data.get("totalReports", 0),
                        "country": data.get("countryCode"),
                        "isp": data.get("isp"),
                        "domain": data.get("domain"),
                        "is_tor": data.get("isTor", False),
                        "is_public": data.get("isPublic", True),
                        "usage_type": data.get("usageType"),
                        "last_reported": data.get("lastReportedAt"),
                    }
                )
            else:
                result["error"] = f"AbuseIPDB returned {r.status_code}"
        except Exception as e:
            result["error"] = str(e)

        return result

    def print_result(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}AbuseIPDB: {result['ip']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        score = result["abuse_score"]
        color = Colors.RED if score >= 50 else Colors.YELLOW if score >= 10 else Colors.GREEN
        print(f"{Colors.YELLOW}Abuse Score:{Colors.RESET} {color}{score}/100{Colors.RESET}")
        print(f"{Colors.YELLOW}Total Reports:{Colors.RESET} {result['total_reports']}")
        print(f"{Colors.YELLOW}Country:{Colors.RESET} {result.get('country', 'N/A')}")
        print(f"{Colors.YELLOW}ISP:{Colors.RESET} {result.get('isp', 'N/A')}")
        print(f"{Colors.YELLOW}Usage Type:{Colors.RESET} {result.get('usage_type', 'N/A')}")
        if result["is_tor"]:
            print(f"{Colors.RED}⚠ TOR Exit Node{Colors.RESET}")
        if result.get("last_reported"):
            print(f"{Colors.YELLOW}Last Reported:{Colors.RESET} {result['last_reported'][:10]}")

def run_threat_intel():
    print(f"\n{Colors.BOLD}Threat Intelligence Lookup{Colors.RESET}")
    print(f"  {Colors.GREEN}1.{Colors.RESET} VirusTotal - IP/Domain/URL")
    print(f"  {Colors.GREEN}2.{Colors.RESET} AbuseIPDB - IP Reputation")
    print(f"  {Colors.GREEN}3.{Colors.RESET} Both")

    choice = input(f"\n{Colors.GREEN}Select (1/2/3): {Colors.RESET}").strip()
    target = input(f"{Colors.GREEN}Enter IP, domain, or URL: {Colors.RESET}").strip()
    if not target:
        return None

    results = {}

    if choice in ("1", "3"):
        vt = VirusTotal()
        if "@" not in target and "://" not in target:
            if target.replace(".", "").isdigit() or ":" in target:
                r = vt.check_ip(target)
            else:
                r = vt.check_domain(target)
        else:
            r = vt.check_url(target)
        vt.print_result(r)
        results["virustotal"] = r

    if choice in ("2", "3"):
        ip_target = target
        if not (target.replace(".", "").isdigit()):
            print(f"{Colors.YELLOW}AbuseIPDB requires an IP address.{Colors.RESET}")
        else:
            adb = AbuseIPDB()
            r = adb.check_ip(ip_target)
            adb.print_result(r)
            results["abuseipdb"] = r

    return results if results else None
