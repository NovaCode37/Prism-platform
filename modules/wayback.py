import requests
from typing import Dict, Any, List
from datetime import datetime
import sys
sys.path.append('..')
from config import Colors

class WaybackMachine:

    CDX_URL = "https://web.archive.org/cdx/search/cdx"
    AVAILABILITY_URL = "https://archive.org/wayback/available"

    def get_snapshots(self, url: str, limit: int = 20) -> Dict[str, Any]:
        result = {
            "url": url,
            "snapshots": [],
            "total_snapshots": 0,
            "first_snapshot": None,
            "last_snapshot": None,
            "error": None,
        }

        try:
            params = {
                "url": url,
                "output": "json",
                "limit": limit,
                "fl": "timestamp,statuscode,mimetype,length",
                "filter": "statuscode:200",
                "collapse": "timestamp:8",
            }
            r = requests.get(self.CDX_URL, params=params, timeout=45)

            if r.status_code != 200:
                result["error"] = f"CDX API returned {r.status_code}"
                return result

            rows = r.json()
            if not rows or len(rows) < 2:
                result["error"] = "No snapshots found"
                return result

            header = rows[0]
            data_rows = rows[1:]

            def idx(field):
                return header.index(field) if field in header else None

            ts_idx = idx("timestamp")
            sc_idx = idx("statuscode")
            mime_idx = idx("mimetype")
            len_idx = idx("length")

            snapshots = []
            for row in data_rows:
                ts = row[ts_idx] if ts_idx is not None else ""
                try:
                    dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
                    human_date = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    human_date = ts

                snapshots.append(
                    {
                        "timestamp": ts,
                        "date": human_date,
                        "wayback_url": f"https://web.archive.org/web/{ts}/{url}",
                        "status": row[sc_idx] if sc_idx is not None else "?",
                        "mime": row[mime_idx] if mime_idx is not None else "?",
                        "size": int(row[len_idx]) if len_idx is not None and row[len_idx].isdigit() else 0,
                    }
                )

            result["snapshots"] = snapshots
            result["total_snapshots"] = len(snapshots)
            if snapshots:
                result["first_snapshot"] = snapshots[0]["date"]
                result["last_snapshot"] = snapshots[-1]["date"]

        except Exception as e:
            result["error"] = str(e)

        return result

    def get_all_urls(self, domain: str, limit: int = 100) -> Dict[str, Any]:
        result = {
            "domain": domain,
            "urls": [],
            "total": 0,
            "interesting": [],
            "error": None,
        }

        interesting_patterns = [
            "/admin", "/login", "/api/", "/backup", "/.git", "/config",
            "/upload", "/password", "/.env", "/wp-admin", "/phpmyadmin",
            "/swagger", "/docs", "/debug", "token=", "key=", "secret=",
        ]

        try:
            params = {
                "url": f"*.{domain}/*",
                "output": "json",
                "limit": limit,
                "fl": "original",
                "collapse": "urlkey",
                "filter": "statuscode:200",
            }
            r = requests.get(self.CDX_URL, params=params, timeout=25)

            if r.status_code != 200:
                result["error"] = f"CDX API returned {r.status_code}"
                return result

            rows = r.json()
            if not rows or len(rows) < 2:
                result["error"] = "No archived URLs found"
                return result

            urls = [row[0] for row in rows[1:] if row]
            result["urls"] = urls
            result["total"] = len(urls)

            for url in urls:
                url_lower = url.lower()
                for pat in interesting_patterns:
                    if pat in url_lower:
                        result["interesting"].append(url)
                        break

        except Exception as e:
            result["error"] = str(e)

        return result

    def check_availability(self, url: str) -> Dict[str, Any]:
        result = {"url": url, "available": False, "closest_snapshot": None, "error": None}
        try:
            r = requests.get(
                self.AVAILABILITY_URL,
                params={"url": url},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                closest = data.get("archived_snapshots", {}).get("closest", {})
                if closest.get("available"):
                    result["available"] = True
                    result["closest_snapshot"] = closest.get("url")
            else:
                result["error"] = f"API returned {r.status_code}"
        except Exception as e:
            result["error"] = str(e)
        return result

    def print_snapshots(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Wayback Machine: {result['url']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        print(f"{Colors.YELLOW}Snapshots Found:{Colors.RESET} {result['total_snapshots']}")
        if result["first_snapshot"]:
            print(f"{Colors.YELLOW}First Archived:{Colors.RESET} {result['first_snapshot']}")
            print(f"{Colors.YELLOW}Latest Snapshot:{Colors.RESET} {result['last_snapshot']}")

        if result["snapshots"]:
            print(f"\n{Colors.BOLD}Recent Snapshots:{Colors.RESET}")
            for s in result["snapshots"][:10]:
                size_str = f" ({s['size']//1024}KB)" if s["size"] > 0 else ""
                print(f"  {Colors.GREEN}[{s['date']}]{Colors.RESET} {s['wayback_url']}{size_str}")

    def print_urls(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Wayback URL Harvest: {result['domain']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        print(f"{Colors.YELLOW}Total Unique URLs Archived:{Colors.RESET} {result['total']}")

        if result["interesting"]:
            print(f"\n{Colors.RED}⚠ Potentially Sensitive URLs:{Colors.RESET}")
            for url in result["interesting"][:20]:
                print(f"  {Colors.RED}[!]{Colors.RESET} {url}")

        if result["urls"]:
            print(f"\n{Colors.BOLD}Sample URLs:{Colors.RESET}")
            for url in result["urls"][:15]:
                print(f"  {Colors.CYAN}•{Colors.RESET} {url}")

def run_wayback():
    print(f"\n{Colors.BOLD}Wayback Machine{Colors.RESET}")
    print(f"  {Colors.GREEN}1.{Colors.RESET} View historical snapshots")
    print(f"  {Colors.GREEN}2.{Colors.RESET} Harvest all archived URLs (useful for recon)")

    choice = input(f"\n{Colors.GREEN}Select (1/2): {Colors.RESET}").strip()
    target = input(f"{Colors.GREEN}Enter URL or domain: {Colors.RESET}").strip()
    if not target:
        return None

    wb = WaybackMachine()
    if choice == "2":
        print(f"{Colors.CYAN}Harvesting URLs from Wayback...{Colors.RESET}")
        result = wb.get_all_urls(target)
        wb.print_urls(result)
        return result
    else:
        print(f"{Colors.CYAN}Fetching snapshots...{Colors.RESET}")
        result = wb.get_snapshots(target)
        wb.print_snapshots(result)
        return result
