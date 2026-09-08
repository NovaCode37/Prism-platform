import hashlib
from typing import Dict, Any, List
import requests
import sys
from modules import get_proxies

sys.path.append("..")

from config import Colors
from modules.module_status import (
    annotate,
    print_status_notice,
    OK,
    RATE_LIMITED,
    ERROR,
)

class GravatarRecon:
    """Public Gravatar profile lookup for an email address.

    Uses the public Gravatar profile endpoint with a SHA-256 email hash.
    No API key is required. HTTP 429 responses are reported as
    `rate_limited`.
    """

    BASE_URL = "https://gravatar.com"

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": "PRISM-OSINT",
        }

    def lookup(self, email: str) -> Dict[str, Any]:
        email = (email or "").strip().lower()

        result: Dict[str, Any] = {
            "email": email,
            "avatar_url": None,
            "display_name": None,
            "accounts": [],
            "error": None,
        }

        if not email:
            return annotate(result, ERROR, "No email provided")

        email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()
        try:
            proxies = get_proxies()
            r = requests.get(
                f"{self.BASE_URL}/{email_hash}.json",
                headers=self._headers(),
                timeout=15,
                proxies=proxies,  # Add this line
            )

            if r.status_code == 404:
                return annotate(result, ERROR, "Gravatar profile not found")

            if r.status_code == 429:
                return annotate(
                    result,
                    RATE_LIMITED,
                    "Gravatar API rate limit reached",
                )

            if r.status_code != 200:
                return annotate(
                    result,
                    ERROR,
                    f"Gravatar API returned {r.status_code}",
                )

            data = r.json()
            entries = data.get("entry") or []

            if not entries:
                return annotate(result, ERROR, "Gravatar profile not found")

            profile = entries[0]

            result["avatar_url"] = profile.get("thumbnailUrl")
            result["display_name"] = profile.get("displayName")
            result["accounts"] = profile.get("accounts", [])

            result["status"] = OK

        except Exception as e:
            return annotate(result, ERROR, str(e)[:200])

        return result

    def print_result(self, result: Dict[str, Any]) -> None:
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}Gravatar Recon: {result.get('email')}{Colors.RESET}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}")

        if print_status_notice(result):
            return

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        print(
            f"{Colors.YELLOW}Display Name:{Colors.RESET} "
            f"{result.get('display_name') or 'N/A'}"
        )

        print(
            f"{Colors.YELLOW}Avatar:{Colors.RESET} "
            f"{result.get('avatar_url') or 'N/A'}"
        )

        accounts: List[Dict[str, Any]] = result.get("accounts") or []

        if accounts:
            print(f"{Colors.YELLOW}Linked Accounts:{Colors.RESET}")

            for account in accounts:
                name = account.get("name") or "Unknown"
                display = account.get("display") or account.get("username") or ""
                url = account.get("url") or ""

                print(f"  • {name}: {display}")

                if url:
                    print(f"    {url}")