import requests
from typing import Dict, Any, List
import sys
sys.path.append('..')
from config import EMAILREP_API_KEY, Colors


class EmailRepLookup:

    BASE_URL = "https://emailrep.io"

    def __init__(self):
        self.api_key = EMAILREP_API_KEY

    def lookup(self, email: str) -> Dict[str, Any]:
        result = {
            "email": email,
            "reputation": None,
            "suspicious": False,
            "references": 0,
            "blacklisted": False,
            "malicious_activity": False,
            "credentials_leaked": False,
            "data_breach": False,
            "disposable": False,
            "free_provider": False,
            "deliverable": None,
            "valid_mx": False,
            "spoofable": False,
            "spam": False,
            "profiles": [],
            "first_seen": None,
            "last_seen": None,
            "domain_reputation": None,
            "days_since_domain_creation": None,
            "error": None,
        }

        headers = {"User-Agent": "OSINT-Toolkit/2.0"}
        if self.api_key:
            headers["Key"] = self.api_key

        try:
            response = requests.get(
                f"{self.BASE_URL}/{email}",
                headers=headers,
                timeout=15,
            )

            if response.status_code == 400:
                result["error"] = "Invalid email address"
                return result
            if response.status_code == 429:
                result["error"] = "Rate limit reached. Add EMAILREP_API_KEY to .env for higher limits."
                return result
            if response.status_code != 200:
                result["error"] = f"API returned status {response.status_code}"
                return result

            data = response.json()
            details = data.get("details", {})

            result.update({
                "reputation": data.get("reputation"),
                "suspicious": data.get("suspicious", False),
                "references": data.get("references", 0),
                "blacklisted": details.get("blacklisted", False),
                "malicious_activity": details.get("malicious_activity", False),
                "credentials_leaked": details.get("credentials_leaked", False),
                "data_breach": details.get("data_breach", False),
                "disposable": details.get("disposable", False),
                "free_provider": details.get("free_provider", False),
                "deliverable": details.get("deliverable"),
                "valid_mx": details.get("valid_mx", False),
                "spoofable": details.get("spoofable", False),
                "spam": details.get("spam", False),
                "profiles": details.get("profiles", []),
                "first_seen": details.get("first_seen"),
                "last_seen": details.get("last_seen"),
                "domain_reputation": details.get("domain_reputation"),
                "days_since_domain_creation": details.get("days_since_domain_creation"),
            })

        except Exception as e:
            result["error"] = str(e)

        return result

    def print_result(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}EmailRep Lookup: {result['email']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        rep_color = {
            "high": Colors.GREEN,
            "medium": Colors.YELLOW,
            "low": Colors.RED,
            "none": Colors.RED,
        }.get(result.get("reputation", ""), Colors.YELLOW)

        print(f"{Colors.YELLOW}Reputation:{Colors.RESET}       {rep_color}{result['reputation'].upper()}{Colors.RESET}")
        print(f"{Colors.YELLOW}Suspicious:{Colors.RESET}       {Colors.RED + 'YES' + Colors.RESET if result['suspicious'] else Colors.GREEN + 'NO' + Colors.RESET}")
        print(f"{Colors.YELLOW}References:{Colors.RESET}       {result['references']}")
        print(f"{Colors.YELLOW}Domain Reputation:{Colors.RESET} {result.get('domain_reputation', 'N/A')}")

        flags = []
        if result["blacklisted"]:        flags.append(f"{Colors.RED}Blacklisted{Colors.RESET}")
        if result["malicious_activity"]: flags.append(f"{Colors.RED}Malicious Activity{Colors.RESET}")
        if result["credentials_leaked"]: flags.append(f"{Colors.RED}Credentials Leaked{Colors.RESET}")
        if result["data_breach"]:        flags.append(f"{Colors.RED}Data Breach{Colors.RESET}")
        if result["spam"]:               flags.append(f"{Colors.YELLOW}Spam{Colors.RESET}")
        if result["spoofable"]:          flags.append(f"{Colors.YELLOW}Spoofable{Colors.RESET}")
        if result["disposable"]:         flags.append(f"{Colors.YELLOW}Disposable{Colors.RESET}")

        if flags:
            print(f"\n{Colors.BOLD}Flags:{Colors.RESET}")
            for f in flags:
                print(f"  {Colors.RED}•{Colors.RESET} {f}")

        if result["profiles"]:
            print(f"\n{Colors.BOLD}Known Profiles:{Colors.RESET} {', '.join(result['profiles'])}")

        if result.get("first_seen"):
            print(f"{Colors.YELLOW}First Seen:{Colors.RESET} {result['first_seen']}")
        if result.get("last_seen"):
            print(f"{Colors.YELLOW}Last Seen:{Colors.RESET}  {result['last_seen']}")


HunterIO = EmailRepLookup


def run_emailrep():
    er = EmailRepLookup()
    print(f"\n{Colors.BOLD}EmailRep Lookup{Colors.RESET}")
    email = input(f"{Colors.GREEN}Enter email address: {Colors.RESET}").strip()
    if not email:
        print(f"{Colors.RED}No email provided{Colors.RESET}")
        return None
    result = er.lookup(email)
    er.print_result(result)
    return result


run_hunter_domain = run_emailrep
run_hunter_email = run_emailrep


if __name__ == "__main__":
    run_emailrep()
