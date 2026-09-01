import ipaddress
import requests
from typing import Dict, Any, List
import sys
sys.path.append('..')
from config import Colors, SHODAN_API_KEY
from modules.module_status import annotate, print_status_notice, OK, SKIPPED, RATE_LIMITED, ERROR


class ShodanLookup:

    BASE_URL = "https://api.shodan.io"
    INTERNETDB_URL = "https://internetdb.shodan.io"

    def __init__(self):
        self.api_key = SHODAN_API_KEY

    @staticmethod
    def _is_ip(value: str) -> bool:
        try:
            ipaddress.ip_address((value or "").strip())
            return True
        except ValueError:
            return False

    def _internetdb(self, ip: str, result: Dict[str, Any], reason: str) -> Dict[str, Any]:
        try:
            r = requests.get(f"{self.INTERNETDB_URL}/{ip}", timeout=15)
        except Exception as e:
            return annotate(result, SKIPPED, f"{reason}; the free InternetDB dataset was unreachable ({str(e)[:80]})")

        if r.status_code == 404:
            result["source"] = "internetdb"
            return annotate(result, OK, f"{reason}; the free InternetDB dataset has nothing on this address")
        if r.status_code == 429:
            return annotate(result, RATE_LIMITED, "InternetDB rate limit reached")
        if r.status_code != 200:
            return annotate(result, SKIPPED, f"{reason}; InternetDB returned {r.status_code}")

        try:
            data = r.json()
        except ValueError:
            return annotate(result, SKIPPED, f"{reason}; InternetDB returned a non-JSON response")

        result.update({
            "open_ports": sorted(data.get("ports") or []),
            "hostnames": data.get("hostnames") or [],
            "tags": data.get("tags") or [],
            "vulns": data.get("vulns") or [],
            "cpes": data.get("cpes") or [],
            "source": "internetdb",
        })
        annotate(result, OK, f"{reason}; ports, hostnames and CVEs come from the free InternetDB dataset, "
                             "which carries no organisation, location or banner detail")
        return result

    def host_info(self, ip: str) -> Dict[str, Any]:
        result = {
            "ip": ip,
            "organization": None,
            "isp": None,
            "country": None,
            "city": None,
            "os": None,
            "open_ports": [],
            "services": [],
            "vulns": [],
            "hostnames": [],
            "domains": [],
            "tags": [],
            "cpes": [],
            "last_update": None,
            "source": "shodan",
            "error": None,
        }

        if not self._is_ip(ip):
            return annotate(result, ERROR, "Host lookup needs an IP address")

        if not self.api_key:
            return self._internetdb(ip, result, "No API key configured (SHODAN_API_KEY)")

        try:
            r = requests.get(
                f"{self.BASE_URL}/shodan/host/{ip}",
                params={"key": self.api_key},
                timeout=15,
            )

            if r.status_code == 404:
                result["error"] = "No information available for this IP in Shodan"
                return result
            if r.status_code == 401:
                return annotate(result, ERROR, "Invalid Shodan API key")
            if r.status_code == 403:
                return self._internetdb(
                    ip, result,
                    "Shodan host lookup needs a paid membership or query credits (free keys return 403)",
                )
            if r.status_code == 429:
                return self._internetdb(ip, result, "Shodan API rate limit reached")
            if r.status_code != 200:
                result["error"] = f"Shodan API returned {r.status_code}"
                return result

            data = r.json()

            result.update(
                {
                    "organization": data.get("org"),
                    "isp": data.get("isp"),
                    "country": data.get("country_name"),
                    "city": data.get("city"),
                    "os": data.get("os"),
                    "open_ports": sorted(data.get("ports", [])),
                    "hostnames": data.get("hostnames", []),
                    "domains": data.get("domains", []),
                    "tags": data.get("tags", []),
                    "last_update": data.get("last_update"),
                    "vulns": list(data.get("vulns", {}).keys()),
                }
            )

            services = []
            for item in data.get("data", []):
                svc = {
                    "port": item.get("port"),
                    "transport": item.get("transport", "tcp"),
                    "product": item.get("product"),
                    "version": item.get("version"),
                    "module": item.get("_shodan", {}).get("module"),
                    "banner": (item.get("data") or "")[:200].strip(),
                }
                services.append(svc)

            result["services"] = services
            result["status"] = OK

        except Exception as e:
            return annotate(result, ERROR, str(e))

        return result

    def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        result = {
            "query": query,
            "total": 0,
            "matches": [],
            "error": None,
        }

        if not self.api_key:
            return annotate(result, SKIPPED, "No API key configured (SHODAN_API_KEY)")

        try:
            r = requests.get(
                f"{self.BASE_URL}/shodan/host/search",
                params={"key": self.api_key, "query": query, "limit": limit},
                timeout=20,
            )

            if r.status_code == 403:
                return annotate(result, SKIPPED, "Shodan search requires a paid membership or query credits (free API keys return 403)")
            if r.status_code == 429:
                return annotate(result, RATE_LIMITED, "Shodan API rate limit reached")
            if r.status_code != 200:
                result["error"] = f"Shodan API returned {r.status_code}: {r.text[:200]}"
                return result

            data = r.json()
            result["total"] = data.get("total", 0)

            for match in data.get("matches", []):
                result["matches"].append(
                    {
                        "ip": match.get("ip_str"),
                        "port": match.get("port"),
                        "org": match.get("org"),
                        "country": match.get("location", {}).get("country_name"),
                        "product": match.get("product"),
                        "version": match.get("version"),
                    }
                )
            result["status"] = OK

        except Exception as e:
            return annotate(result, ERROR, str(e))

        return result

    def print_host_result(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Shodan Host: {result['ip']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if print_status_notice(result):
            return
        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        print(f"{Colors.YELLOW}Organization:{Colors.RESET} {result.get('organization', 'N/A')}")
        print(f"{Colors.YELLOW}ISP:{Colors.RESET} {result.get('isp', 'N/A')}")
        print(f"{Colors.YELLOW}Location:{Colors.RESET} {result.get('city', 'N/A')}, {result.get('country', 'N/A')}")
        print(f"{Colors.YELLOW}OS:{Colors.RESET} {result.get('os', 'Unknown')}")

        if result.get("source") == "internetdb":
            print(f"{Colors.YELLOW}Source:{Colors.RESET} InternetDB (free dataset)")

        if result["open_ports"]:
            print(f"\n{Colors.YELLOW}Open Ports:{Colors.RESET} {', '.join(map(str, result['open_ports']))}")

        if result["services"]:
            print(f"\n{Colors.BOLD}Services:{Colors.RESET}")
            for svc in result["services"]:
                product = f" {svc['product']}" if svc["product"] else ""
                version = f" {svc['version']}" if svc["version"] else ""
                print(f"  {Colors.GREEN}{svc['port']}/{svc['transport']}{Colors.RESET}{product}{version}")

        if result["vulns"]:
            print(f"\n{Colors.RED}⚠ Known Vulnerabilities (CVEs):{Colors.RESET}")
            for cve in result["vulns"]:
                print(f"  {Colors.RED}[!]{Colors.RESET} {cve}")

        if result["tags"]:
            print(f"\n{Colors.YELLOW}Tags:{Colors.RESET} {', '.join(result['tags'])}")

        if result.get("last_update"):
            print(f"\n{Colors.YELLOW}Last Updated:{Colors.RESET} {result['last_update'][:10]}")

    def print_search_result(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Shodan Search: {result['query']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if print_status_notice(result):
            return
        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        print(f"{Colors.YELLOW}Total Results:{Colors.RESET} {result['total']}")
        if result["matches"]:
            print(f"\n{Colors.BOLD}Top Matches:{Colors.RESET}")
            for m in result["matches"]:
                print(
                    f"  {Colors.GREEN}{m['ip']}:{m['port']}{Colors.RESET} "
                    f"| {m.get('org', 'N/A')} | {m.get('country', 'N/A')}"
                )


def run_shodan():
    print(f"\n{Colors.BOLD}Shodan Lookup{Colors.RESET}")
    print(f"  {Colors.GREEN}1.{Colors.RESET} Host info (IP)")
    print(f"  {Colors.GREEN}2.{Colors.RESET} Search (dork query)")

    choice = input(f"\n{Colors.GREEN}Select (1/2): {Colors.RESET}").strip()
    target = input(f"{Colors.GREEN}Enter IP or search query: {Colors.RESET}").strip()
    if not target:
        return None

    sh = ShodanLookup()
    if choice == "2":
        print(f"{Colors.CYAN}Searching Shodan...{Colors.RESET}")
        result = sh.search(target)
        sh.print_search_result(result)
        return result
    else:
        print(f"{Colors.CYAN}Fetching host info...{Colors.RESET}")
        result = sh.host_info(target)
        sh.print_host_result(result)
        return result
