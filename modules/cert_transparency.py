import requests
from typing import Dict, Any, List
import sys
sys.path.append('..')
from config import Colors, USER_AGENT
from modules import get_proxies


class CertTransparency:

    BASE_URL = "https://crt.sh"
    # Keyless and free, but limited to a few requests an hour: fallback only.
    FALLBACK_URL = "https://api.certspotter.com/v1/issuances"

    def _search_crtsh(self, domain: str) -> Dict[str, Any]:
        result = {
            "domain": domain,
            "certificates": [],
            "subdomains": [],
            "total_certs": 0,
            "error": None,
        }

        try:
            proxies = get_proxies()
            response = requests.get(
                self.BASE_URL,
                params = {"q": f"%.{domain}", "output": "json", "deduplicate": "Y"},
                timeout=30,
                headers={"User-Agent": USER_AGENT},
                proxies=proxies,  
            )


            if response.status_code != 200:
                result["error"] = f"crt.sh returned status {response.status_code}"
                return result

            try:
                certs = response.json()
            except Exception:
                result["error"] = "Failed to parse crt.sh response"
                return result

            result["total_certs"] = len(certs)
            subdomains: set = set()
            cert_list: List[Dict] = []

            for cert in certs:
                name_value = cert.get("name_value", "")
                for name in name_value.split("\n"):
                    name = name.strip().lower()
                    if name.startswith("*."):
                        name = name[2:]
                    if name == domain or name.endswith("." + domain):
                        subdomains.add(name)

                issuer_raw = cert.get("issuer_name", "")
                issuer = ""
                if "O=" in issuer_raw:
                    issuer = issuer_raw.split("O=")[-1].split(",")[0].strip()
                else:
                    issuer = issuer_raw

                cert_list.append(
                    {
                        "id": cert.get("id"),
                        "logged_at": cert.get("entry_timestamp"),
                        "not_before": cert.get("not_before"),
                        "not_after": cert.get("not_after"),
                        "common_name": cert.get("common_name"),
                        "issuer": issuer,
                    }
                )

            result["subdomains"] = sorted(list(subdomains))
            result["certificates"] = cert_list[:20]

        except requests.Timeout:
            result["error"] = "Request timed out (crt.sh can be slow, try again)"
        except Exception as e:
            result["error"] = str(e)

        return result

    def search(self, domain: str) -> Dict[str, Any]:
        """Look up subdomains in CT logs: crt.sh first, certspotter when it fails.

        crt.sh stays the primary source. certspotter is only asked when crt.sh
        returned an error, so a healthy crt.sh never spends the fallback's small
        keyless quota. ``result["source"]`` names the source that answered.
        """
        result = self._search_crtsh(domain)
        if not result["error"]:
            result["source"] = "crt.sh"
            return result

        fallback = self._search_certspotter(domain)
        if fallback["error"]:
            # Report both, so a reader can tell the fallback was tried too.
            result["error"] = f"{result['error']}; fallback certspotter: {fallback['error']}"
            result["source"] = None
            return result

        fallback["fallback_reason"] = result["error"]
        return fallback

    def _search_certspotter(self, domain: str) -> Dict[str, Any]:
        result = {
            "domain": domain,
            "certificates": [],
            "subdomains": [],
            "total_certs": 0,
            "error": None,
            "source": "certspotter",
        }

        try:
            response = requests.get(
                self.FALLBACK_URL,
                params=[
                    ("domain", domain),
                    ("include_subdomains", "true"),
                    ("expand", "dns_names"),
                    ("expand", "issuer"),
                ],
                timeout=30,
                headers={"User-Agent": USER_AGENT},
                proxies=get_proxies(),
            )
            if response.status_code != 200:
                result["error"] = f"certspotter returned status {response.status_code}"
                return result
            try:
                issuances = response.json()
            except Exception:
                result["error"] = "Failed to parse certspotter response"
                return result
            if not isinstance(issuances, list):
                result["error"] = "Unexpected certspotter response"
                return result
        except requests.Timeout:
            result["error"] = "certspotter request timed out"
            return result
        except Exception as e:
            result["error"] = str(e)
            return result

        result["total_certs"] = len(issuances)
        subdomains: set = set()
        cert_list: List[Dict] = []
        for issuance in issuances:
            names = issuance.get("dns_names") or []
            for name in names:
                name = str(name).strip().lower()
                if name.startswith("*."):
                    name = name[2:]
                # A certificate can cover unrelated domains (example.com's also
                # lists example.net and example.org), so keep only this domain.
                if name == domain or name.endswith("." + domain):
                    subdomains.add(name)
            issuer = issuance.get("issuer") or {}
            cert_list.append(
                {
                    "id": issuance.get("id"),
                    "logged_at": None,  # certspotter's issuances do not carry a log time
                    "not_before": issuance.get("not_before"),
                    "not_after": issuance.get("not_after"),
                    "common_name": names[0] if names else None,
                    "issuer": issuer.get("friendly_name") or issuer.get("name") or "",
                }
            )

        result["subdomains"] = sorted(subdomains)
        result["certificates"] = cert_list[:20]
        return result

    def print_result(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Certificate Transparency: {result['domain']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        if result.get("source") and result["source"] != "crt.sh":
            print(f"{Colors.YELLOW}Source:{Colors.RESET} {result['source']} (crt.sh failed: {result.get('fallback_reason')})")
        print(f"{Colors.YELLOW}Total Certificates in CT logs:{Colors.RESET} {result['total_certs']}")
        print(f"{Colors.YELLOW}Unique Subdomains Discovered:{Colors.RESET} {len(result['subdomains'])}")

        if result["subdomains"]:
            print(f"\n{Colors.BOLD}Subdomains:{Colors.RESET}")
            for sub in result["subdomains"][:40]:
                print(f"  {Colors.GREEN}•{Colors.RESET} {sub}")
            if len(result["subdomains"]) > 40:
                print(f"  {Colors.YELLOW}... and {len(result['subdomains']) - 40} more{Colors.RESET}")

        if result["certificates"]:
            print(f"\n{Colors.BOLD}Recent Certificates:{Colors.RESET}")
            for cert in result["certificates"][:5]:
                print(
                    f"  {Colors.CYAN}CN:{Colors.RESET} {cert['common_name']}  "
                    f"{Colors.CYAN}Issuer:{Colors.RESET} {cert['issuer']}  "
                    f"{Colors.CYAN}Logged:{Colors.RESET} {(cert['logged_at'] or '')[:10]}"
                )


def run_cert_transparency():
    ct = CertTransparency()
    print(f"\n{Colors.BOLD}Certificate Transparency Lookup{Colors.RESET}")
    domain = input(f"{Colors.GREEN}Enter domain: {Colors.RESET}").strip()
    if domain:
        print(f"{Colors.CYAN}Querying crt.sh... (may take 10-30 seconds){Colors.RESET}")
        result = ct.search(domain)
        ct.print_result(result)
        return result
    return None
