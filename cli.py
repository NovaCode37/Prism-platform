#!/usr/bin/env python3
"""
PRISM - Open Source Intelligence Platform
CLI entry point for running scans directly from the command line.
"""

import asyncio
import json
import os
import sys
import argparse
from typing import Any, Dict, List, Optional
from datetime import datetime

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules
from modules.cert_transparency import CertTransparency
from modules.darkweb_search import DarkWebSearch
from modules.gravatar import GravatarRecon
from modules.onion_checker import OnionChecker
from modules.rdap import RDAPLookup
from modules.shodan_lookup import ShodanLookup
from modules.virustotal_lookup import VirusTotalLookup
from modules.abuseipdb_lookup import AbuseIPDBLookup
from modules.github_recon import GitHubRecon
from modules.breach_check import BreachCheck
from modules.whois_lookup import WhoisLookup
from modules.dns_lookup import DNSLookup
from modules.geoip import GeoIP
from modules.wayback import Wayback
from config import Colors, print_banner


def normalize_target(target: str) -> str:
    """Normalize a target string for consistent handling."""
    if not target:
        return target

    # Strip whitespace
    target = target.strip()

    # Remove protocol prefixes
    if target.startswith(("http://", "https://")):
        target = target.split("://", 1)[1]

    # Remove trailing slashes
    target = target.rstrip("/")

    # Lowercase for domains/emails
    if "@" in target:
        # Email - lowercase the whole thing
        return target.lower()
    elif "." in target and " " not in target:
        # Domain or IP-like - lowercase
        return target.lower()

    return target


def detect_type(target: str) -> str:
    """Detect the type of target."""
    target = target.strip()

    # Email
    if "@" in target and "." in target.split("@")[-1]:
        return "email"

    # IP address (IPv4)
    import re
    if re.match(r"^(\d{1,3}\.){3}\d{1,3}$", target):
        return "ip"

    # Phone number (basic detection)
    if re.match(r"^\+?[\d][\d\s().-]{6,}$", target):
        return "phone"

    # Username (starts with @)
    if target.startswith("@"):
        return "username"

    # Domain (has a dot and no spaces)
    if "." in target and " " not in target:
        return "domain"

    # Default to username
    return "username"


def output_json(data: Dict[str, Any], path: Optional[str] = None) -> None:
    """Output results as JSON."""
    json_str = json.dumps(data, indent=2, default=str)
    if path:
        with open(path, "w") as f:
            f.write(json_str)
    else:
        print(json_str)


def output_markdown(results: Dict[str, Any]) -> str:
    """Generate a Markdown report from results."""
    lines = []
    lines.append(f"# PRISM Scan Results")
    lines.append(f"")
    lines.append(f"**Target:** {results.get('target', 'N/A')}")
    lines.append(f"**Type:** {results.get('scan_type', 'N/A')}")
    lines.append(f"**Timestamp:** {datetime.now().isoformat()}")
    lines.append(f"")

    # OPSEC Score
    opsec = results.get("opsec", {})
    if opsec:
        lines.append(f"## OPSEC Score")
        lines.append(f"")
        lines.append(f"**Score:** {opsec.get('score', 'N/A')}/100")
        lines.append(f"**Risk Level:** {opsec.get('risk_level', 'N/A')}")
        lines.append(f"")

    # Modules
    lines.append(f"## Module Results")
    lines.append(f"")
    for key, value in results.items():
        if key in ("target", "scan_type", "opsec", "started_at", "completed_at", "status"):
            continue
        if not value:
            continue
        if isinstance(value, dict) and value.get("error"):
            lines.append(f"### {key}")
            lines.append(f"")
            lines.append(f"Error: {value['error']}")
            lines.append(f"")
            continue
        lines.append(f"### {key}")
        lines.append(f"")
        lines.append(f"```json")
        lines.append(json.dumps(value, indent=2, default=str))
        lines.append(f"```")
        lines.append(f"")

    return "\n".join(lines)


async def run_scan(
    target: str,
    scan_type: str,
    modules: Optional[List[str]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run a scan with the specified parameters."""
    results: Dict[str, Any] = {
        "target": target,
        "scan_type": scan_type,
        "started_at": datetime.now().isoformat(),
        "status": "running",
    }

    # Determine which modules to run
    module_handlers = {}

    # Common modules for all types
    common_modules = {
        "geoip": GeoIP,
        "opsec": None,  # Special case
    }

    # Type-specific modules
    if scan_type == "domain":
        type_modules = {
            "whois": WhoisLookup,
            "dns": DNSLookup,
            "cert_transparency": CertTransparency,
            "rdap": RDAPLookup,
            "wayback": Wayback,
        }
        # Conditionally add keyed modules if keys are set
        if os.getenv("VIRUSTOTAL_API_KEY"):
            type_modules["virustotal"] = VirusTotalLookup
        if os.getenv("SHODAN_API_KEY"):
            type_modules["shodan"] = ShodanLookup
        if os.getenv("ABUSEIPDB_API_KEY"):
            type_modules["abuseipdb"] = AbuseIPDBLookup

    elif scan_type == "email":
        type_modules = {
            "gravatar": GravatarRecon,
            "breach": BreachCheck,
        }

    elif scan_type == "username":
        type_modules = {
            "github": GitHubRecon,
        }

    elif scan_type == "ip":
        type_modules = {
            "geoip": GeoIP,
        }
        if os.getenv("VIRUSTOTAL_API_KEY"):
            type_modules["virustotal"] = VirusTotalLookup
        if os.getenv("SHODAN_API_KEY"):
            type_modules["shodan"] = ShodanLookup
        if os.getenv("ABUSEIPDB_API_KEY"):
            type_modules["abuseipdb"] = AbuseIPDBLookup

    elif scan_type == "phone":
        type_modules = {}

    else:
        type_modules = {}

    # Combine modules
    all_modules = {**common_modules, **type_modules}

    # Filter if specific modules requested
    if modules:
        all_modules = {k: v for k, v in all_modules.items() if k in modules}

    # Run each module
    for name, handler in all_modules.items():
        if verbose:
            print(f"{Colors.CYAN}Running module: {name}{Colors.RESET}")

        try:
            if handler is None:
                # Special handling for modules without a class
                if name == "opsec":
                    # OPSEC scoring is done after all modules
                    continue
                results[name] = {"error": "Module not available"}
                continue

            # Instantiate and run
            instance = handler()
            if hasattr(instance, "lookup"):
                result = instance.lookup(target)
            elif hasattr(instance, "search"):
                result = instance.search(target)
            elif hasattr(instance, "check"):
                result = instance.check(target)
            elif hasattr(instance, "run"):
                result = instance.run(target)
            else:
                result = {"error": f"Module {name} has no main method"}

            results[name] = result

        except Exception as e:
            results[name] = {"error": str(e)}
            if verbose:
                print(f"{Colors.RED}Error in {name}: {e}{Colors.RESET}")

    # Run OPSEC scoring
    try:
        from modules.opsec_scorer import score_results
        results["opsec"] = score_results(results)
    except Exception as e:
        results["opsec"] = {"error": str(e)}

    results["completed_at"] = datetime.now().isoformat()
    results["status"] = "completed"

    return results


def main(args=None):
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="PRISM - Open Source Intelligence Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py scan example.com
  python cli.py scan user@example.com --type email
  python cli.py scan @username --type username
  python cli.py scan 8.8.8.8 --type ip
  python cli.py scan +1234567890 --type phone
  python cli.py scan example.com --modules whois,dns,cert_transparency
  python cli.py scan example.com --json -o results.json
  python cli.py scan example.com --html -o report.html
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Run a scan")
    scan_parser.add_argument("target", help="Target to scan (domain, email, IP, phone, username)")
    scan_parser.add_argument("--type", choices=["domain", "email", "ip", "phone", "username"],
                            help="Force target type (auto-detected if not specified)")
    scan_parser.add_argument("--modules", help="Comma-separated list of modules to run")
    scan_parser.add_argument("--json", "-j", action="store_true", help="Output results as JSON")
    scan_parser.add_argument("--markdown", "-m", action="store_true", help="Output results as Markdown")
    scan_parser.add_argument("--html", action="store_true", help="Output results as HTML")
    scan_parser.add_argument("--output", "-o", help="Output file (for JSON/Markdown/HTML)")
    scan_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    scan_parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output (no banner)")

    # Web command
    web_parser = subparsers.add_parser("web", help="Start the web interface")

    # Parse arguments
    parsed_args = parser.parse_args(args)

    if parsed_args.command == "scan":
        target = parsed_args.target
        if not target:
            print("Error: No target specified")
            sys.exit(1)

        # Normalize target
        target = normalize_target(target)

        # Detect type if not specified
        scan_type = parsed_args.type or detect_type(target)

        # Parse modules
        modules = None
        if parsed_args.modules:
            modules = [m.strip() for m in parsed_args.modules.split(",")]

        # Print banner
        if not parsed_args.quiet:
            print_banner()
            print(f"\n{Colors.YELLOW}Target:{Colors.RESET} {target}")
            print(f"{Colors.YELLOW}Type:{Colors.RESET} {scan_type}")
            if modules:
                print(f"{Colors.YELLOW}Modules:{Colors.RESET} {', '.join(modules)}")
            print()

        # Run scan
        try:
            results = asyncio.run(run_scan(target, scan_type, modules, parsed_args.verbose))

            # Output results
            if parsed_args.json:
                output_json(results, parsed_args.output)
            elif parsed_args.markdown:
                markdown = output_markdown(results)
                if parsed_args.output:
                    with open(parsed_args.output, "w") as f:
                        f.write(markdown)
                else:
                    print(markdown)
            elif parsed_args.html:
                try:
                    from modules.report_generator import generate_html_report
                    html = generate_html_report(results)
                    if parsed_args.output:
                        with open(parsed_args.output, "w") as f:
                            f.write(html)
                    else:
                        print(html)
                except ImportError as e:
                    print(f"{Colors.RED}Error: {e}{Colors.RESET}")
                    print("HTML report generation requires additional dependencies.")
                    print("Install them with: pip install -r requirements-web.txt")
                    sys.exit(1)
            else:
                # Default: print summary
                print_summary(results)

            sys.exit(0)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Scan interrupted by user{Colors.RESET}")
            sys.exit(1)
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")
            if parsed_args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    elif parsed_args.command == "web":
        print("Starting web interface...")
        print("Run: uvicorn web.app:app --host 0.0.0.0 --port 8080")
        print("Or use Docker: docker compose up")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


def print_summary(results: Dict[str, Any]) -> None:
    """Print a summary of scan results."""
    from config import Colors

    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Scan Results{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

    print(f"{Colors.YELLOW}Target:{Colors.RESET} {results.get('target', 'N/A')}")
    print(f"{Colors.YELLOW}Type:{Colors.RESET} {results.get('scan_type', 'N/A')}")
    print(f"{Colors.YELLOW}Started:{Colors.RESET} {results.get('started_at', 'N/A')}")
    print(f"{Colors.YELLOW}Completed:{Colors.RESET} {results.get('completed_at', 'N/A')}")
    print(f"{Colors.YELLOW}Status:{Colors.RESET} {results.get('status', 'N/A')}")

    # OPSEC Score
    opsec = results.get("opsec", {})
    if opsec and not opsec.get("error"):
        score = opsec.get("score", "N/A")
        risk = opsec.get("risk_level", "N/A")
        color = Colors.GREEN if score >= 70 else Colors.YELLOW if score >= 40 else Colors.RED
        print(f"\n{Colors.BOLD}OPSEC Score:{Colors.RESET} {color}{score}/100{Colors.RESET} ({risk})")

    # Module results
    print(f"\n{Colors.BOLD}Module Results:{Colors.RESET}")
    for key, value in results.items():
        if key in ("target", "scan_type", "opsec", "started_at", "completed_at", "status"):
            continue
        if not value:
            continue

        if isinstance(value, dict):
            if value.get("error"):
                status = f"{Colors.RED}ERROR{Colors.RESET}"
            elif value.get("status") == "ok":
                status = f"{Colors.GREEN}OK{Colors.RESET}"
            else:
                status = f"{Colors.YELLOW}{value.get('status', 'UNKNOWN')}{Colors.RESET}"
            print(f"  {key}: {status}")
        else:
            print(f"  {key}: {type(value).__name__}")

    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")


if __name__ == "__main__":
    main()