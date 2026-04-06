import socket
import requests
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
sys.path.append('..')
from config import IPINFO_API_KEY, Colors

try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

class WhoisLookup:

    def lookup(self, domain: str) -> Dict[str, Any]:
        result = {
            "domain": domain,
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "updated_date": None,
            "name_servers": [],
            "status": [],
            "emails": [],
            "org": None,
            "country": None,
            "error": None
        }

        if not WHOIS_AVAILABLE:
            result["error"] = "python-whois not installed. Run: pip install python-whois"
            return result

        try:
            w = whois.whois(domain)

            result["registrar"] = w.registrar
            result["org"] = w.org
            result["country"] = w.country

            if w.creation_date:
                cd = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
                result["creation_date"] = cd.isoformat() if hasattr(cd, 'isoformat') else str(cd)

            if w.expiration_date:
                ed = w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
                result["expiration_date"] = ed.isoformat() if hasattr(ed, 'isoformat') else str(ed)

            if w.updated_date:
                ud = w.updated_date[0] if isinstance(w.updated_date, list) else w.updated_date
                result["updated_date"] = ud.isoformat() if hasattr(ud, 'isoformat') else str(ud)

            if w.name_servers:
                ns = w.name_servers if isinstance(w.name_servers, list) else [w.name_servers]
                result["name_servers"] = [str(n).lower() for n in ns if n]

            if w.status:
                status = w.status if isinstance(w.status, list) else [w.status]
                result["status"] = [str(s) for s in status if s]

            if w.emails:
                emails = w.emails if isinstance(w.emails, list) else [w.emails]
                result["emails"] = [e for e in emails if e]

        except Exception as e:
            result["error"] = str(e)

        return result

    def print_result(self, result: Dict):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}WHOIS Lookup: {result['domain']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        print(f"{Colors.YELLOW}Registrar:{Colors.RESET} {result.get('registrar', 'N/A')}")
        print(f"{Colors.YELLOW}Organization:{Colors.RESET} {result.get('org', 'N/A')}")
        print(f"{Colors.YELLOW}Country:{Colors.RESET} {result.get('country', 'N/A')}")
        print(f"{Colors.YELLOW}Created:{Colors.RESET} {result.get('creation_date', 'N/A')}")
        print(f"{Colors.YELLOW}Expires:{Colors.RESET} {result.get('expiration_date', 'N/A')}")
        print(f"{Colors.YELLOW}Updated:{Colors.RESET} {result.get('updated_date', 'N/A')}")

        if result.get("name_servers"):
            print(f"{Colors.YELLOW}Name Servers:{Colors.RESET}")
            for ns in result["name_servers"]:
                print(f"  • {ns}")

        if result.get("emails"):
            print(f"{Colors.YELLOW}Contact Emails:{Colors.RESET}")
            for email in result["emails"]:
                print(f"  • {email}")

class GeoIPLookup:

    def __init__(self):
        self.api_key = IPINFO_API_KEY

    def lookup(self, ip_or_domain: str) -> Dict[str, Any]:
        result = {
            "query": ip_or_domain,
            "ip": None,
            "hostname": None,
            "city": None,
            "region": None,
            "country": None,
            "country_name": None,
            "loc": None,
            "org": None,
            "asn": None,
            "timezone": None,
            "postal": None,
            "error": None
        }

        try:
            ip = socket.gethostbyname(ip_or_domain)
            result["ip"] = ip
        except socket.gaierror:
            result["ip"] = ip_or_domain

        try:
            url = f"https://ipinfo.io/{result['ip']}/json"
            params = {}
            if self.api_key:
                params["token"] = self.api_key

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                result.update({
                    "ip": data.get("ip"),
                    "hostname": data.get("hostname"),
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country"),
                    "loc": data.get("loc"),
                    "org": data.get("org"),
                    "timezone": data.get("timezone"),
                    "postal": data.get("postal")
                })

                country_code = data.get("country")
                if country_code:
                    result["country_name"] = self._get_country_name(country_code)

            else:
                result["error"] = f"API returned status {response.status_code}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def _get_country_name(self, code: str) -> str:
        countries = {
            "US": "United States", "GB": "United Kingdom", "RU": "Russia",
            "DE": "Germany", "FR": "France", "CN": "China", "JP": "Japan",
            "IN": "India", "BR": "Brazil", "CA": "Canada", "AU": "Australia",
            "UA": "Ukraine", "PL": "Poland", "NL": "Netherlands", "IT": "Italy"
        }
        return countries.get(code, code)

    def print_result(self, result: Dict):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}GeoIP Lookup: {result['query']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        print(f"{Colors.YELLOW}IP:{Colors.RESET} {result.get('ip', 'N/A')}")
        print(f"{Colors.YELLOW}Hostname:{Colors.RESET} {result.get('hostname', 'N/A')}")
        print(f"{Colors.YELLOW}Location:{Colors.RESET} {result.get('city', 'N/A')}, {result.get('region', 'N/A')}")
        print(f"{Colors.YELLOW}Country:{Colors.RESET} {result.get('country_name', result.get('country', 'N/A'))}")
        print(f"{Colors.YELLOW}Coordinates:{Colors.RESET} {result.get('loc', 'N/A')}")
        print(f"{Colors.YELLOW}Organization:{Colors.RESET} {result.get('org', 'N/A')}")
        print(f"{Colors.YELLOW}Timezone:{Colors.RESET} {result.get('timezone', 'N/A')}")
        print(f"{Colors.YELLOW}Postal Code:{Colors.RESET} {result.get('postal', 'N/A')}")

class DNSLookup:

    RECORD_TYPES = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA', 'PTR']

    def lookup(self, domain: str, record_types: List[str] = None) -> Dict[str, Any]:
        if record_types is None:
            record_types = self.RECORD_TYPES

        result = {
            "domain": domain,
            "records": {},
            "error": None
        }

        if not DNS_AVAILABLE:
            result["error"] = "dnspython not installed. Run: pip install dnspython"
            return result

        for rtype in record_types:
            try:
                answers = dns.resolver.resolve(domain, rtype)
                result["records"][rtype] = []

                for rdata in answers:
                    if rtype == 'MX':
                        result["records"][rtype].append({
                            "priority": rdata.preference,
                            "host": str(rdata.exchange).rstrip('.')
                        })
                    elif rtype == 'SOA':
                        result["records"][rtype].append({
                            "mname": str(rdata.mname),
                            "rname": str(rdata.rname),
                            "serial": rdata.serial
                        })
                    else:
                        result["records"][rtype].append(str(rdata).strip('"'))

            except dns.resolver.NoAnswer:
                pass
            except dns.resolver.NXDOMAIN:
                result["error"] = "Domain does not exist"
                break
            except dns.exception.Timeout:
                result["error"] = "DNS query timeout"
            except Exception:
                pass

        return result

    def print_result(self, result: Dict):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}DNS Lookup: {result['domain']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        for rtype, records in result.get("records", {}).items():
            if records:
                print(f"\n{Colors.YELLOW}{rtype} Records:{Colors.RESET}")
                for r in records:
                    if isinstance(r, dict):
                        if 'priority' in r:
                            print(f"  [{r['priority']}] {r['host']}")
                        else:
                            print(f"  {r}")
                    else:
                        print(f"  • {r}")

class WebsiteAnalyzer:

    def analyze(self, url: str) -> Dict[str, Any]:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        result = {
            "url": url,
            "title": None,
            "description": None,
            "technologies": [],
            "social_links": [],
            "emails": [],
            "phones": [],
            "headers": {},
            "error": None
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            html = response.text

            result["headers"] = {
                "server": response.headers.get("Server"),
                "x-powered-by": response.headers.get("X-Powered-By"),
                "content-type": response.headers.get("Content-Type")
            }

            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            if title_match:
                result["title"] = title_match.group(1).strip()

            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
            if desc_match:
                result["description"] = desc_match.group(1).strip()

            result["technologies"] = self._detect_technologies(html, response.headers)

            result["social_links"] = self._extract_social_links(html)

            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            result["emails"] = list(set(re.findall(email_pattern, html)))[:10]

            phone_pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}'
            phones = re.findall(phone_pattern, html)
            result["phones"] = list(set([p for p in phones if len(p) >= 10]))[:10]

        except Exception as e:
            result["error"] = str(e)

        return result

    def _detect_technologies(self, html: str, headers) -> List[str]:
        techs = []

        server = headers.get("Server", "").lower()
        powered = headers.get("X-Powered-By", "").lower()

        if "nginx" in server:
            techs.append("Nginx")
        if "apache" in server:
            techs.append("Apache")
        if "cloudflare" in server:
            techs.append("Cloudflare")
        if "php" in powered:
            techs.append("PHP")
        if "asp.net" in powered:
            techs.append("ASP.NET")

        patterns = {
            "WordPress": [r'wp-content', r'wp-includes', r'wordpress'],
            "React": [r'react', r'_reactRootContainer'],
            "Vue.js": [r'vue\.js', r'v-bind', r'v-on'],
            "Angular": [r'ng-app', r'angular\.js', r'ng-version'],
            "jQuery": [r'jquery\.js', r'jquery\.min\.js'],
            "Bootstrap": [r'bootstrap\.css', r'bootstrap\.min\.js'],
            "Tailwind": [r'tailwindcss', r'tailwind\.css'],
            "Laravel": [r'laravel', r'csrf-token'],
            "Django": [r'csrfmiddlewaretoken', r'django'],
            "Shopify": [r'cdn\.shopify', r'shopify'],
            "Wix": [r'wix\.com', r'wixstatic'],
            "Squarespace": [r'squarespace'],
            "Google Analytics": [r'google-analytics\.com', r'gtag', r'ga\.js'],
            "Google Tag Manager": [r'googletagmanager\.com'],
        }

        html_lower = html.lower()
        for tech, pats in patterns.items():
            for pat in pats:
                if re.search(pat, html_lower):
                    if tech not in techs:
                        techs.append(tech)
                    break

        return techs

    def _extract_social_links(self, html: str) -> List[Dict]:
        social_patterns = {
            "Twitter/X": r'https?://(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)',
            "Facebook": r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)',
            "Instagram": r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)',
            "LinkedIn": r'https?://(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)',
            "YouTube": r'https?://(?:www\.)?youtube\.com/(?:channel|user|c)/([a-zA-Z0-9_-]+)',
            "GitHub": r'https?://(?:www\.)?github\.com/([a-zA-Z0-9_-]+)',
            "Telegram": r'https?://(?:www\.)?t\.me/([a-zA-Z0-9_]+)',
            "TikTok": r'https?://(?:www\.)?tiktok\.com/@([a-zA-Z0-9_.]+)',
        }

        links = []
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, html)
            for match in set(matches):
                if match and match not in ('share', 'intent', 'sharer'):
                    links.append({"platform": platform, "username": match})

        return links[:20]

    def print_result(self, result: Dict):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Website Analysis: {result['url']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        print(f"{Colors.YELLOW}Title:{Colors.RESET} {result.get('title', 'N/A')}")
        print(f"{Colors.YELLOW}Description:{Colors.RESET} {(result.get('description', 'N/A') or 'N/A')[:100]}")

        if result.get("technologies"):
            print(f"\n{Colors.YELLOW}Technologies Detected:{Colors.RESET}")
            for tech in result["technologies"]:
                print(f"  • {tech}")

        if result.get("social_links"):
            print(f"\n{Colors.YELLOW}Social Links:{Colors.RESET}")
            for link in result["social_links"]:
                print(f"  • {link['platform']}: @{link['username']}")

        if result.get("emails"):
            print(f"\n{Colors.YELLOW}Emails Found:{Colors.RESET}")
            for email in result["emails"][:5]:
                print(f"  • {email}")

        if result.get("phones"):
            print(f"\n{Colors.YELLOW}Phones Found:{Colors.RESET}")
            for phone in result["phones"][:5]:
                print(f"  • {phone}")

def run_whois():
    whois_lookup = WhoisLookup()
    print(f"\n{Colors.BOLD}WHOIS Lookup{Colors.RESET}")
    domain = input(f"{Colors.GREEN}Enter domain: {Colors.RESET}").strip()
    if domain:
        result = whois_lookup.lookup(domain)
        whois_lookup.print_result(result)
        return result
    return None

def run_geoip():
    geoip = GeoIPLookup()
    print(f"\n{Colors.BOLD}GeoIP Lookup{Colors.RESET}")
    target = input(f"{Colors.GREEN}Enter IP or domain: {Colors.RESET}").strip()
    if target:
        result = geoip.lookup(target)
        geoip.print_result(result)
        return result
    return None

def run_dns():
    dns_lookup = DNSLookup()
    print(f"\n{Colors.BOLD}DNS Lookup{Colors.RESET}")
    domain = input(f"{Colors.GREEN}Enter domain: {Colors.RESET}").strip()
    if domain:
        result = dns_lookup.lookup(domain)
        dns_lookup.print_result(result)
        return result
    return None

def run_website_analysis():
    analyzer = WebsiteAnalyzer()
    print(f"\n{Colors.BOLD}Website Analysis{Colors.RESET}")
    url = input(f"{Colors.GREEN}Enter URL: {Colors.RESET}").strip()
    if url:
        result = analyzer.analyze(url)
        analyzer.print_result(result)
        return result
    return None

if __name__ == "__main__":
    run_whois()
