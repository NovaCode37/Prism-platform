import asyncio
import aiohttp
import json
import csv
import os
import html as _html
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import sys
sys.path.append('..')
from config import OUTPUT_DIR, Colors

@dataclass
class SiteResult:
    site: str
    url: str
    status: str
    http_code: int = 0
    response_time: float = 0.0

class Blackbird:
    
    SITES = {
        "GitHub": ("https://github.com/{}", "status", 404),
        "Twitter/X": ("https://x.com/{}", "status", 404),
        "Instagram": ("https://www.instagram.com/{}/", "status", 404),
        "TikTok": ("https://www.tiktok.com/@{}", "text", "couldn't find this account"),
        "Reddit": ("https://www.reddit.com/user/{}", "status", 404),
        "YouTube": ("https://www.youtube.com/@{}", "status", 404),
        "Twitch": ("https://www.twitch.tv/{}", "text", "Sorry. Unless you've got a time machine"),
        "Pinterest": ("https://www.pinterest.com/{}/", "status", 404),
        "LinkedIn": ("https://www.linkedin.com/in/{}", "status", 404),
        "Telegram": ("https://t.me/{}", "text", "If you have <strong>Telegram</strong>"),
        "VK": ("https://vk.com/{}", "text", "Страница удалена"),
        "Steam": ("https://steamcommunity.com/id/{}", "text", "The specified profile could not be found"),
        "Spotify": ("https://open.spotify.com/user/{}", "status", 404),
        "SoundCloud": ("https://soundcloud.com/{}", "status", 404),
        "Medium": ("https://medium.com/@{}", "status", 404),
        "Dev.to": ("https://dev.to/{}", "status", 404),
        "GitLab": ("https://gitlab.com/{}", "status", 404),
        "Bitbucket": ("https://bitbucket.org/{}/", "status", 404),
        "HackerNews": ("https://news.ycombinator.com/user?id={}", "text", "No such user"),
        "Keybase": ("https://keybase.io/{}", "status", 404),
        "Patreon": ("https://www.patreon.com/{}", "status", 404),
        "Tumblr": ("https://{}.tumblr.com/", "status", 404),
        "Flickr": ("https://www.flickr.com/people/{}", "status", 404),
        "Behance": ("https://www.behance.net/{}", "status", 404),
        "Dribbble": ("https://dribbble.com/{}", "status", 404),
        "500px": ("https://500px.com/p/{}", "status", 404),
        "Imgur": ("https://imgur.com/user/{}", "status", 404),
        "ProductHunt": ("https://www.producthunt.com/@{}", "status", 404),
        "AngelList": ("https://angel.co/u/{}", "status", 404),
        "About.me": ("https://about.me/{}", "status", 404),
        "Gravatar": ("https://gravatar.com/{}", "status", 404),
        "Disqus": ("https://disqus.com/by/{}/", "status", 404),
        "Fiverr": ("https://www.fiverr.com/{}", "status", 404),
        "Freelancer": ("https://www.freelancer.com/u/{}", "status", 404),
        "Replit": ("https://replit.com/@{}", "status", 404),
        "CodePen": ("https://codepen.io/{}", "status", 404),
        "HackerRank": ("https://www.hackerrank.com/{}", "status", 404),
        "LeetCode": ("https://leetcode.com/{}", "status", 404),
        "Kaggle": ("https://www.kaggle.com/{}", "status", 404),
        "Trello": ("https://trello.com/{}", "status", 404),
        "Duolingo": ("https://www.duolingo.com/profile/{}", "status", 404),
        "Chess.com": ("https://www.chess.com/member/{}", "status", 404),
        "Lichess": ("https://lichess.org/@/{}", "status", 404),
        "Roblox": ("https://www.roblox.com/users/profile?username={}", "text", "Page cannot be found"),
        "Minecraft": ("https://namemc.com/profile/{}", "status", 404),
        "Xbox": ("https://xboxgamertag.com/search/{}", "status", 404),
        "PSN": ("https://psnprofiles.com/{}", "status", 404),
        "Pornhub": ("https://www.pornhub.com/users/{}", "status", 404),
        "OnlyFans": ("https://onlyfans.com/{}", "status", 404),
    }
    
    def __init__(self, timeout: int = 10, max_concurrent: int = 20):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.results: List[SiteResult] = []
        
    async def check_site(self, session: aiohttp.ClientSession, username: str, 
                         site: str, config: tuple) -> SiteResult:
        url_template, error_type, error_indicator = config
        url = url_template.format(username)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with session.get(url, allow_redirects=True) as response:
                response_time = asyncio.get_event_loop().time() - start_time
                http_code = response.status
                
                if error_type == "status":
                    if http_code == error_indicator or http_code >= 400:
                        status = "not_found"
                    else:
                        status = "found"
                else:
                    try:
                        text = await response.text()
                        if error_indicator.lower() in text.lower():
                            status = "not_found"
                        else:
                            status = "found" if http_code == 200 else "not_found"
                    except:
                        status = "error"
                
                return SiteResult(site, url, status, http_code, response_time)
                
        except asyncio.TimeoutError:
            return SiteResult(site, url, "timeout", 0, self.timeout)
        except Exception as e:
            return SiteResult(site, url, "error", 0, 0)
    
    async def search(self, username: str, sites: List[str] = None) -> List[SiteResult]:
        self.results = []
        
        if sites is None:
            sites_to_check = self.SITES
        else:
            sites_to_check = {k: v for k, v in self.SITES.items() if k in sites}
        
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers) as session:
            tasks = [
                self.check_site(session, username, site, config) 
                for site, config in sites_to_check.items()
            ]
            self.results = await asyncio.gather(*tasks)
        
        return self.results
    
    def get_found(self) -> List[SiteResult]:
        return [r for r in self.results if r.status == "found"]
    
    def export_json(self, username: str, filepath: str = None) -> str:
        if filepath is None:
            filepath = os.path.join(OUTPUT_DIR, f"blackbird_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        data = {
            "username": username,
            "timestamp": datetime.now().isoformat(),
            "total_checked": len(self.results),
            "total_found": len(self.get_found()),
            "results": [
                {
                    "site": r.site,
                    "url": r.url,
                    "status": r.status,
                    "http_code": r.http_code,
                    "response_time": round(r.response_time, 3)
                }
                for r in self.results
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def export_csv(self, username: str, filepath: str = None) -> str:
        if filepath is None:
            filepath = os.path.join(OUTPUT_DIR, f"blackbird_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Site", "URL", "Status", "HTTP Code", "Response Time (s)"])
            for r in self.results:
                writer.writerow([r.site, r.url, r.status, r.http_code, round(r.response_time, 3)])
        
        return filepath
    
    def export_html(self, username: str, filepath: str = None) -> str:
        if filepath is None:
            filepath = os.path.join(OUTPUT_DIR, f"blackbird_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        
        found = self.get_found()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Blackbird Report - {username}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
        h1 {{ color: #00d4ff; }}
        .stats {{ background: #16213e; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #0f3460; color: #00d4ff; }}
        tr:hover {{ background: #16213e; }}
        .found {{ color: #00ff88; font-weight: bold; }}
        .not_found {{ color: #666; }}
        .error {{ color: #ff6b6b; }}
        .timeout {{ color: #ffa500; }}
        a {{ color: #00d4ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>🔍 Blackbird Report</h1>
    <div class="stats">
        <p><strong>Username:</strong> {username}</p>
        <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Sites Checked:</strong> {len(self.results)}</p>
        <p><strong>Accounts Found:</strong> {len(found)}</p>
    </div>
    <table>
        <tr><th>Site</th><th>URL</th><th>Status</th><th>Response Time</th></tr>
"""
        
        for r in sorted(self.results, key=lambda x: (x.status != "found", x.site)):
            status_class = _html.escape(r.status)
            safe_site = _html.escape(r.site)
            safe_url = _html.escape(r.url)
            url_link = f'<a href="{safe_url}" target="_blank">{safe_url}</a>' if r.status == "found" else safe_url
            html += f'        <tr><td>{safe_site}</td><td>{url_link}</td><td class="{status_class}">{r.status.upper()}</td><td>{r.response_time:.2f}s</td></tr>\n'
        
        html += """    </table>
</body>
</html>"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return filepath
    
    def export_txt(self, username: str, filepath: str = None) -> str:
        if filepath is None:
            filepath = os.path.join(OUTPUT_DIR, f"blackbird_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        found = self.get_found()
        
        lines = [
            f"Blackbird Report - Username: {username}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Sites Checked: {len(self.results)}",
            f"Accounts Found: {len(found)}",
            "",
            "=" * 60,
            "FOUND ACCOUNTS:",
            "=" * 60,
        ]
        
        for r in found:
            lines.append(f"[+] {r.site}: {r.url}")
        
        lines.extend(["", "=" * 60, "ALL RESULTS:", "=" * 60])
        
        for r in self.results:
            status_symbol = "+" if r.status == "found" else "-" if r.status == "not_found" else "?" if r.status == "error" else "!"
            lines.append(f"[{status_symbol}] {r.site}: {r.status} ({r.response_time:.2f}s)")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return filepath
    
    def print_results(self, username: str):
        found = self.get_found()
        
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Blackbird Username Search: {username}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.YELLOW}Sites Checked:{Colors.RESET} {len(self.results)}")
        print(f"{Colors.YELLOW}Accounts Found:{Colors.RESET} {Colors.GREEN}{len(found)}{Colors.RESET}")
        
        if found:
            print(f"\n{Colors.BOLD}Found Accounts:{Colors.RESET}")
            for r in found:
                print(f"  {Colors.GREEN}[+]{Colors.RESET} {r.site}: {Colors.CYAN}{r.url}{Colors.RESET}")
        
        errors = [r for r in self.results if r.status in ("error", "timeout")]
        if errors:
            print(f"\n{Colors.YELLOW}Errors/Timeouts: {len(errors)}{Colors.RESET}")

def run_blackbird():
    print(f"\n{Colors.BOLD}Blackbird - Username Search{Colors.RESET}")
    username = input(f"{Colors.GREEN}Enter username to search: {Colors.RESET}").strip()
    
    if not username:
        print(f"{Colors.RED}No username provided{Colors.RESET}")
        return None
    
    print(f"\n{Colors.CYAN}Searching for '{username}' across {len(Blackbird.SITES)} sites...{Colors.RESET}")
    
    bb = Blackbird(timeout=10, max_concurrent=25)
    asyncio.run(bb.search(username))
    bb.print_results(username)
    
    export = input(f"\n{Colors.GREEN}Export results? (json/csv/html/txt/all/no): {Colors.RESET}").strip().lower()
    
    if export and export != "no":
        exports = []
        if export == "all":
            exports = ["json", "csv", "html", "txt"]
        else:
            exports = [export]
        
        for fmt in exports:
            if fmt == "json":
                path = bb.export_json(username)
            elif fmt == "csv":
                path = bb.export_csv(username)
            elif fmt == "html":
                path = bb.export_html(username)
            elif fmt == "txt":
                path = bb.export_txt(username)
            else:
                continue
            print(f"{Colors.GREEN}Exported to:{Colors.RESET} {path}")
    
    return bb.results

if __name__ == "__main__":
    run_blackbird()
