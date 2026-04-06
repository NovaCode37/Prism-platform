import requests
import hashlib
from typing import Dict, Any, List, Optional
import sys
sys.path.append('..')
from config import LEAK_LOOKUP_API_KEY, Colors

class LeakLookup:

    HIBP_API = "https://haveibeenpwned.com/api/v3"
    LEAK_LOOKUP_API = "https://leak-lookup.com/api/search"

    def __init__(self):
        self.leak_lookup_key = LEAK_LOOKUP_API_KEY

    def check_email_hibp(self, email: str) -> Dict[str, Any]:
        result = {
            "email": email,
            "breached": False,
            "breaches": [],
            "total_breaches": 0,
            "error": None
        }

        headers = {
            "User-Agent": "OSINT-Tool",
            "hibp-api-key": ""
        }

        try:
            response = requests.get(
                f"{self.HIBP_API}/breachedaccount/{email}",
                headers=headers,
                params={"truncateResponse": "false"},
                timeout=10
            )

            if response.status_code == 200:
                breaches = response.json()
                result["breached"] = True
                result["total_breaches"] = len(breaches)

                for breach in breaches:
                    result["breaches"].append({
                        "name": breach.get("Name"),
                        "title": breach.get("Title"),
                        "domain": breach.get("Domain"),
                        "breach_date": breach.get("BreachDate"),
                        "added_date": breach.get("AddedDate"),
                        "pwn_count": breach.get("PwnCount"),
                        "data_classes": breach.get("DataClasses", []),
                        "is_verified": breach.get("IsVerified"),
                        "is_sensitive": breach.get("IsSensitive")
                    })

            elif response.status_code == 404:
                result["breached"] = False
            elif response.status_code == 401:
                result["error"] = "HIBP API key required for breach lookup"
            else:
                result["error"] = f"HIBP returned status {response.status_code}"

        except requests.exceptions.RequestException as e:
            result["error"] = str(e)

        return result

    def check_password_pwned(self, password: str) -> Dict[str, Any]:
        result = {
            "pwned": False,
            "count": 0,
            "error": None
        }

        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]

        try:
            response = requests.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                timeout=10
            )

            if response.status_code == 200:
                hashes = response.text.splitlines()
                for h in hashes:
                    h_suffix, count = h.split(':')
                    if h_suffix == suffix:
                        result["pwned"] = True
                        result["count"] = int(count)
                        break
            else:
                result["error"] = f"API returned status {response.status_code}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def check_leak_lookup(self, query: str, query_type: str = "email_address") -> Dict[str, Any]:
        result = {
            "query": query,
            "type": query_type,
            "found": False,
            "leaks": [],
            "error": None
        }

        if not self.leak_lookup_key:
            result["error"] = "Leak-Lookup API key not configured"
            return result

        try:
            response = requests.post(
                self.LEAK_LOOKUP_API,
                data={
                    "key": self.leak_lookup_key,
                    "type": query_type,
                    "query": query
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("error") == "false" and data.get("message"):
                    result["found"] = True
                    if isinstance(data["message"], dict):
                        for source, entries in data["message"].items():
                            result["leaks"].append({
                                "source": source,
                                "entries": entries if isinstance(entries, list) else [entries]
                            })
                elif data.get("message") == "Not found":
                    result["found"] = False
                else:
                    result["error"] = data.get("message", "Unknown response")
            else:
                result["error"] = f"API returned status {response.status_code}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def check_email_full(self, email: str) -> Dict[str, Any]:
        result = {
            "email": email,
            "hibp": self.check_email_hibp(email),
            "leak_lookup": self.check_leak_lookup(email, "email_address") if self.leak_lookup_key else None
        }

        result["total_breaches"] = 0
        result["is_compromised"] = False

        if result["hibp"]["breached"]:
            result["is_compromised"] = True
            result["total_breaches"] += result["hibp"]["total_breaches"]

        if result["leak_lookup"] and result["leak_lookup"]["found"]:
            result["is_compromised"] = True
            result["total_breaches"] += len(result["leak_lookup"]["leaks"])

        return result

    def print_result(self, result: Dict, check_type: str = "email"):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Leak/Breach Check Results{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if check_type == "email":
            email = result.get("email", "")
            is_compromised = result.get("is_compromised", False)

            status = f"{Colors.RED}⚠ COMPROMISED{Colors.RESET}" if is_compromised else f"{Colors.GREEN}✓ NOT FOUND IN BREACHES{Colors.RESET}"

            print(f"{Colors.YELLOW}Email:{Colors.RESET} {email}")
            print(f"{Colors.YELLOW}Status:{Colors.RESET} {status}")
            print(f"{Colors.YELLOW}Total Breaches:{Colors.RESET} {result.get('total_breaches', 0)}")

            hibp = result.get("hibp", {})
            if hibp.get("breaches"):
                print(f"\n{Colors.BOLD}Have I Been Pwned Breaches:{Colors.RESET}")
                for breach in hibp["breaches"][:10]:
                    print(f"  {Colors.RED}•{Colors.RESET} {breach['name']} ({breach.get('breach_date', 'N/A')})")
                    print(f"    Data: {', '.join(breach.get('data_classes', [])[:5])}")
                if len(hibp["breaches"]) > 10:
                    print(f"    ... and {len(hibp['breaches']) - 10} more")

            ll = result.get("leak_lookup")
            if ll and ll.get("leaks"):
                print(f"\n{Colors.BOLD}Leak-Lookup Results:{Colors.RESET}")
                for leak in ll["leaks"][:5]:
                    print(f"  {Colors.RED}•{Colors.RESET} Source: {leak['source']}")

        elif check_type == "password":
            if result.get("pwned"):
                print(f"{Colors.RED}⚠ PASSWORD COMPROMISED!{Colors.RESET}")
                print(f"Found in {Colors.RED}{result['count']:,}{Colors.RESET} breaches")
                print(f"{Colors.YELLOW}Recommendation: Change this password immediately!{Colors.RESET}")
            else:
                print(f"{Colors.GREEN}✓ Password not found in known breaches{Colors.RESET}")

        if result.get("error"):
            print(f"\n{Colors.YELLOW}Note:{Colors.RESET} {result['error']}")

def run_leak_lookup():
    ll = LeakLookup()

    print(f"\n{Colors.BOLD}Leak/Breach Lookup{Colors.RESET}")
    print(f"{Colors.CYAN}Check if data has been compromised{Colors.RESET}")

    print(f"\n{Colors.YELLOW}Options:{Colors.RESET}")
    print("  1. Check email")
    print("  2. Check password (safe - uses k-anonymity)")
    print("  3. Check username")
    print("  4. Check IP address")
    print("  5. Check domain")

    choice = input(f"\n{Colors.GREEN}Select option (1-5): {Colors.RESET}").strip()

    if choice == "1":
        email = input(f"{Colors.GREEN}Enter email: {Colors.RESET}").strip()
        if email:
            result = ll.check_email_full(email)
            ll.print_result(result, "email")
            return result

    elif choice == "2":
        import getpass
        password = getpass.getpass(f"{Colors.GREEN}Enter password (hidden): {Colors.RESET}")
        if password:
            result = ll.check_password_pwned(password)
            ll.print_result(result, "password")
            return result

    elif choice in ("3", "4", "5"):
        type_map = {"3": "username", "4": "ip_address", "5": "domain"}
        query_type = type_map[choice]
        query = input(f"{Colors.GREEN}Enter {query_type.replace('_', ' ')}: {Colors.RESET}").strip()
        if query:
            result = ll.check_leak_lookup(query, query_type)
            ll.print_result(result, query_type)
            return result

    print(f"{Colors.RED}Invalid input{Colors.RESET}")
    return None

if __name__ == "__main__":
    run_leak_lookup()
