import requests
from typing import Dict, Any, List
import sys
sys.path.append('..')
from config import Colors

class CertTransparency:

    BASE_URL = "https://crt.sh"

    def search(self, domain: str) -> Dict[str, Any]:
        result = {
            "domain": domain,
            "certificates": [],
            "subdomains": [],
            "total_certs": 0,
            "error": None,
        }

        try:
            params = {"q": f"%.{domain}", "output": "json", "deduplicate": "Y"}
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=30,
                headers={"User-Agent": "OSINT-Toolkit/2.0"},
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
                    if name and domain in name:
                        if name.startswith("*."):
                            name = name[2:]
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

    def print_result(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Certificate Transparency: {result['domain']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

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
