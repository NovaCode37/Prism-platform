import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

class TestCertTransparency:
    def test_parse_subdomains(self):
        from modules.cert_transparency import CertTransparency
        ct = CertTransparency()
        domain = "example.com"
        fake_certs = [
            {"id": 1, "entry_timestamp": "2024-01-01T00:00:00", "not_before": "2024-01-01",
             "not_after": "2025-01-01", "common_name": "example.com",
             "issuer_name": "O=Let's Encrypt,C=US",
             "name_value": "example.com\nwww.example.com\napi.example.com"},
            {"id": 2, "entry_timestamp": "2024-06-01T00:00:00", "not_before": "2024-06-01",
             "not_after": "2025-06-01", "common_name": "*.example.com",
             "issuer_name": "O=DigiCert,C=US",
             "name_value": "*.example.com\nmail.example.com"},
        ]

        subdomains = set()
        for cert in fake_certs:
            for name in cert["name_value"].split("\n"):
                name = name.strip().lower()
                if name and domain in name:
                    if name.startswith("*."):
                        name = name[2:]
                    subdomains.add(name)

        assert "www.example.com" in subdomains
        assert "api.example.com" in subdomains
        assert "mail.example.com" in subdomains
        assert "example.com" in subdomains

    def test_result_structure(self, monkeypatch):
        from modules.cert_transparency import CertTransparency
        import requests

        ct = CertTransparency()

        class MockResponse:
            status_code = 200
            def json(self):
                return [
                    {"id": 1, "entry_timestamp": "2024-01-01T00:00:00",
                     "not_before": "2024-01-01", "not_after": "2025-01-01",
                     "common_name": "test.com", "issuer_name": "O=Test CA",
                     "name_value": "test.com\nsub.test.com"}
                ]

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResponse())
        result = ct.search("test.com")

        assert result["domain"] == "test.com"
        assert isinstance(result["subdomains"], list)
        assert result["error"] is None
        assert result["total_certs"] > 0
        assert "sub.test.com" in result["subdomains"]

    def test_error_on_bad_status(self, monkeypatch):
        from modules.cert_transparency import CertTransparency
        import requests

        class MockBadResponse:
            status_code = 503
            def json(self):
                return []

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockBadResponse())
        result = CertTransparency().search("test.com")
        assert result["error"] is not None

class TestOpsecScore:
    def test_perfect_score_empty_results(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        result = scorer.calculate()
        assert result["score"] == 100
        assert result["risk_level"] == "MINIMAL"
        assert len(result["all_findings"]) == 0

    def test_breach_deduction(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_leaks({"breach_count": 3, "breaches": ["Adobe", "LinkedIn", "MySpace"]})
        result = scorer.calculate()
        assert result["score"] < 100
        assert any(f["severity"] == "HIGH" for f in result["all_findings"])

    def test_critical_breach_deduction(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_leaks({"breach_count": 8, "breaches": ["A","B","C","D","E","F","G","H"]})
        result = scorer.calculate()
        assert result["score"] < 80
        assert any(f["severity"] == "CRITICAL" for f in result["all_findings"])

    def test_virustotal_malicious(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_virustotal({"malicious": 10, "suspicious": 0, "harmless": 50})
        result = scorer.calculate()
        assert result["score"] < 80

    def test_many_platforms_deduction(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        found = [{"status": "found", "site": f"site{i}"} for i in range(25)]
        scorer.process_blackbird(found)
        result = scorer.calculate()
        assert result["score"] < 100

    def test_shodan_cves_critical(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_shodan({
            "ip": "1.2.3.4", "open_ports": [22, 80, 443, 3306, 5432],
            "vulns": ["CVE-2021-44228", "CVE-2022-26134"], "services": [],
            "error": None
        })
        result = scorer.calculate()
        assert any(f["severity"] == "CRITICAL" for f in result["all_findings"])

    def test_score_from_results_convenience(self):
        from modules.opsec_score import score_from_results
        results = {
            "breaches": {"breach_count": 2, "breaches": ["A", "B"]},
            "blackbird": [{"status": "found", "site": "GitHub"}] * 12,
        }
        result = score_from_results(results)
        assert "score" in result
        assert "risk_level" in result
        assert "categories" in result
        assert result["score"] < 100

    def test_categories_always_present(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        result = scorer.calculate()
        for cat in ("data_exposure", "identity_opsec", "infrastructure", "web_security"):
            assert cat in result["categories"]
            assert "score" in result["categories"][cat]
            assert "max" in result["categories"][cat]

    def test_whois_exposed_emails(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_whois({"emails": ["admin@example.com"], "org": "ACME Corp", "error": None})
        result = scorer.calculate()
        assert result["score"] < 100
        assert len(result["all_findings"]) >= 1

class TestGraphBuilder:
    def test_target_node_always_present(self):
        from modules.graph_builder import build_graph
        graph = build_graph("example.com", "domain", {})
        assert len(graph["nodes"]) >= 1
        target_node = next(n for n in graph["nodes"] if n["type"] == "target")
        assert target_node["full_label"] == "example.com"

    def test_whois_email_node(self):
        from modules.graph_builder import build_graph
        results = {
            "whois": {
                "org": "Test Corp",
                "emails": ["admin@example.com"],
                "name_servers": ["ns1.example.com"],
                "error": None,
            }
        }
        graph = build_graph("example.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        assert "email::admin@example.com" in node_ids
        assert "org::Test Corp" in node_ids

    def test_geoip_ip_node(self):
        from modules.graph_builder import build_graph
        results = {
            "geoip": {
                "ip": "93.184.216.34", "city": "Norwell", "country": "US",
                "country_name": "United States", "org": "AS15133 MCI Communications",
                "error": None,
            }
        }
        graph = build_graph("example.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        assert "ip::93.184.216.34" in node_ids

    def test_ct_subdomain_nodes(self):
        from modules.graph_builder import build_graph
        results = {
            "cert_transparency": {
                "subdomains": ["api.example.com", "mail.example.com", "www.example.com"],
                "total_certs": 10,
                "error": None,
            }
        }
        graph = build_graph("example.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        assert "subdomain::api.example.com" in node_ids

    def test_blackbird_account_nodes(self):
        from modules.graph_builder import build_graph
        results = {
            "blackbird": [
                {"site": "GitHub", "url": "https://github.com/johndoe", "status": "found"},
                {"site": "Twitter/X", "url": "https://x.com/johndoe", "status": "found"},
                {"site": "Reddit", "url": "", "status": "not_found"},
            ]
        }
        graph = build_graph("johndoe", "username", results)
        account_nodes = [n for n in graph["nodes"] if n["type"] == "account"]
        assert len(account_nodes) == 2

    def test_nodes_have_required_fields(self):
        from modules.graph_builder import build_graph
        graph = build_graph("test.com", "domain", {})
        for node in graph["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "type" in node
            assert "color" in node
        for edge in graph["edges"]:
            assert "from" in edge
            assert "to" in edge

class TestReportGenerator:
    def test_generate_html_report(self, tmp_path):
        from modules.report_generator import generate_html_report
        results = {
            "whois": {"domain": "example.com", "registrar": "Test Registrar",
                      "org": "Test Corp", "country": "US",
                      "creation_date": "2010-01-01", "expiration_date": "2030-01-01",
                      "emails": [], "name_servers": [], "error": None},
        }
        opsec = {
            "score": 75, "risk_level": "LOW",
            "categories": {
                "data_exposure": {"score": 35, "max": 35, "percent": 100, "findings": []},
                "identity_opsec": {"score": 25, "max": 25, "percent": 100, "findings": []},
                "infrastructure": {"score": 10, "max": 25, "percent": 40,
                                   "findings": [{"severity": "MEDIUM", "message": "test", "deduction": 15}]},
                "web_security": {"score": 15, "max": 15, "percent": 100, "findings": []},
            },
            "all_findings": [{"category": "infrastructure", "severity": "MEDIUM",
                               "message": "test finding", "deduction": 15}],
        }
        output = str(tmp_path / "report.html")
        path = generate_html_report("example.com", "domain", results, opsec, output)
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "example.com" in content
        assert "OPSEC" in content
        assert "75" in content
        assert "Test Registrar" in content

    def test_report_without_opsec(self, tmp_path):
        from modules.report_generator import generate_html_report
        output = str(tmp_path / "report_no_opsec.html")
        path = generate_html_report("test.com", "domain", {}, None, output)
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "test.com" in content

class TestWayback:
    def test_parse_snapshots(self, monkeypatch):
        from modules.wayback import WaybackMachine
        import requests

        class MockResp:
            status_code = 200
            def json(self):
                return [
                    ["timestamp", "statuscode", "mimetype", "length"],
                    ["20200101120000", "200", "text/html", "12000"],
                    ["20210601090000", "200", "text/html", "15000"],
                ]

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        wb = WaybackMachine()
        result = wb.get_snapshots("example.com")
        assert result["total_snapshots"] == 2
        assert result["error"] is None
        assert "web.archive.org" in result["snapshots"][0]["wayback_url"]

    def test_interesting_url_detection(self, monkeypatch):
        from modules.wayback import WaybackMachine
        import requests

        class MockResp:
            status_code = 200
            def json(self):
                return [
                    ["original"],
                    ["https://example.com/admin"],
                    ["https://example.com/about"],
                    ["https://example.com/login"],
                    ["https://example.com/.env"],
                ]

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        wb = WaybackMachine()
        result = wb.get_all_urls("example.com")
        assert len(result["interesting"]) >= 3

    def test_error_on_bad_status(self, monkeypatch):
        from modules.wayback import WaybackMachine
        import requests

        class MockBadResp:
            status_code = 500
            def json(self):
                return []

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockBadResp())
        result = WaybackMachine().get_snapshots("example.com")
        assert result["error"] is not None

class TestDNSLookup:
    def test_result_structure(self, monkeypatch):
        from modules.extra_tools import DNSLookup
        import dns.resolver

        class MockAnswer:
            def __iter__(self):
                return iter([type('R', (), {'__str__': lambda self: '93.184.216.34'})() ])

        def mock_resolve(domain, rtype):
            if rtype == 'A':
                return MockAnswer()
            raise dns.resolver.NoAnswer()

        monkeypatch.setattr(dns.resolver, "resolve", mock_resolve)
        result = DNSLookup().lookup("example.com", ['A'])
        assert result["domain"] == "example.com"
        assert "A" in result["records"]
        assert result["records"]["A"] == ["93.184.216.34"]

class TestWebsiteAnalyzer:
    def test_tech_detection(self):
        from modules.extra_tools import WebsiteAnalyzer
        analyzer = WebsiteAnalyzer()
        html = """
        <html><head><script src="/wp-content/themes/test.js"></script>
        <script src="jquery.min.js"></script></head>
        <body><title>Test Site</title></body></html>
        """
        techs = analyzer._detect_technologies(html, {"Server": "nginx/1.18", "X-Powered-By": "PHP/8.0"})
        assert "WordPress" in techs
        assert "jQuery" in techs
        assert "Nginx" in techs
        assert "PHP" in techs

    def test_social_links_extraction(self):
        from modules.extra_tools import WebsiteAnalyzer
        html = """
        <a href="https://github.com/johndoe">GitHub</a>
        <a href="https://twitter.com/johndoe">Twitter</a>
        <a href="https://www.linkedin.com/in/johndoe">LinkedIn</a>
        """
        links = WebsiteAnalyzer()._extract_social_links(html)
        platforms = {l["platform"] for l in links}
        assert "GitHub" in platforms
        assert "Twitter/X" in platforms
        assert "LinkedIn" in platforms
