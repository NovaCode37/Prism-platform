import re
import requests
from typing import Dict, Any, Optional
import sys
sys.path.append('..')
from config import Colors

class TelegramLookup:

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def lookup_username(self, username: str) -> Dict[str, Any]:
        username = username.lstrip("@").strip()
        result = {
            "username": username,
            "url": f"https://t.me/{username}",
            "name": None,
            "bio": None,
            "subscribers": None,
            "entity_type": None,
            "verified": False,
            "photo_url": None,
            "is_private": False,
            "found": False,
            "fragment_url": f"https://fragment.com/username/{username}",
            "error": None,
        }

        try:
            r = requests.get(
                f"https://t.me/{username}",
                headers=self.HEADERS,
                timeout=12,
                allow_redirects=True,
            )

            if r.status_code == 404:
                result["found"] = False
                return result

            html = r.text

            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            og_desc  = re.search(r'<meta property="og:description" content="([^"]+)"', html)
            og_image = re.search(r'<meta property="og:image" content="([^"]+)"', html)

            if og_title:
                result["name"] = og_title.group(1).strip()
                result["found"] = True

            if og_desc:
                desc = og_desc.group(1).strip()
                sub_match = re.search(r'([\d\s,]+)\s+(?:subscribers|members|followers)', desc, re.IGNORECASE)
                if sub_match:
                    result["subscribers"] = sub_match.group(0).strip()
                result["bio"] = desc

            if og_image:
                result["photo_url"] = og_image.group(1)

            if '"tgme_page_extra"' in html or 'subscribers' in html.lower():
                result["entity_type"] = "channel" if "subscribers" in html.lower() else "group"
            elif 'tgme_page_context_link' in html:
                result["entity_type"] = "user"
            else:
                result["entity_type"] = "user"

            if "tgme_page_verified" in html or '"verified"' in html.lower():
                result["verified"] = True

            if "This account is private" in html or "tgme_page_joined" not in html and result["entity_type"] == "user":
                result["is_private"] = True

            subs_match = re.search(r'<div class="tgme_page_extra">([^<]+)</div>', html)
            if subs_match:
                result["subscribers"] = subs_match.group(1).strip()

        except requests.exceptions.ConnectionError:
            result["error"] = "Connection error — Telegram may be blocked. Try with VPN."
        except Exception as e:
            result["error"] = str(e)

        return result

    def lookup_id(self, tg_id: str, bot_token: Optional[str] = None) -> Dict[str, Any]:
        result = {
            "id": tg_id,
            "name": None,
            "username": None,
            "entity_type": None,
            "found": False,
            "error": None,
        }

        if bot_token:
            try:
                r = requests.get(
                    f"https://api.telegram.org/bot{bot_token}/getChat",
                    params={"chat_id": tg_id},
                    timeout=10,
                )
                data = r.json()
                if data.get("ok") and data.get("result"):
                    chat = data["result"]
                    result["found"] = True
                    result["name"] = (chat.get("first_name", "") + " " + chat.get("last_name", "")).strip() or chat.get("title")
                    result["username"] = chat.get("username")
                    result["entity_type"] = chat.get("type", "unknown")
                    result["bio"] = chat.get("bio") or chat.get("description")
                    result["url"] = f"https://t.me/{chat['username']}" if chat.get("username") else None
                    result["subscribers"] = chat.get("member_count")
                else:
                    result["error"] = data.get("description", "Not found")
            except Exception as e:
                result["error"] = str(e)
        else:
            result["error"] = "ID lookup requires TELEGRAM_BOT_TOKEN — add to .env"
            result["hint"] = "Create a bot via @BotFather (free) and add the token to .env"

        return result

    def run_lookup(self, target: str, bot_token: Optional[str] = None) -> Dict[str, Any]:
        target = target.strip()
        if target.lstrip("-").isdigit():
            return self.lookup_id(target, bot_token)
        return self.lookup_username(target.lstrip("@"))

    def print_result(self, result: Dict[str, Any]) -> None:
        print(f"\n{Colors.BOLD}Telegram Lookup{Colors.RESET}")
        if result.get("error"):
            print(f"{Colors.RED}Error:{Colors.RESET} {result['error']}")
            if result.get("hint"):
                print(f"{Colors.YELLOW}Hint:{Colors.RESET} {result['hint']}")
            return
        if not result.get("found"):
            print(f"{Colors.RED}Not found{Colors.RESET}")
            return
        print(f"{Colors.GREEN}Found{Colors.RESET}")
        for key in ("name", "username", "entity_type", "subscribers", "verified", "bio", "url"):
            if result.get(key) not in (None, False, ""):
                print(f"{Colors.YELLOW}{key.title()}:{Colors.RESET} {result[key]}")
