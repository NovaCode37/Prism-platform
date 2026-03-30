from typing import Dict, Any, List
import sys
sys.path.append('..')
from config import Colors

RISK_LEVELS = {
    (0, 30): ("CRITICAL", Colors.RED),
    (31, 50): ("HIGH", Colors.RED),
    (51, 70): ("MEDIUM", Colors.YELLOW),
    (71, 85): ("LOW", Colors.GREEN),
    (86, 100): ("MINIMAL", Colors.GREEN),
}

class OpsecScorer:

    def __init__(self):
        self.findings: List[Dict] = []
        self.score = 100
        self.category_scores: Dict[str, Dict] = {
            "data_exposure": {"max": 35, "score": 35, "findings": []},
            "identity_opsec": {"max": 25, "score": 25, "findings": []},
            "infrastructure": {"max": 25, "score": 25, "findings": []},
            "web_security": {"max": 15, "score": 15, "findings": []},
        }

    def _deduct(self, category: str, points: int, severity: str, message: str) -> None:
        cat = self.category_scores[category]
        actual_deduction = min(points, cat["score"])
        cat["score"] = max(0, cat["score"] - actual_deduction)
        cat["findings"].append(
            {
                "severity": severity,
                "message": message,
                "deduction": actual_deduction,
            }
        )
        self.findings.append(
            {
                "category": category,
                "severity": severity,
                "message": message,
                "deduction": actual_deduction,
            }
        )

    def process_leaks(self, leak_result: Dict) -> None:
        if not leak_result:
            return
        breach_count = leak_result.get("breach_count", 0)
        if breach_count >= 5:
            self._deduct("data_exposure", 25, "CRITICAL",
                         f"Found in {breach_count} known data breaches")
        elif breach_count >= 2:
            self._deduct("data_exposure", 15, "HIGH",
                         f"Found in {breach_count} known data breaches")
        elif breach_count == 1:
            self._deduct("data_exposure", 8, "MEDIUM",
                         "Found in 1 known data breach")

    def process_smtp(self, smtp_result: Dict) -> None:
        if not smtp_result:
            return
        if smtp_result.get("exists") is True:
            self._deduct("data_exposure", 5, "INFO",
                         "Email address is active and publicly confirmable via SMTP")

    def process_virustotal(self, vt_result: Dict) -> None:
        if not vt_result or vt_result.get("error"):
            return
        malicious = vt_result.get("malicious", 0)
        suspicious = vt_result.get("suspicious", 0)
        if malicious >= 5:
            self._deduct("data_exposure", 30, "CRITICAL",
                         f"Flagged as malicious by {malicious} VirusTotal engines")
        elif malicious >= 1:
            self._deduct("data_exposure", 20, "HIGH",
                         f"Flagged as malicious by {malicious} VirusTotal engines")
        elif suspicious >= 3:
            self._deduct("data_exposure", 10, "MEDIUM",
                         f"Flagged as suspicious by {suspicious} VirusTotal engines")

    def process_abuseipdb(self, adb_result: Dict) -> None:
        if not adb_result or adb_result.get("error"):
            return
        score = adb_result.get("abuse_score", 0)
        if score >= 80:
            self._deduct("data_exposure", 25, "CRITICAL",
                         f"AbuseIPDB confidence score: {score}/100")
        elif score >= 40:
            self._deduct("data_exposure", 15, "HIGH",
                         f"AbuseIPDB confidence score: {score}/100")
        elif score >= 10:
            self._deduct("data_exposure", 7, "MEDIUM",
                         f"AbuseIPDB confidence score: {score}/100")
        if adb_result.get("is_tor"):
            self._deduct("data_exposure", 10, "HIGH", "IP is a known TOR exit node")

    def process_blackbird(self, blackbird_results: List) -> None:
        if not blackbird_results:
            return
        found = [r for r in blackbird_results
                 if isinstance(r, dict) and r.get("status") == "found"]
        count = len(found)
        if count >= 20:
            self._deduct("identity_opsec", 20, "HIGH",
                         f"Username found on {count} platforms — high digital footprint")
        elif count >= 10:
            self._deduct("identity_opsec", 13, "MEDIUM",
                         f"Username found on {count} platforms")
        elif count >= 5:
            self._deduct("identity_opsec", 7, "LOW",
                         f"Username found on {count} platforms")
        elif count >= 1:
            self._deduct("identity_opsec", 3, "INFO",
                         f"Username found on {count} platform(s)")

    def process_hunter(self, hunter_result: Dict) -> None:
        if not hunter_result:
            return
        emails = hunter_result.get("emails", [])
        if len(emails) >= 10:
            self._deduct("identity_opsec", 15, "HIGH",
                         f"{len(emails)} corporate email addresses publicly indexed")
        elif len(emails) >= 3:
            self._deduct("identity_opsec", 8, "MEDIUM",
                         f"{len(emails)} email addresses found via Hunter.io")
        elif len(emails) >= 1:
            self._deduct("identity_opsec", 3, "LOW",
                         f"{len(emails)} email address(es) found via Hunter.io")

    def process_whois(self, whois_result: Dict) -> None:
        if not whois_result or whois_result.get("error"):
            return
        emails = whois_result.get("emails", [])
        if emails:
            self._deduct("infrastructure", 8, "MEDIUM",
                         f"WHOIS exposes {len(emails)} contact email(s) — registrar privacy not used")
        org = whois_result.get("org", "")
        if org and org.lower() not in ("", "none", "n/a", "redacted for privacy"):
            self._deduct("infrastructure", 3, "INFO",
                         f"WHOIS exposes organization: {org}")

    def process_shodan(self, shodan_result: Dict) -> None:
        if not shodan_result or shodan_result.get("error"):
            return
        ports = shodan_result.get("open_ports", [])
        vulns = shodan_result.get("vulns", [])
        sensitive_ports = {21, 22, 23, 3389, 5900, 445, 3306, 5432, 27017, 6379}
        exposed = [p for p in ports if p in sensitive_ports]

        if vulns:
            self._deduct("infrastructure", 20, "CRITICAL",
                         f"Shodan found {len(vulns)} known CVE(s): {', '.join(vulns[:3])}")
        if len(ports) >= 10:
            self._deduct("infrastructure", 10, "HIGH",
                         f"{len(ports)} open ports detected via Shodan")
        elif len(ports) >= 5:
            self._deduct("infrastructure", 5, "MEDIUM",
                         f"{len(ports)} open ports detected via Shodan")
        if exposed:
            self._deduct("infrastructure", 12, "HIGH",
                         f"Sensitive services exposed: {', '.join(map(str, exposed))}")

    def process_cert_transparency(self, ct_result: Dict) -> None:
        if not ct_result or ct_result.get("error"):
            return
        subdomains = ct_result.get("subdomains", [])
        if len(subdomains) >= 20:
            self._deduct("infrastructure", 5, "MEDIUM",
                         f"Certificate transparency reveals {len(subdomains)} subdomains")
        elif len(subdomains) >= 5:
            self._deduct("infrastructure", 3, "LOW",
                         f"Certificate transparency reveals {len(subdomains)} subdomains")

    def process_dns(self, dns_result: Dict) -> None:
        if not dns_result or dns_result.get("error"):
            return
        records = dns_result.get("records", {})
        txt = records.get("TXT", [])
        for record in txt:
            r_str = str(record).lower()
            if "spf" not in r_str and "dkim" not in r_str and "dmarc" not in r_str:
                pass
        has_spf = any("spf" in str(r).lower() for r in txt)
        if not has_spf and txt is not None:
            self._deduct("infrastructure", 5, "MEDIUM",
                         "No SPF record found — domain may be vulnerable to email spoofing")

    def process_website(self, web_result: Dict) -> None:
        if not web_result or web_result.get("error"):
            return
        headers = web_result.get("headers", {})
        url = web_result.get("url", "")

        if url.startswith("http://"):
            self._deduct("web_security", 8, "HIGH",
                         "Site served over HTTP — no TLS encryption")

        missing_headers = []
        resp_headers_lower = {k.lower(): v for k, v in headers.items()}
        if not resp_headers_lower.get("x-frame-options") and not resp_headers_lower.get("content-security-policy"):
            missing_headers.append("X-Frame-Options / CSP")
        if not resp_headers_lower.get("x-content-type-options"):
            missing_headers.append("X-Content-Type-Options")

        if missing_headers:
            self._deduct("web_security", 5, "LOW",
                         f"Missing security headers: {', '.join(missing_headers)}")

        emails = web_result.get("emails", [])
        if len(emails) >= 5:
            self._deduct("web_security", 4, "MEDIUM",
                         f"{len(emails)} email addresses scraped from website HTML")
        elif emails:
            self._deduct("web_security", 2, "LOW",
                         f"{len(emails)} email address(es) found in website HTML")

        techs = [t.lower() for t in web_result.get("technologies", [])]
        risky = [t for t in techs if any(r in t for r in ["php", "asp.net", "jquery"])]
        if risky:
            self._deduct("web_security", 3, "INFO",
                         f"Potentially outdated technologies detected: {', '.join(risky)}")

    def process_wayback(self, wb_result: Dict) -> None:
        if not wb_result or wb_result.get("error"):
            return
        interesting = wb_result.get("interesting", [])
        if len(interesting) >= 5:
            self._deduct("web_security", 8, "HIGH",
                         f"Wayback Machine reveals {len(interesting)} sensitive/admin URLs in history")
        elif interesting:
            self._deduct("web_security", 4, "MEDIUM",
                         f"Wayback Machine reveals {len(interesting)} sensitive URL(s) in history")

    def calculate(self) -> Dict[str, Any]:
        total = sum(c["score"] for c in self.category_scores.values())
        max_total = sum(c["max"] for c in self.category_scores.values())
        self.score = round((total / max_total) * 100)

        risk_label, risk_color = "UNKNOWN", Colors.RESET
        for (lo, hi), (label, color) in RISK_LEVELS.items():
            if lo <= self.score <= hi:
                risk_label = label
                risk_color = color
                break

        return {
            "score": self.score,
            "risk_level": risk_label,
            "categories": {
                name: {
                    "score": cat["score"],
                    "max": cat["max"],
                    "percent": round((cat["score"] / cat["max"]) * 100),
                    "findings": cat["findings"],
                }
                for name, cat in self.category_scores.items()
            },
            "all_findings": sorted(
                self.findings,
                key=lambda f: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(f["severity"], 5),
            ),
        }

    def print_report(self, result: Dict) -> None:
        score = result["score"]
        risk = result["risk_level"]

        risk_color = Colors.RED if risk in ("CRITICAL", "HIGH") else (
            Colors.YELLOW if risk == "MEDIUM" else Colors.GREEN
        )

        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}OPSEC Security Score{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        bar_filled = int(score / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        print(f"\n  Score: {risk_color}{score}/100  [{bar}]  {risk}{Colors.RESET}\n")

        cat_labels = {
            "data_exposure": "Data Exposure",
            "identity_opsec": "Identity OPSEC",
            "infrastructure": "Infrastructure",
            "web_security": "Web Security",
        }

        print(f"  {'Category':<22} {'Score':>7}  Findings")
        print(f"  {'-'*50}")
        for key, cat in result["categories"].items():
            label = cat_labels.get(key, key)
            pct = cat["percent"]
            c = Colors.RED if pct < 50 else Colors.YELLOW if pct < 75 else Colors.GREEN
            finding_count = len(cat["findings"])
            print(f"  {label:<22} {c}{cat['score']:>3}/{cat['max']:<3}{Colors.RESET}  {finding_count} finding(s)")

        if result["all_findings"]:
            print(f"\n{Colors.BOLD}Findings:{Colors.RESET}")
            sev_colors = {
                "CRITICAL": Colors.RED,
                "HIGH": Colors.RED,
                "MEDIUM": Colors.YELLOW,
                "LOW": Colors.CYAN,
                "INFO": Colors.RESET,
            }
            for f in result["all_findings"]:
                c = sev_colors.get(f["severity"], Colors.RESET)
                print(f"  {c}[{f['severity']:<8}]{Colors.RESET} {f['message']}")

def score_from_results(all_results: Dict[str, Any]) -> Dict[str, Any]:
    scorer = OpsecScorer()

    if "breaches" in all_results:
        scorer.process_leaks(all_results["breaches"])
    if "smtp" in all_results:
        scorer.process_smtp(all_results["smtp"])
    if "virustotal" in all_results:
        scorer.process_virustotal(all_results["virustotal"])
    if "abuseipdb" in all_results:
        scorer.process_abuseipdb(all_results["abuseipdb"])
    if "blackbird" in all_results:
        scorer.process_blackbird(all_results["blackbird"])
    if "hunter" in all_results:
        scorer.process_hunter(all_results["hunter"])
    if "whois" in all_results:
        scorer.process_whois(all_results["whois"])
    if "shodan" in all_results:
        scorer.process_shodan(all_results["shodan"])
    if "cert_transparency" in all_results:
        scorer.process_cert_transparency(all_results["cert_transparency"])
    if "dns" in all_results:
        scorer.process_dns(all_results["dns"])
    if "website" in all_results:
        scorer.process_website(all_results["website"])
    if "wayback" in all_results:
        scorer.process_wayback(all_results["wayback"])

    return scorer.calculate()
