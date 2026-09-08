import os
import requests
from typing import Dict, Any, List
import sys
sys.path.append('..')
from config import Colors
from modules.module_status import annotate, print_status_notice, OK, RATE_LIMITED, ERROR
from modules import get_proxies

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


class GitHubRecon:
    """Public GitHub recon for a username or organization.

    Works without any API key (unauthenticated, 60 req/h). An optional
    GITHUB_TOKEN raises the rate limit. A rate-limited response (HTTP 403/429)
    degrades to `rate_limited` instead of erroring.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self):
        self.token = GITHUB_TOKEN

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "PRISM-OSINT"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def lookup(self, username: str) -> Dict[str, Any]:
        username = (username or "").strip().lstrip("@")
        result: Dict[str, Any] = {
            "username": username,
            "profile": None,
            "repo_count": 0,
            "total_stars": 0,
            "top_languages": [],
            "emails": [],
            "error": None,
        }

        if not username:
            return annotate(result, ERROR, "No username provided")

        try:
            proxies = get_proxies()
            r = requests.get(
                f"{self.BASE_URL}/users/{username}",
                headers=self._headers(),
                timeout=15,
                proxies=proxies,  
            )
            if r.status_code == 404:
                result["error"] = "GitHub user not found"
                return result
            if r.status_code in (403, 429):
                return annotate(result, RATE_LIMITED,
                                "GitHub API rate limit reached - set GITHUB_TOKEN to raise it")
            if r.status_code != 200:
                return annotate(result, ERROR, f"GitHub API returned {r.status_code}")

            u = r.json()
            result["profile"] = {
                "name": u.get("name"),
                "bio": u.get("bio"),
                "company": u.get("company"),
                "location": u.get("location"),
                "blog": u.get("blog") or None,
                "twitter": u.get("twitter_username"),
                "email": u.get("email"),
                "type": u.get("type"),
                "followers": u.get("followers"),
                "following": u.get("following"),
                "public_repos": u.get("public_repos"),
                "created_at": (u.get("created_at") or "")[:10] or None,
                "avatar_url": u.get("avatar_url"),
                "html_url": u.get("html_url"),
            }
            if u.get("email"):
                result["emails"].append(u["email"])

            repos = self._get_repos(username)
            result["repo_count"] = len(repos)
            lang_count: Dict[str, int] = {}
            stars = 0
            for repo in repos:
                stars += repo.get("stargazers_count", 0) or 0
                lang = repo.get("language")
                if lang:
                    lang_count[lang] = lang_count.get(lang, 0) + 1
            result["total_stars"] = stars
            result["top_languages"] = [
                {"language": k, "count": v}
                for k, v in sorted(lang_count.items(), key=lambda x: x[1], reverse=True)[:8]
            ]

            for email in self._emails_from_events(username):
                if email not in result["emails"]:
                    result["emails"].append(email)

            result["status"] = OK
        except Exception as e:
            return annotate(result, ERROR, str(e)[:200])

        return result

    def _get_repos(self, username: str) -> List[Dict[str, Any]]:
        try:
            proxies = get_proxies()
            r = requests.get(
                f"{self.BASE_URL}/users/{username}/repos",
                headers=self._headers(),
                params={"per_page": 100, "sort": "pushed"},
                timeout=15,
                proxies=proxies,  
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return []

    def _emails_from_events(self, username: str) -> List[str]:
        emails: List[str] = []
        try:
            proxies = get_proxies()
            r = requests.get(
                f"{self.BASE_URL}/users/{username}/events/public",
                headers=self._headers(),
                timeout=15,
                proxies=proxies,  
            )
            if r.status_code != 200:
                return emails
            for event in r.json():
                for commit in (event.get("payload", {}) or {}).get("commits") or []:
                    email = ((commit.get("author") or {}).get("email") or "").strip()
                    if email and "noreply" not in email and email not in emails:
                        emails.append(email)
        except Exception:
            pass
        return emails

    def print_result(self, result: Dict[str, Any]) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}GitHub Recon: {result.get('username')}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if print_status_notice(result):
            return
        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        p = result.get("profile") or {}
        print(f"{Colors.YELLOW}Name:{Colors.RESET} {p.get('name', 'N/A')}")
        print(f"{Colors.YELLOW}Bio:{Colors.RESET} {p.get('bio', 'N/A')}")
        print(f"{Colors.YELLOW}Location:{Colors.RESET} {p.get('location', 'N/A')}")
        print(f"{Colors.YELLOW}Followers:{Colors.RESET} {p.get('followers', 0)} · Repos: {result.get('repo_count', 0)} · Stars: {result.get('total_stars', 0)}")
        if result.get("top_languages"):
            langs = ", ".join(f"{l['language']} ({l['count']})" for l in result["top_languages"])
            print(f"{Colors.YELLOW}Top languages:{Colors.RESET} {langs}")
        if result.get("emails"):
            print(f"{Colors.RED}Emails:{Colors.RESET} {', '.join(result['emails'])}")
