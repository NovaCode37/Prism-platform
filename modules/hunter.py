import dns.resolver
import requests
import socket
from typing import Dict, Any, List
import sys
sys.path.append('..')
from config import Colors

FREE_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "mail.com", "protonmail.com", "proton.me", "zoho.com",
    "yandex.ru", "yandex.com", "mail.ru", "bk.ru", "inbox.ru", "list.ru",
    "gmx.com", "gmx.net", "tutanota.com", "tuta.io", "fastmail.com",
}


class EmailRepLookup:

    def __init__(self):
        pass

    def _check_mx(self, domain: str) -> List[str]:
        try:
            answers = dns.resolver.resolve(domain, "MX")
            return sorted(
                [(r.preference, str(r.exchange).rstrip(".")) for r in answers],
                key=lambda x: x[0],
            )
        except Exception:
            return []

    def _check_spf(self, domain: str) -> bool:
        try:
            answers = dns.resolver.resolve(domain, "TXT")
            for r in answers:
                if "v=spf1" in str(r).lower():
                    return True
        except Exception:
            pass
        return False

    def _check_dmarc(self, domain: str) -> bool:
        try:
            answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
            for r in answers:
                if "v=dmarc1" in str(r).lower():
                    return True
        except Exception:
            pass
        return False

    def _check_disposable(self, domain: str) -> bool:
        try:
            r = requests.get(
                f"https://open.kickbox.com/v1/disposable/{domain}",
                timeout=8,
            )
            if r.status_code == 200:
                return r.json().get("disposable", False)
        except Exception:
            pass
        return False

    def _check_smtp_exists(self, email: str, domain: str, mx_host: str) -> bool:
        try:
            with socket.create_connection((mx_host, 25), timeout=8) as sock:
                sock.recv(1024)
                sock.sendall(b"EHLO prism.local\r\n")
                sock.recv(1024)
                sock.sendall(f"MAIL FROM:<test@prism.local>\r\n".encode())
                sock.recv(1024)
                sock.sendall(f"RCPT TO:<{email}>\r\n".encode())
                resp = sock.recv(1024).decode(errors="ignore")
                sock.sendall(b"QUIT\r\n")
                return resp.startswith("250")
        except Exception:
            return False

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

        try:
            domain = email.split("@")[-1].lower()

            mx_records = self._check_mx(domain)
            result["valid_mx"] = len(mx_records) > 0
            result["mx_records"] = [h for _, h in mx_records[:5]]

            result["free_provider"] = domain in FREE_PROVIDERS
            result["disposable"] = self._check_disposable(domain)

            has_spf = self._check_spf(domain)
            has_dmarc = self._check_dmarc(domain)
            result["spoofable"] = not has_spf or not has_dmarc
            result["spf"] = has_spf
            result["dmarc"] = has_dmarc

            if mx_records:
                mx_host = mx_records[0][1]
                result["deliverable"] = self._check_smtp_exists(email, domain, mx_host)

            score = 0
            if result["valid_mx"]:       score += 30
            if not result["disposable"]: score += 25
            if has_spf:                  score += 15
            if has_dmarc:                score += 15
            if result["deliverable"]:    score += 15

            if score >= 70:
                result["reputation"] = "high"
            elif score >= 40:
                result["reputation"] = "medium"
            else:
                result["reputation"] = "low"

            result["suspicious"] = result["disposable"] or (not result["valid_mx"])
            result["domain_reputation"] = "high" if (has_spf and has_dmarc) else "medium" if has_spf else "low"

        except Exception as e:
            result["error"] = str(e)

        return result

    def print_result(self, result: Dict) -> None:
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Email Reputation: {result['email']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        rep_color = {
            "high": Colors.GREEN,
            "medium": Colors.YELLOW,
            "low": Colors.RED,
        }.get(result.get("reputation", ""), Colors.YELLOW)

        print(f"{Colors.YELLOW}Reputation:{Colors.RESET}       {rep_color}{(result['reputation'] or 'N/A').upper()}{Colors.RESET}")
        print(f"{Colors.YELLOW}Suspicious:{Colors.RESET}       {Colors.RED + 'YES' + Colors.RESET if result['suspicious'] else Colors.GREEN + 'NO' + Colors.RESET}")
        print(f"{Colors.YELLOW}Valid MX:{Colors.RESET}         {Colors.GREEN + 'YES' + Colors.RESET if result['valid_mx'] else Colors.RED + 'NO' + Colors.RESET}")
        print(f"{Colors.YELLOW}Deliverable:{Colors.RESET}      {result.get('deliverable', 'N/A')}")
        print(f"{Colors.YELLOW}SPF:{Colors.RESET}              {Colors.GREEN + 'YES' + Colors.RESET if result.get('spf') else Colors.RED + 'NO' + Colors.RESET}")
        print(f"{Colors.YELLOW}DMARC:{Colors.RESET}            {Colors.GREEN + 'YES' + Colors.RESET if result.get('dmarc') else Colors.RED + 'NO' + Colors.RESET}")
        print(f"{Colors.YELLOW}Domain Rep:{Colors.RESET}       {result.get('domain_reputation', 'N/A')}")

        flags = []
        if result["disposable"]:  flags.append(f"{Colors.YELLOW}Disposable{Colors.RESET}")
        if result["spoofable"]:   flags.append(f"{Colors.YELLOW}Spoofable{Colors.RESET}")
        if result["free_provider"]: flags.append(f"{Colors.CYAN}Free Provider{Colors.RESET}")

        if flags:
            print(f"\n{Colors.BOLD}Flags:{Colors.RESET}")
            for f in flags:
                print(f"  {Colors.RED}•{Colors.RESET} {f}")


HunterIO = EmailRepLookup


def run_emailrep():
    er = EmailRepLookup()
    print(f"\n{Colors.BOLD}Email Reputation Lookup{Colors.RESET}")
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
