import socket
import smtplib
import dns.resolver
import re
from typing import Dict, Any, List, Optional
import sys
sys.path.append('..')
from config import Colors

class SMTPVerifier:

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.sender_email = "verify@gmail.com"

    def validate_email_format(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def get_mx_records(self, domain: str) -> List[str]:
        mx_records = []
        try:
            records = dns.resolver.resolve(domain, 'MX')
            mx_records = sorted(
                [(r.preference, str(r.exchange).rstrip('.')) for r in records],
                key=lambda x: x[0]
            )
            return [mx[1] for mx in mx_records]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
            return []
        except Exception:
            return []

    def verify_email(self, email: str) -> Dict[str, Any]:
        result = {
            "email": email,
            "valid_format": False,
            "domain": None,
            "mx_records": [],
            "mx_found": False,
            "smtp_connect": False,
            "exists": None,
            "catch_all": False,
            "disposable": False,
            "details": [],
            "error": None
        }

        if not self.validate_email_format(email):
            result["error"] = "Invalid email format"
            return result
        result["valid_format"] = True

        domain = email.split('@')[1]
        result["domain"] = domain

        result["disposable"] = self._check_disposable(domain)
        if result["disposable"]:
            result["details"].append("Disposable/temporary email detected")

        mx_records = self.get_mx_records(domain)
        result["mx_records"] = mx_records

        if not mx_records:
            result["details"].append("No MX records found")
            result["error"] = "Domain has no mail server"
            return result

        result["mx_found"] = True
        result["details"].append(f"Found {len(mx_records)} MX record(s)")

        for mx in mx_records[:3]:
            smtp_result = self._smtp_check(mx, email)

            if smtp_result["connected"]:
                result["smtp_connect"] = True
                result["details"].append(f"Connected to {mx}")

                if smtp_result["exists"] is not None:
                    result["exists"] = smtp_result["exists"]
                    result["catch_all"] = smtp_result.get("catch_all", False)

                    if result["exists"]:
                        result["details"].append("Email address exists")
                    else:
                        result["details"].append("Email address does not exist")

                    if result["catch_all"]:
                        result["details"].append("Server accepts all addresses (catch-all)")

                    break
                else:
                    result["details"].append(smtp_result.get("message", "Could not verify"))
            else:
                result["details"].append(f"Could not connect to {mx}: {smtp_result.get('error', 'Unknown')}")

        if result["exists"] is None:
            result["details"].append("Could not definitively verify email existence")

        return result

    def _smtp_check(self, mx_host: str, email: str) -> Dict[str, Any]:
        result = {
            "connected": False,
            "exists": None,
            "catch_all": False,
            "error": None,
            "message": None
        }

        try:
            smtp = smtplib.SMTP(timeout=self.timeout)
            smtp.connect(mx_host)

            result["connected"] = True

            smtp.ehlo_or_helo_if_needed()

            code, message = smtp.mail(self.sender_email)
            if code != 250:
                result["message"] = f"MAIL FROM rejected: {message}"
                smtp.quit()
                return result

            code, message = smtp.rcpt(email)

            if code == 250:
                result["exists"] = True

                fake_email = f"nonexistent_test_12345@{email.split('@')[1]}"
                code2, _ = smtp.rcpt(fake_email)
                if code2 == 250:
                    result["catch_all"] = True

            elif code == 550:
                result["exists"] = False
            elif code in (451, 452):
                result["message"] = "Server temporarily unavailable"
            else:
                result["message"] = f"Unexpected response: {code} {message}"

            smtp.quit()

        except smtplib.SMTPServerDisconnected:
            result["error"] = "Server disconnected"
        except smtplib.SMTPConnectError as e:
            result["error"] = f"Connection error: {e}"
        except socket.timeout:
            result["error"] = "Connection timeout"
        except Exception as e:
            result["error"] = str(e)

        return result

    def _check_disposable(self, domain: str) -> bool:
        disposable_domains = {
            'tempmail.com', 'guerrillamail.com', 'mailinator.com',
            '10minutemail.com', 'throwaway.email', 'temp-mail.org',
            'fakeinbox.com', 'trashmail.com', 'maildrop.cc',
            'yopmail.com', 'sharklasers.com', 'guerrillamail.info',
            'grr.la', 'mailnesia.com', 'emailondeck.com',
            'tempail.com', 'dispostable.com', 'mailcatch.com',
            'tempr.email', 'discard.email', 'tmpmail.org'
        }
        return domain.lower() in disposable_domains

    def print_result(self, result: Dict):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}SMTP Email Verification{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        email = result["email"]

        if result["exists"] is True:
            status = f"{Colors.GREEN}✓ EXISTS{Colors.RESET}"
        elif result["exists"] is False:
            status = f"{Colors.RED}✗ DOES NOT EXIST{Colors.RESET}"
        else:
            status = f"{Colors.YELLOW}? UNKNOWN{Colors.RESET}"

        print(f"{Colors.YELLOW}Email:{Colors.RESET} {email}")
        print(f"{Colors.YELLOW}Status:{Colors.RESET} {status}")
        print(f"{Colors.YELLOW}Valid Format:{Colors.RESET} {'Yes' if result['valid_format'] else 'No'}")
        print(f"{Colors.YELLOW}Domain:{Colors.RESET} {result.get('domain', 'N/A')}")
        print(f"{Colors.YELLOW}MX Records:{Colors.RESET} {len(result.get('mx_records', []))} found")

        if result.get("mx_records"):
            for mx in result["mx_records"][:3]:
                print(f"  • {mx}")

        print(f"{Colors.YELLOW}SMTP Connect:{Colors.RESET} {'Yes' if result['smtp_connect'] else 'No'}")

        if result.get("disposable"):
            print(f"{Colors.RED}⚠ Disposable email detected{Colors.RESET}")

        if result.get("catch_all"):
            print(f"{Colors.YELLOW}⚠ Server accepts all addresses (catch-all){Colors.RESET}")

        if result.get("details"):
            print(f"\n{Colors.BOLD}Details:{Colors.RESET}")
            for detail in result["details"]:
                print(f"  • {detail}")

        if result.get("error"):
            print(f"\n{Colors.RED}Error: {result['error']}{Colors.RESET}")

def run_smtp_verify():
    verifier = SMTPVerifier()

    print(f"\n{Colors.BOLD}SMTP Email Verification{Colors.RESET}")
    print(f"{Colors.CYAN}Check if email address exists in real-time{Colors.RESET}")

    email = input(f"\n{Colors.GREEN}Enter email address: {Colors.RESET}").strip()

    if not email:
        print(f"{Colors.RED}No email provided{Colors.RESET}")
        return None

    print(f"\n{Colors.CYAN}Verifying...{Colors.RESET}")
    result = verifier.verify_email(email)
    verifier.print_result(result)

    return result

if __name__ == "__main__":
    run_smtp_verify()
