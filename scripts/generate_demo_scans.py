import json
import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.opsec_score import score_from_results
from modules.graph_builder import build_graph

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "demo", "scan_data")

DEMO_DOMAIN = {
    "target": "example-corp.com",
    "scan_type": "domain",
    "results": {
        "whois": {
            "registrar": "NameCheap, Inc.",
            "org": "Example Corp Ltd",
            "country": "US",
            "creation_date": "2014-03-21T00:00:00",
            "expiration_date": "2026-03-21T00:00:00",
            "name_servers": ["ns1.examplehost.com", "ns2.examplehost.com"],
            "emails": ["admin@example-corp.com", "abuse@example-corp.com"],
            "error": None,
        },
        "dns": {
            "records": {
                "A": ["93.184.216.34"],
                "MX": ["10 mail.example-corp.com"],
                "NS": ["ns1.examplehost.com", "ns2.examplehost.com"],
                "TXT": ["v=spf1 include:_spf.google.com ~all"],
            },
            "error": None,
        },
        "geoip": {
            "ip": "93.184.216.34",
            "city": "Norwell",
            "region": "Massachusetts",
            "country": "US",
            "country_name": "United States",
            "loc": "42.1596,-70.8203",
            "org": "AS15133 Edgecast Inc.",
            "timezone": "America/New_York",
            "error": None,
        },
        "cert_transparency": {
            "subdomains": [
                "www.example-corp.com", "mail.example-corp.com", "vpn.example-corp.com",
                "dev.example-corp.com", "staging.example-corp.com", "api.example-corp.com",
                "admin.example-corp.com", "git.example-corp.com", "ci.example-corp.com",
                "jenkins.example-corp.com", "grafana.example-corp.com", "vault.example-corp.com",
            ],
            "total_certs": 47,
            "error": None,
        },
        "website": {
            "url": "https://example-corp.com",
            "title": "Example Corp — Enterprise Solutions",
            "technologies": ["nginx", "WordPress", "jQuery", "Cloudflare"],
            "emails": ["contact@example-corp.com", "careers@example-corp.com"],
            "headers": {
                "Server": "nginx",
                "Strict-Transport-Security": "max-age=31536000",
            },
            "social_links": [
                {"platform": "twitter", "username": "examplecorp"},
                {"platform": "linkedin", "username": "example-corp"},
            ],
            "error": None,
        },
        "wayback": {
            "total_snapshots": 1284,
            "first_snapshot": "2014-05-02",
            "last_snapshot": "2026-05-30",
            "interesting": [
                "https://example-corp.com/.env.bak",
                "https://example-corp.com/admin/config.old",
            ],
        },
    },
}

DEMO_IP = {
    "target": "45.83.64.12",
    "scan_type": "ip",
    "results": {
        "geoip": {
            "ip": "45.83.64.12",
            "city": "Amsterdam",
            "region": "North Holland",
            "country": "NL",
            "country_name": "Netherlands",
            "loc": "52.3740,4.8897",
            "org": "AS209103 Example Hosting B.V.",
            "timezone": "Europe/Amsterdam",
            "error": None,
        },
        "shodan": {
            "ip": "45.83.64.12",
            "open_ports": [22, 80, 443, 3306, 6379],
            "vulns": ["CVE-2021-44228", "CVE-2022-0778"],
            "services": [
                {"port": 22, "transport": "tcp", "product": "OpenSSH", "version": "7.4"},
                {"port": 80, "transport": "tcp", "product": "nginx", "version": "1.18.0"},
                {"port": 443, "transport": "tcp", "product": "nginx", "version": "1.18.0"},
                {"port": 3306, "transport": "tcp", "product": "MySQL", "version": "5.7.38"},
                {"port": 6379, "transport": "tcp", "product": "Redis", "version": "6.2.6"},
            ],
            "error": None,
        },
        "virustotal": {
            "malicious": 3,
            "suspicious": 1,
            "harmless": 62,
            "undetected": 8,
            "country": "NL",
            "as_owner": "Example Hosting B.V.",
            "error": None,
        },
        "abuseipdb": {
            "abuse_score": 64,
            "total_reports": 38,
            "isp": "Example Hosting B.V.",
            "usage_type": "Data Center/Web Hosting/Transit",
            "is_tor": False,
            "error": None,
        },
    },
}

DEMO_USERNAME = {
    "target": "johndoe",
    "scan_type": "username",
    "results": {
        "blackbird": [
            {"site": "GitHub", "url": "https://github.com/johndoe", "status": "found", "response_time": 0.41},
            {"site": "Reddit", "url": "https://reddit.com/user/johndoe", "status": "found", "response_time": 0.55},
            {"site": "Twitter", "url": "https://twitter.com/johndoe", "status": "found", "response_time": 0.62},
            {"site": "Instagram", "url": "https://instagram.com/johndoe", "status": "found", "response_time": 0.71},
            {"site": "Steam", "url": "https://steamcommunity.com/id/johndoe", "status": "found", "response_time": 0.48},
            {"site": "GitLab", "url": "https://gitlab.com/johndoe", "status": "found", "response_time": 0.53},
            {"site": "Pinterest", "url": "https://pinterest.com/johndoe", "status": "found", "response_time": 0.66},
            {"site": "TikTok", "url": "https://tiktok.com/@johndoe", "status": "not_found", "response_time": 0.39},
        ],
    },
}


def _build_scan(spec: dict, started: datetime) -> dict:
    target = spec["target"]
    scan_type = spec["scan_type"]
    results = dict(spec["results"])
    results["opsec_score"] = score_from_results(results)
    results["graph"] = build_graph(target, scan_type, results)

    scan_id = str(uuid.uuid4())
    return {
        "scan_id": scan_id,
        "target": target,
        "scan_type": scan_type,
        "status": "completed",
        "owner": "anonymous",
        "started_at": started.isoformat(),
        "completed_at": (started + timedelta(seconds=18)).isoformat(),
        "progress": [],
        "results": results,
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for old in os.listdir(OUT_DIR):
        if old.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, old))

    base = datetime(2026, 6, 3, 14, 0, 0)
    specs = [DEMO_DOMAIN, DEMO_IP, DEMO_USERNAME]
    for i, spec in enumerate(specs):
        scan = _build_scan(spec, base + timedelta(minutes=7 * i))
        path = os.path.join(OUT_DIR, f"{scan['scan_id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(scan, f, ensure_ascii=False, indent=2, default=str)
        score = scan["results"]["opsec_score"].get("score")
        print(f"  {spec['scan_type']:<9} {spec['target']:<22} OPSEC={score}  -> {os.path.basename(path)}")

    print(f"\nWrote {len(specs)} demo scans to {os.path.relpath(OUT_DIR)}")


if __name__ == "__main__":
    main()
