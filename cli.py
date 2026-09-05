#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import config

__version__ = "2.8.0"


def normalize_target(target: str) -> str:
    normalized = target.strip()
    scheme_sep = normalized.find("://")
    if scheme_sep != -1 and normalized[:scheme_sep].lower() in {"http", "https"}:
        normalized = normalized[scheme_sep + 3:]
    normalized = normalized.rstrip("/")

    if "@" in normalized and not normalized.startswith("@"):
        return normalized.lower()
    if "." in normalized and not any(ch.isspace() for ch in normalized):
        return normalized.lower()
    return normalized


def detect_type(target: str) -> str:
    if "@" in target:
        return "email"
    stripped = target.replace("+", "").replace("-", "").replace(" ", "")
    if stripped.isdigit():
        return "phone"
    t = target.lstrip("@")
    if t.startswith("t.me/") or t.startswith("telegram.me/"):
        return "telegram"
    if "." in target:
        segs = target.split(".")
        if len(segs) == 4 and all(s.isdigit() for s in segs):
            return "ip"
        return "domain"
    return "username"


async def run_scan(
    target: str,
    scan_type: str,
    modules: Optional[List[str]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    selected = set(modules) if modules else set()
    all_modules = not selected

    def want(name: str) -> bool:
        return all_modules or name in selected

    def _log(msg: str) -> None:
        if verbose:
            print(f"  [*] {msg}", file=sys.stderr)

    if scan_type in ("domain", "ip"):
        if want("whois") and scan_type == "domain":
            _log("Running whois ...")
            from modules.extra_tools import WhoisLookup
            results["whois"] = await _invoke(WhoisLookup().lookup, target)

        if want("rdap") and scan_type == "domain":
            _log("Running rdap ...")
            from modules.rdap import RDAPLookup
            results["rdap"] = await _invoke(RDAPLookup().lookup, target)

        if want("dns") and scan_type == "domain":
            _log("Running dns ...")
            from modules.extra_tools import DNSLookup
            results["dns"] = await _invoke(DNSLookup().lookup, target)

        if want("geoip"):
            _log("Running geoip ...")
            from modules.extra_tools import GeoIPLookup
            results["geoip"] = await _invoke(GeoIPLookup().lookup, target)

        if want("cert_transparency") and scan_type == "domain":
            _log("Running cert_transparency ...")
            from modules.cert_transparency import CertTransparency
            results["cert_transparency"] = await _invoke(CertTransparency().search, target)

        if want("website") and scan_type == "domain":
            _log("Running website ...")
            from modules.extra_tools import WebsiteAnalyzer
            results["website"] = await _invoke(WebsiteAnalyzer().analyze, target)

        if want("wayback") and scan_type == "domain":
            _log("Running wayback ...")
            from modules.wayback import WaybackMachine
            wb = WaybackMachine()
            wayback_snap = await _invoke(wb.get_snapshots, target, 15)
            wayback_urls = await _invoke(wb.get_all_urls, target, 200)
            merged = dict(wayback_snap) if isinstance(wayback_snap, dict) else {}
            if isinstance(wayback_urls, dict):
                merged["urls"] = wayback_urls.get("urls", [])
                merged["total_urls"] = wayback_urls.get("total", 0)
                merged["interesting"] = wayback_urls.get("interesting", [])
                if wayback_urls.get("error") and not merged.get("error"):
                    merged["urls_error"] = wayback_urls["error"]
            results["wayback"] = merged

        if want("shodan"):
            _log("Running shodan ...")
            from modules.shodan_lookup import ShodanLookup
            ip = target
            if scan_type == "domain":
                import socket
                try:
                    ip = socket.gethostbyname(target)
                except Exception:
                    ip = target
            results["shodan"] = await _invoke(ShodanLookup().host_info, ip)

        if want("virustotal"):
            _log("Running virustotal ...")
            from modules.threat_intel import VirusTotal
            vt = VirusTotal()
            if scan_type == "ip":
                results["virustotal"] = await _invoke(vt.check_ip, target)
            else:
                results["virustotal"] = await _invoke(vt.check_domain, target)

        if want("abuseipdb") and scan_type == "ip":
            _log("Running abuseipdb ...")
            from modules.threat_intel import AbuseIPDB
            results["abuseipdb"] = await _invoke(AbuseIPDB().check_ip, target)

        if want("onion") and scan_type == "domain":
            _log("Running onion ...")
            from modules.onion_checker import OnionChecker
            results["onion"] = await _invoke(OnionChecker().check, target)

        if want("censys"):
            _log("Running censys ...")
            from modules.censys_lookup import CensysLookup
            cl = CensysLookup()
            if scan_type == "domain":
                results["censys"] = await _invoke(cl.search_domain, target)
            else:
                results["censys"] = await _invoke(cl.search_ip, target)

        if want("hudsonrock") and scan_type == "domain":
            _log("Running hudsonrock ...")
            from modules.hudsonrock import HudsonRockLookup
            results["hudsonrock"] = await _invoke(HudsonRockLookup().search_domain, target)

        if want("lunar") and scan_type == "domain":
            _log("Running lunar ...")
            from modules.lunar import LunarLookup
            results["lunar"] = await _invoke(LunarLookup().search_domain, target)

    elif scan_type == "email":
        if want("smtp"):
            _log("Running smtp ...")
            from modules.smtp_verify import SMTPVerifier
            results["smtp"] = await _invoke(SMTPVerifier().verify_email, target)

        if want("leaks"):
            _log("Running leaks ...")
            from modules.leak_lookup import LeakLookup
            results["breaches"] = await _invoke(LeakLookup().check_email_full, target)

        if want("emailrep"):
            _log("Running emailrep ...")
            from modules.hunter import EmailRepLookup
            results["emailrep"] = await _invoke(EmailRepLookup().lookup, target)

        if want("hudsonrock"):
            _log("Running hudsonrock ...")
            from modules.hudsonrock import HudsonRockLookup
            results["hudsonrock"] = await _invoke(HudsonRockLookup().search_email, target)

    elif scan_type == "phone":
        if want("hlr"):
            _log("Running hlr ...")
            from modules.hlr_lookup import HLRLookup
            hlr_obj = HLRLookup()
            hlr = await _invoke(hlr_obj.validate_phone, target)
            results["hlr"] = hlr
            owner = await _invoke(hlr_obj.reverse_lookup, hlr.get("formatted") or target)
            results["phone_owner"] = owner
            results["phone"] = {
                "valid": hlr.get("valid"),
                "country_name": hlr.get("country_name") or hlr.get("country"),
                "country_code": hlr.get("country_code"),
                "carrier": hlr.get("carrier"),
                "line_type": hlr.get("line_type"),
                "region": hlr.get("region"),
                "timezones": hlr.get("timezones"),
                "reverse": {
                    "name": ", ".join(owner.get("names", [])) or None,
                    "address": owner.get("city"),
                    "source": ", ".join(owner.get("sources", [])) or None,
                } if owner else None,
            }

    elif scan_type == "telegram":
        _log("Running telegram ...")
        from modules.telegram_lookup import TelegramLookup
        from config import TELEGRAM_BOT_TOKEN
        tg = TelegramLookup()
        tg_target = target.lstrip("@").replace("t.me/", "").replace("telegram.me/", "").strip()
        results["telegram"] = await _invoke(tg.run_lookup, tg_target, TELEGRAM_BOT_TOKEN or None)

    elif scan_type == "username":
        if want("blackbird"):
            _log("Running blackbird ...")
            from modules.blackbird import Blackbird
            bb = Blackbird(timeout=10, max_concurrent=25)
            outcome = await _invoke(bb.search, target)
            if isinstance(outcome, dict) and outcome.get("error"):
                results["blackbird"] = outcome
            else:
                results["blackbird"] = [
                    {"site": r.site, "url": r.url, "status": r.status, "response_time": r.response_time}
                    for r in bb.results
                ]

        if want("maigret"):
            _log("Running maigret ...")
            from modules.maigret_wrapper import MaigretWrapper
            results["maigret"] = await _invoke(MaigretWrapper().search, target)

        if want("hudsonrock"):
            _log("Running hudsonrock ...")
            from modules.hudsonrock import HudsonRockLookup
            results["hudsonrock"] = await _invoke(HudsonRockLookup().search_username, target)

    _log("Computing opsec score ...")
    from modules.opsec_score import score_from_results
    opsec = score_from_results(results)
    results["opsec_score"] = opsec

    _log("Building graph ...")
    from modules.graph_builder import build_graph
    graph = build_graph(target, scan_type, results)
    results["graph"] = graph

    return results


async def _invoke(func, *args, **kwargs) -> Any:
    try:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    except Exception as exc:
        return {"error": str(exc)}


def _serialisable(results: Dict[str, Any]) -> Dict[str, Any]:
    skip = {"report_path"}
    out = {}
    for k, v in results.items():
        if k in skip:
            continue
        out[k] = v
    return out


def output_json(results: Dict[str, Any], path: Optional[str] = None) -> None:
    text = json.dumps(_serialisable(results), indent=2, default=str, ensure_ascii=False)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Results saved to {path}", file=sys.stderr)
    else:
        print(text)


def output_html(target: str, scan_type: str, results: Dict[str, Any], path: Optional[str] = None) -> None:
    from modules.report_generator import generate_html_report
    opsec = results.get("opsec_score")
    report_path = generate_html_report(target, scan_type, results, opsec, output_path=path)
    print(f"HTML report saved to {report_path}", file=sys.stderr)


def output_pdf(target: str, scan_type: str, results: Dict[str, Any], path: Optional[str] = None) -> None:
    from modules.report_generator import generate_pdf_report
    opsec = results.get("opsec_score")
    report_path = generate_pdf_report(target, scan_type, results, opsec, output_path=path)
    print(f"PDF report saved to {report_path}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prism",
        description="PRISM OSINT Platform - Command Line Interface",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    scan_p = sub.add_parser("scan", help="Run an OSINT scan against a target")
    scan_p.add_argument("target", help="Scan target (domain, IP, email, phone number, or username)")
    scan_p.add_argument(
        "--type", "-t",
        dest="scan_type",
        choices=["domain", "ip", "email", "phone", "username", "telegram"],
        default=None,
        help="Target type (auto-detected if omitted)",
    )
    scan_p.add_argument(
        "--modules", "-m",
        default=None,
        help="Comma-separated list of modules to run (default: all applicable)",
    )
    scan_p.add_argument("--json", dest="fmt_json", action="store_true", default=False, help="Output JSON (default)")
    scan_p.add_argument("--html", dest="fmt_html", action="store_true", default=False, help="Generate HTML report")
    scan_p.add_argument("--pdf", dest="fmt_pdf", action="store_true", default=False, help="Generate PDF report")
    scan_p.add_argument("--output", "-o", default=None, help="Output file path")
    scan_p.add_argument("--verbose", "-v", action="store_true", default=False, help="Print progress to stderr")
    scan_p.add_argument("--quiet", "-q", action="store_true", default=False, help="Print only the result (suppress banners and progress)")

    watch_p = sub.add_parser("watchlist", help="Manage scheduled re-scans")
    watch_p.set_defaults(watch_parser=watch_p)
    watch_sub = watch_p.add_subparsers(dest="watch_command")

    watch_list = watch_sub.add_parser("list", help="List watchlist entries")
    watch_list.add_argument("--json", dest="fmt_json", action="store_true", default=False, help="Output JSON")

    watch_add = watch_sub.add_parser("add", help="Add a target to the watchlist")
    watch_add.add_argument("target", help="Target to re-scan on a schedule")
    watch_add.add_argument(
        "--type", "-t",
        dest="scan_type",
        choices=["domain", "ip", "email", "phone", "username", "telegram"],
        default=None,
        help="Target type (auto-detected if omitted)",
    )
    watch_add.add_argument("--modules", "-m", default=None, help="Comma-separated list of modules (default: all applicable)")
    watch_add.add_argument("--interval", type=float, default=24.0, help="Hours between runs (default: 24)")
    watch_add.add_argument("--webhook", default=None, help="Webhook URL to notify on changes")

    watch_rm = watch_sub.add_parser("rm", help="Remove a watchlist entry")
    watch_rm.add_argument("id", help="Watchlist entry id")

    watch_pause = watch_sub.add_parser("pause", help="Pause a watchlist entry")
    watch_pause.add_argument("id", help="Watchlist entry id")

    watch_resume = watch_sub.add_parser("resume", help="Resume a paused watchlist entry")
    watch_resume.add_argument("id", help="Watchlist entry id")

    return parser


def _fmt_ts(ts: Optional[float]) -> str:
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def run_watchlist(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    from web import watchlist as wl

    command = getattr(args, "watch_command", None)
    if command is None:
        args.watch_parser.print_help()
        return 1

    if command == "list":
        entries = wl.list_watchlists(wl.ANONYMOUS)
        if getattr(args, "fmt_json", False):
            print(json.dumps(entries, indent=2, default=str))
            return 0
        if not entries:
            print("No watchlist entries. Add one with: prism watchlist add <target>")
            return 0
        print(f"{'ID':<38} {'TARGET':<28} {'TYPE':<9} {'EVERY':<7} {'STATUS':<10} NEXT RUN")
        for e in entries:
            status = "paused" if e.get("paused") else (e.get("last_status") or "pending")
            interval = f"{e.get('interval_hours', 0):g}h"
            print(
                f"{e['id']:<38} {e['target'][:27]:<28} {e['scan_type']:<9} "
                f"{interval:<7} {status:<10} {_fmt_ts(e.get('next_run'))}"
            )
        return 0

    if command == "add":
        target = normalize_target(args.target)
        scan_type = args.scan_type or detect_type(target)
        modules = [m.strip() for m in args.modules.split(",") if m.strip()] if args.modules else None
        interval = max(1.0, min(float(args.interval), 24 * 30))
        entry = wl.create_watchlist(wl.ANONYMOUS, target, scan_type, modules, interval, args.webhook)
        print(f"Watching {entry['target']} ({entry['scan_type']}) every {interval:g}h")
        print(f"id: {entry['id']}")
        return 0

    if command == "rm":
        if wl.delete_watchlist(args.id, wl.ANONYMOUS):
            print(f"Removed {args.id}")
            return 0
        print(f"No watchlist entry with id {args.id}", file=sys.stderr)
        return 1

    if command in ("pause", "resume"):
        entry = wl.set_paused(args.id, wl.ANONYMOUS, command == "pause")
        if entry is None:
            print(f"No watchlist entry with id {args.id}", file=sys.stderr)
            return 1
        print(f"{'Paused' if entry['paused'] else 'Resumed'} {entry['target']}")
        return 0

    args.watch_parser.print_help()
    return 1


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "watchlist":
        sys.exit(run_watchlist(args, parser))

    if args.command == "scan":
        target = normalize_target(args.target)
        scan_type = args.scan_type or detect_type(target)
        modules = [m.strip() for m in args.modules.split(",") if m.strip()] if args.modules else None

        verbose = args.verbose and not args.quiet

        if verbose:
            print(f"Target : {target}", file=sys.stderr)
            print(f"Type   : {scan_type}", file=sys.stderr)
            if modules:
                print(f"Modules: {', '.join(modules)}", file=sys.stderr)
            print(file=sys.stderr)

        try:
            results = asyncio.run(run_scan(target, scan_type, modules, verbose=verbose))
        except KeyboardInterrupt:
            print("\nScan interrupted.", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        output_path = args.output

        if args.fmt_html:
            output_html(target, scan_type, results, path=output_path)
        elif args.fmt_pdf:
            output_pdf(target, scan_type, results, path=output_path)
        else:
            output_json(results, path=output_path)

        if not args.quiet:
            print(
                "\n⭐ Found PRISM useful? Star it: "
                "https://github.com/NovaCode37/Prism-platform",
                file=sys.stderr,
            )
        sys.exit(0)


if __name__ == "__main__":
    main()