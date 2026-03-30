import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import print_banner, Colors, OUTPUT_DIR
from modules.hlr_lookup import HLRLookup, run_hlr_lookup
from modules.hunter import HunterIO, run_hunter_domain, run_hunter_email
from modules.blackbird import Blackbird, run_blackbird
from modules.maigret_wrapper import MaigretWrapper, run_maigret
from modules.leak_lookup import LeakLookup, run_leak_lookup
from modules.smtp_verify import SMTPVerifier, run_smtp_verify
from modules.extra_tools import (
    WhoisLookup, run_whois,
    GeoIPLookup, run_geoip,
    DNSLookup, run_dns,
    WebsiteAnalyzer, run_website_analysis,
)
from modules.cert_transparency import CertTransparency, run_cert_transparency
from modules.threat_intel import run_threat_intel
from modules.wayback import WaybackMachine, run_wayback
from modules.shodan_lookup import ShodanLookup, run_shodan
from modules.opsec_score import score_from_results
from modules.report_generator import generate_html_report

class OSINTToolkit:
    
    MENU_OPTIONS = {
        "1": ("HLR Lookup", "Check mobile number activity", run_hlr_lookup),
        "2": ("Hunter Domain", "Find emails on a domain", run_hunter_domain),
        "3": ("Hunter Email", "Find email by name + domain", run_hunter_email),
        "4": ("Blackbird", "Username search (fast, 50+ sites)", run_blackbird),
        "5": ("Maigret", "Username search (deep, 3000+ sites)", run_maigret),
        "6": ("Leak Lookup", "Check data breaches", run_leak_lookup),
        "7": ("SMTP Verify", "Verify email existence", run_smtp_verify),
        "8": ("WHOIS", "Domain registration info", run_whois),
        "9": ("GeoIP", "IP/Domain geolocation", run_geoip),
        "10": ("DNS Lookup", "DNS records", run_dns),
        "11": ("Website Analysis", "Tech stack & social links", run_website_analysis),
        "12": ("Cert Transparency", "Subdomain discovery via crt.sh", run_cert_transparency),
        "13": ("Threat Intel", "VirusTotal + AbuseIPDB reputation", run_threat_intel),
        "14": ("Wayback Machine", "Historical snapshots & URL harvest", run_wayback),
        "15": ("Shodan", "Open ports, CVEs, host fingerprinting", run_shodan),
        "16": ("OPSEC Score", "Run full scan & score security posture", None),
        "w": ("Web Dashboard", "Launch browser-based dashboard", None),
        "0": ("Exit", "Exit the toolkit", None),
    }
    
    def __init__(self):
        self.results_history = []
    
    def display_menu(self):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}OSINT Toolkit v2.0 - Main Menu{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        print(f"\n{Colors.YELLOW}Phone & Email:{Colors.RESET}")
        print(f"  {Colors.GREEN}1.{Colors.RESET}  HLR Lookup      - Mobile number check")
        print(f"  {Colors.GREEN}7.{Colors.RESET}  SMTP Verify     - Email existence check")

        print(f"\n{Colors.YELLOW}Email Intelligence:{Colors.RESET}")
        print(f"  {Colors.GREEN}2.{Colors.RESET}  Hunter Domain   - Find all emails on domain")
        print(f"  {Colors.GREEN}3.{Colors.RESET}  Hunter Email    - Find email by name")
        print(f"  {Colors.GREEN}6.{Colors.RESET}  Leak Lookup     - Check data breaches")

        print(f"\n{Colors.YELLOW}Username OSINT:{Colors.RESET}")
        print(f"  {Colors.GREEN}4.{Colors.RESET}  Blackbird       - Fast username search (50+ sites)")
        print(f"  {Colors.GREEN}5.{Colors.RESET}  Maigret         - Deep username search (3000+ sites)")

        print(f"\n{Colors.YELLOW}Domain & IP:{Colors.RESET}")
        print(f"  {Colors.GREEN}8.{Colors.RESET}  WHOIS           - Domain registration info")
        print(f"  {Colors.GREEN}9.{Colors.RESET}  GeoIP           - IP/Domain geolocation")
        print(f"  {Colors.GREEN}10.{Colors.RESET} DNS Lookup      - DNS records")
        print(f"  {Colors.GREEN}11.{Colors.RESET} Website Analysis- Tech stack & social links")
        print(f"  {Colors.GREEN}12.{Colors.RESET} Cert Transparency - Subdomain discovery")
        print(f"  {Colors.GREEN}14.{Colors.RESET} Wayback Machine - Historical snapshots & URL harvest")

        print(f"\n{Colors.YELLOW}Threat Intelligence:{Colors.RESET}")
        print(f"  {Colors.GREEN}13.{Colors.RESET} Threat Intel   - VirusTotal + AbuseIPDB")
        print(f"  {Colors.GREEN}15.{Colors.RESET} Shodan         - Open ports & CVEs")

        print(f"\n{Colors.YELLOW}Analysis & Reporting:{Colors.RESET}")
        print(f"  {Colors.GREEN}16.{Colors.RESET} OPSEC Score    - Full scan & security posture report")

        print(f"\n{Colors.YELLOW}Web Dashboard:{Colors.RESET}")
        print(f"  {Colors.MAGENTA}w.{Colors.RESET}  Web Dashboard  - Launch browser UI at http://localhost:8080")

        print(f"\n{Colors.RED}  0. Exit{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    
    def run(self):
        print_banner()
        
        while True:
            self.display_menu()
            
            choice = input(f"\n{Colors.GREEN}Select option: {Colors.RESET}").strip()
            
            if choice == "0":
                print(f"\n{Colors.CYAN}Goodbye!{Colors.RESET}\n")
                break
            
            if choice == "w":
                print(f"\n{Colors.CYAN}Starting web dashboard...{Colors.RESET}")
                print(f"{Colors.GREEN}Open your browser at: http://localhost:8080{Colors.RESET}")
                try:
                    import subprocess
                    subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "web.app:app",
                         "--host", "0.0.0.0", "--port", "8080"],
                        cwd=os.path.dirname(os.path.abspath(__file__))
                    )
                    import time
                    time.sleep(2)
                    import webbrowser
                    webbrowser.open("http://localhost:8080")
                except Exception as e:
                    print(f"{Colors.RED}Failed to start web dashboard: {e}{Colors.RESET}")
                    print(f"Run manually: python -m uvicorn web.app:app --port 8080")
            elif choice == "16":
                self._run_opsec_score()
            elif choice in self.MENU_OPTIONS:
                name, desc, func = self.MENU_OPTIONS[choice]
                if func:
                    try:
                        result = func()
                        if result:
                            self.results_history.append({
                                "tool": name,
                                "timestamp": datetime.now().isoformat(),
                                "result": result
                            })
                    except KeyboardInterrupt:
                        print(f"\n{Colors.YELLOW}Operation cancelled{Colors.RESET}")
                    except Exception as e:
                        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
            else:
                print(f"{Colors.RED}Invalid option{Colors.RESET}")
            
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
    
    def _run_opsec_score(self):
        target = input(f"\n{Colors.GREEN}Enter target (domain/email/username): {Colors.RESET}").strip()
        if not target:
            return

        all_results = {}
        scan_type = "auto"
        if "@" in target:
            scan_type = "email"
        elif "." in target:
            scan_type = "domain"
        else:
            scan_type = "username"

        print(f"\n{Colors.CYAN}Running full OPSEC scan for: {target} (type: {scan_type}){Colors.RESET}\n")

        if scan_type == "domain":
            print(f"{Colors.YELLOW}[1/7] WHOIS...{Colors.RESET}")
            all_results["whois"] = WhoisLookup().lookup(target)
            print(f"{Colors.YELLOW}[2/7] DNS...{Colors.RESET}")
            all_results["dns"] = DNSLookup().lookup(target)
            print(f"{Colors.YELLOW}[3/7] GeoIP...{Colors.RESET}")
            all_results["geoip"] = GeoIPLookup().lookup(target)
            print(f"{Colors.YELLOW}[4/7] Certificate Transparency...{Colors.RESET}")
            all_results["cert_transparency"] = CertTransparency().search(target)
            print(f"{Colors.YELLOW}[5/7] Website Analysis...{Colors.RESET}")
            all_results["website"] = WebsiteAnalyzer().analyze(target)
            print(f"{Colors.YELLOW}[6/7] Wayback Machine...{Colors.RESET}")
            all_results["wayback"] = WaybackMachine().get_all_urls(target, limit=50)
            print(f"{Colors.YELLOW}[7/7] Hunter.io...{Colors.RESET}")
            from modules.hunter import HunterIO
            all_results["hunter"] = HunterIO().domain_search(target)

        elif scan_type == "email":
            print(f"{Colors.YELLOW}[1/2] SMTP Verify...{Colors.RESET}")
            all_results["smtp"] = SMTPVerifier().verify_email(target)
            print(f"{Colors.YELLOW}[2/2] Leak Lookup...{Colors.RESET}")
            all_results["breaches"] = LeakLookup().check_email_full(target)

        elif scan_type == "username":
            import asyncio
            print(f"{Colors.YELLOW}[1/1] Blackbird username search...{Colors.RESET}")
            bb = Blackbird(timeout=10, max_concurrent=25)
            asyncio.run(bb.search(target))
            all_results["blackbird"] = [
                {"site": r.site, "url": r.url, "status": r.status} for r in bb.results
            ]

        print(f"\n{Colors.CYAN}Calculating OPSEC score...{Colors.RESET}")
        opsec = score_from_results(all_results)

        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.findings = opsec["all_findings"]
        scorer.category_scores = {
            k: {"score": v["score"], "max": v["max"], "findings": v["findings"]}
            for k, v in opsec["categories"].items()
        }
        scorer.print_report(opsec)

        save = input(f"\n{Colors.GREEN}Generate HTML report? (y/n): {Colors.RESET}").strip().lower()
        if save == "y":
            path = generate_html_report(target, scan_type, all_results, opsec)
            print(f"{Colors.GREEN}Report saved: {path}{Colors.RESET}")

        return opsec

    def export_session(self, filepath: str = None):
        if not self.results_history:
            print(f"{Colors.YELLOW}No results to export{Colors.RESET}")
            return
        
        if filepath is None:
            filepath = os.path.join(
                OUTPUT_DIR, 
                f"osint_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results_history, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"{Colors.GREEN}Session exported to:{Colors.RESET} {filepath}")

def quick_scan(target: str, scan_type: str = "auto"):
    print_banner()
    print(f"\n{Colors.CYAN}Quick Scan: {target}{Colors.RESET}")
    
    results = {}
    
    if scan_type == "auto":
        if "@" in target:
            scan_type = "email"
        elif target.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            scan_type = "phone"
        elif "." in target and not "@" in target:
            scan_type = "domain"
        else:
            scan_type = "username"
    
    print(f"{Colors.YELLOW}Detected type: {scan_type}{Colors.RESET}\n")
    
    if scan_type == "email":
        print(f"{Colors.CYAN}[1/3] Checking SMTP...{Colors.RESET}")
        smtp = SMTPVerifier()
        results["smtp"] = smtp.verify_email(target)
        smtp.print_result(results["smtp"])
        
        print(f"\n{Colors.CYAN}[2/3] Checking breaches...{Colors.RESET}")
        leak = LeakLookup()
        results["breaches"] = leak.check_email_full(target)
        leak.print_result(results["breaches"], "email")
        
        print(f"\n{Colors.CYAN}[3/3] Hunter verification...{Colors.RESET}")
        hunter = HunterIO()
        results["hunter"] = hunter.email_verifier(target)
        
    elif scan_type == "phone":
        print(f"{Colors.CYAN}[1/1] HLR Lookup...{Colors.RESET}")
        hlr = HLRLookup()
        results["hlr"] = hlr.validate_phone(target)
        hlr.print_result(results["hlr"])
        
    elif scan_type == "username":
        print(f"{Colors.CYAN}[1/1] Blackbird username search...{Colors.RESET}")
        import asyncio
        bb = Blackbird(timeout=10, max_concurrent=25)
        asyncio.run(bb.search(target))
        bb.print_results(target)
        results["blackbird"] = [
            {"site": r.site, "url": r.url, "status": r.status} 
            for r in bb.results
        ]
        
    elif scan_type == "domain":
        print(f"{Colors.CYAN}[1/4] WHOIS lookup...{Colors.RESET}")
        whois_lookup = WhoisLookup()
        results["whois"] = whois_lookup.lookup(target)
        whois_lookup.print_result(results["whois"])
        
        print(f"\n{Colors.CYAN}[2/4] DNS records...{Colors.RESET}")
        dns_lookup = DNSLookup()
        results["dns"] = dns_lookup.lookup(target)
        dns_lookup.print_result(results["dns"])
        
        print(f"\n{Colors.CYAN}[3/4] GeoIP...{Colors.RESET}")
        geoip = GeoIPLookup()
        results["geoip"] = geoip.lookup(target)
        geoip.print_result(results["geoip"])
        
        print(f"\n{Colors.CYAN}[4/4] Hunter domain search...{Colors.RESET}")
        hunter = HunterIO()
        results["hunter"] = hunter.domain_search(target)
        hunter.print_domain_result(results["hunter"])
        
    elif scan_type == "ip":
        print(f"{Colors.CYAN}[1/1] GeoIP lookup...{Colors.RESET}")
        geoip = GeoIPLookup()
        results["geoip"] = geoip.lookup(target)
        geoip.print_result(results["geoip"])
    
    return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OSINT Toolkit - Open Source Intelligence Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                      
  python main.py -t user@example.com  
  python main.py -t +79001234567     
  python main.py -t johndoe           
  python main.py -t example.com      
        """
    )
    
    parser.add_argument("-t", "--target", help="Target for quick scan")
    parser.add_argument("--type", choices=["auto", "email", "phone", "username", "domain", "ip"],
                       default="auto", help="Target type (default: auto-detect)")
    parser.add_argument("-o", "--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    if args.target:
        results = quick_scan(args.target, args.type)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n{Colors.GREEN}Results saved to:{Colors.RESET} {args.output}")
    else:
        toolkit = OSINTToolkit()
        try:
            toolkit.run()
        except KeyboardInterrupt:
            print(f"\n{Colors.CYAN}Goodbye!{Colors.RESET}\n")

if __name__ == "__main__":
    main()
