import sys
import os
import json
import hashlib
import pytest
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

class TestEmailRepLookup:
    def test_lookup_high_reputation(self, monkeypatch):
        import dns.resolver
        import requests
        from modules.hunter import EmailRepLookup

        class MXAnswer:
            def __iter__(self):
                return iter([type('R', (), {
                    'preference': 10,
                    'exchange': type('E', (), {'__str__': lambda s: 'mail.example.com.'})()
                })()])

        class TXTAnswerSPF:
            def __iter__(self):
                return iter([type('R', (), {'__str__': lambda s: '"v=spf1 include:_spf.google.com ~all"'})() ])

        class TXTAnswerDMARC:
            def __iter__(self):
                return iter([type('R', (), {'__str__': lambda s: '"v=DMARC1; p=reject"'})() ])

        def mock_resolve(domain, rtype):
            if rtype == "MX":
                return MXAnswer()
            if rtype == "TXT":
                if domain.startswith("_dmarc."):
                    return TXTAnswerDMARC()
                return TXTAnswerSPF()
            raise dns.resolver.NoAnswer()

        monkeypatch.setattr(dns.resolver, "resolve", mock_resolve)

        class MockKickbox:
            status_code = 200
            def json(self):
                return {"disposable": False}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockKickbox())

        import socket
        monkeypatch.setattr(socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(OSError("mocked")))

        er = EmailRepLookup()
        result = er.lookup("test@example.com")

        assert result["email"] == "test@example.com"
        assert result["valid_mx"] is True
        assert result["spf"] is True
        assert result["dmarc"] is True
        assert result["spoofable"] is False
        assert result["disposable"] is False
        assert result["reputation"] == "high"
        assert result["domain_reputation"] == "high"
        assert result["error"] is None

    def test_lookup_no_mx(self, monkeypatch):
        import dns.resolver
        import requests
        from modules.hunter import EmailRepLookup

        def mock_resolve(domain, rtype):
            raise dns.resolver.NoAnswer()

        monkeypatch.setattr(dns.resolver, "resolve", mock_resolve)

        class MockKickbox:
            status_code = 200
            def json(self):
                return {"disposable": False}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockKickbox())

        result = EmailRepLookup().lookup("bad@nxdomain.fake")
        assert result["valid_mx"] is False
        assert result["suspicious"] is True
        assert result["reputation"] in ("low", "medium")

    def test_lookup_disposable(self, monkeypatch):
        import dns.resolver
        import requests
        from modules.hunter import EmailRepLookup

        class MXAnswer:
            def __iter__(self):
                return iter([type('R', (), {
                    'preference': 10,
                    'exchange': type('E', (), {'__str__': lambda s: 'mx.tempmail.com.'})()
                })()])

        def mock_resolve(domain, rtype):
            if rtype == "MX":
                return MXAnswer()
            raise dns.resolver.NoAnswer()

        monkeypatch.setattr(dns.resolver, "resolve", mock_resolve)

        class MockKickbox:
            status_code = 200
            def json(self):
                return {"disposable": True}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockKickbox())

        import socket
        monkeypatch.setattr(socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(OSError("mocked")))

        result = EmailRepLookup().lookup("x@tempmail.com")
        assert result["disposable"] is True
        assert result["suspicious"] is True

    def test_free_provider_detection(self):
        from modules.hunter import EmailRepLookup, FREE_PROVIDERS
        er = EmailRepLookup()
        assert "gmail.com" in FREE_PROVIDERS
        assert "protonmail.com" in FREE_PROVIDERS
        assert "somecorp.com" not in FREE_PROVIDERS

    def test_lookup_dns_failures_graceful(self, monkeypatch):
        import dns.resolver
        import requests
        from modules.hunter import EmailRepLookup

        def mock_resolve(domain, rtype):
            raise dns.resolver.NoAnswer()

        monkeypatch.setattr(dns.resolver, "resolve", mock_resolve)

        class MockKickbox:
            status_code = 200
            def json(self):
                return {"disposable": False}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockKickbox())

        result = EmailRepLookup().lookup("x@fail.com")
        assert result["error"] is None
        assert result["valid_mx"] is False
        assert result["spf"] is False
        assert result["suspicious"] is True



class TestSMTPVerifier:
    def test_validate_email_format_valid(self):
        from modules.smtp_verify import SMTPVerifier
        v = SMTPVerifier()
        assert v.validate_email_format("test@example.com") is True
        assert v.validate_email_format("user.name+tag@domain.co.uk") is True

    def test_validate_email_format_invalid(self):
        from modules.smtp_verify import SMTPVerifier
        v = SMTPVerifier()
        assert v.validate_email_format("notanemail") is False
        assert v.validate_email_format("@missing.com") is False
        assert v.validate_email_format("user@") is False
        assert v.validate_email_format("") is False

    def test_verify_invalid_format(self):
        from modules.smtp_verify import SMTPVerifier
        result = SMTPVerifier().verify_email("notanemail")
        assert result["valid_format"] is False
        assert result["error"] == "Invalid email format"

    def test_verify_no_mx(self, monkeypatch):
        import dns.resolver
        from modules.smtp_verify import SMTPVerifier

        def mock_resolve(domain, rtype):
            raise dns.resolver.NXDOMAIN()

        monkeypatch.setattr(dns.resolver, "resolve", mock_resolve)

        result = SMTPVerifier().verify_email("user@nonexistent.fake")
        assert result["valid_format"] is True
        assert result["mx_found"] is False
        assert result["error"] == "Domain has no mail server"

    def test_verify_with_mx_smtp_fail(self, monkeypatch):
        import dns.resolver
        import smtplib
        from modules.smtp_verify import SMTPVerifier

        class MXAnswer:
            def __iter__(self):
                return iter([type('R', (), {
                    'preference': 10,
                    'exchange': type('E', (), {'__str__': lambda s: 'mail.test.com.'})()
                })()])

        def mock_resolve(domain, rtype):
            if rtype == "MX":
                return MXAnswer()
            raise dns.resolver.NoAnswer()

        monkeypatch.setattr(dns.resolver, "resolve", mock_resolve)

        class MockSMTP:
            def __init__(self, timeout=10):
                pass
            def connect(self, host):
                raise smtplib.SMTPConnectError(421, "Connection refused")
            def quit(self):
                pass

        monkeypatch.setattr(smtplib, "SMTP", MockSMTP)

        result = SMTPVerifier().verify_email("user@test.com")
        assert result["mx_found"] is True
        assert result["smtp_connect"] is False

    def test_disposable_detection(self):
        from modules.smtp_verify import SMTPVerifier
        v = SMTPVerifier()
        assert v._check_disposable("mailinator.com") is True
        assert v._check_disposable("yopmail.com") is True
        assert v._check_disposable("gmail.com") is False
        assert v._check_disposable("company.com") is False



class TestHLRLookup:
    def test_validate_valid_phone(self):
        from modules.hlr_lookup import HLRLookup
        hlr = HLRLookup()
        result = hlr.validate_phone("+14155552671")
        assert result["valid"] is True
        assert result["country_code"] == "US"
        assert result["error"] is None
        assert result["country"] is not None and len(result["country"]) > 0

    def test_validate_phone_with_country_code(self):
        from modules.hlr_lookup import HLRLookup
        result = HLRLookup().validate_phone("9001234567", "RU")
        assert result["valid"] is True
        assert result["country_code"] == "RU"

    def test_validate_invalid_phone(self):
        from modules.hlr_lookup import HLRLookup
        result = HLRLookup().validate_phone("+0000000")
        assert result["valid"] is False

    def test_auto_prepend_plus(self):
        from modules.hlr_lookup import HLRLookup
        result = HLRLookup().validate_phone("14155552671")
        assert result["valid"] is True

    def test_region_is_english(self):
        from modules.hlr_lookup import HLRLookup
        result = HLRLookup().validate_phone("+43800901051")
        assert result["error"] is None
        if result["region"]:
            assert all(ord(c) < 128 or c in ' -()' for c in result["region"]), \
                f"Region contains non-ASCII chars (possibly Russian): {result['region']}"

    def test_parse_error(self):
        from modules.hlr_lookup import HLRLookup
        result = HLRLookup().validate_phone("not_a_phone")
        assert result["error"] is not None
        assert "Parse error" in result["error"] or "error" in result["error"].lower()

    def test_timezones_returned(self):
        from modules.hlr_lookup import HLRLookup
        result = HLRLookup().validate_phone("+14155552671")
        assert isinstance(result["timezones"], list)
        assert len(result["timezones"]) > 0

    def test_line_type_detected(self):
        from modules.hlr_lookup import HLRLookup
        result = HLRLookup().validate_phone("+14155552671")
        assert result["line_type"] is not None
        assert result["line_type"] != "Unknown"

    def test_country_and_region_differ(self):
        from modules.hlr_lookup import HLRLookup
        result = HLRLookup().validate_phone("+14155552671")
        assert result["country"] == "United States"
        assert result["region"] != result["country"]

    def test_country_name_for_known_codes(self):
        from modules.hlr_lookup import HLRLookup
        result = HLRLookup().validate_phone("+43800901051")
        assert result["country"] == "Austria"
        assert result["country_code"] == "AT"



class TestLeakLookup:
    def test_check_email_hibp_not_found(self, monkeypatch):
        import requests
        from modules.leak_lookup import LeakLookup

        class MockResp:
            status_code = 404
            def json(self):
                return []

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        result = LeakLookup().check_email_hibp("clean@example.com")
        assert result["breached"] is False
        assert result["total_breaches"] == 0
        assert result["error"] is None

    def test_check_email_hibp_found(self, monkeypatch):
        import requests
        from modules.leak_lookup import LeakLookup

        class MockResp:
            status_code = 200
            def json(self):
                return [
                    {"Name": "Adobe", "Title": "Adobe", "Domain": "adobe.com",
                     "BreachDate": "2013-10-04", "AddedDate": "2013-12-04",
                     "PwnCount": 152445165, "DataClasses": ["Emails", "Passwords"],
                     "IsVerified": True, "IsSensitive": False},
                ]

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        result = LeakLookup().check_email_hibp("breached@example.com")
        assert result["breached"] is True
        assert result["total_breaches"] == 1
        assert result["breaches"][0]["name"] == "Adobe"

    def test_check_email_hibp_401(self, monkeypatch):
        import requests
        from modules.leak_lookup import LeakLookup

        class MockResp:
            status_code = 401
            def json(self):
                return {}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        result = LeakLookup().check_email_hibp("x@example.com")
        assert result["error"] is not None
        assert "API key" in result["error"]

    def test_check_password_pwned(self, monkeypatch):
        import requests
        from modules.leak_lookup import LeakLookup

        test_password = "password123"
        sha1 = hashlib.sha1(test_password.encode()).hexdigest().upper()
        suffix = sha1[5:]

        class MockResp:
            status_code = 200
            text = f"{suffix}:9999\nABCDE12345:1\n"

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        result = LeakLookup().check_password_pwned(test_password)
        assert result["pwned"] is True
        assert result["count"] == 9999

    def test_check_password_not_pwned(self, monkeypatch):
        import requests
        from modules.leak_lookup import LeakLookup

        class MockResp:
            status_code = 200
            text = "ABCDE12345:1\nFEDCB54321:2\n"

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        result = LeakLookup().check_password_pwned("s0me_v3ry_un1que_p@ss!")
        assert result["pwned"] is False
        assert result["count"] == 0

    def test_leak_lookup_no_api_key(self, monkeypatch):
        from modules.leak_lookup import LeakLookup
        ll = LeakLookup()
        ll.leak_lookup_key = ""
        result = ll.check_leak_lookup("test@example.com")
        assert result["error"] is not None
        assert "not configured" in result["error"]

    def test_check_email_full_structure(self, monkeypatch):
        import requests
        from modules.leak_lookup import LeakLookup

        class MockResp:
            status_code = 404
            def json(self):
                return []

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())

        ll = LeakLookup()
        ll.leak_lookup_key = ""
        result = ll.check_email_full("test@example.com")

        assert "email" in result
        assert "hibp" in result
        assert "total_breaches" in result
        assert "is_compromised" in result
        assert result["is_compromised"] is False



class TestVirusTotal:
    def test_no_api_key(self, monkeypatch):
        from modules.threat_intel import VirusTotal
        monkeypatch.setattr("modules.threat_intel.VIRUSTOTAL_API_KEY", "")
        vt = VirusTotal()
        result = vt.check_ip("1.2.3.4")
        assert result["error"] is not None
        assert "not set" in result["error"]

    def test_check_ip_success(self, monkeypatch):
        import requests
        from modules.threat_intel import VirusTotal

        class MockResp:
            status_code = 200
            def json(self):
                return {"data": {"attributes": {
                    "last_analysis_stats": {"malicious": 0, "suspicious": 0, "harmless": 62, "undetected": 5},
                    "country": "US", "asn": 15169, "as_owner": "GOOGLE", "reputation": 0, "tags": [],
                }}}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        monkeypatch.setattr("modules.threat_intel.VIRUSTOTAL_API_KEY", "fakekey")
        vt = VirusTotal()
        result = vt.check_ip("8.8.8.8")
        assert result["error"] is None
        assert result["malicious"] == 0
        assert result["country"] == "US"
        assert result["as_owner"] == "GOOGLE"

    def test_check_domain_success(self, monkeypatch):
        import requests
        from modules.threat_intel import VirusTotal

        class MockResp:
            status_code = 200
            def json(self):
                return {"data": {"attributes": {
                    "last_analysis_stats": {"malicious": 1, "suspicious": 2, "harmless": 50, "undetected": 10},
                    "reputation": -5, "categories": {"Forcepoint": "malware"}, "tags": ["phishing"],
                }}}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        monkeypatch.setattr("modules.threat_intel.VIRUSTOTAL_API_KEY", "fakekey")
        vt = VirusTotal()
        result = vt.check_domain("evil.com")
        assert result["malicious"] == 1
        assert result["suspicious"] == 2
        assert result["error"] is None

    def test_check_ip_404(self, monkeypatch):
        import requests
        from modules.threat_intel import VirusTotal

        class MockResp:
            status_code = 404
            text = "Not found"
            def json(self):
                return {}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        monkeypatch.setattr("modules.threat_intel.VIRUSTOTAL_API_KEY", "fakekey")
        vt = VirusTotal()
        result = vt.check_ip("0.0.0.0")
        assert result["error"] is not None



class TestAbuseIPDB:
    def test_no_api_key(self, monkeypatch):
        from modules.threat_intel import AbuseIPDB
        monkeypatch.setattr("modules.threat_intel.ABUSEIPDB_API_KEY", "")
        adb = AbuseIPDB()
        result = adb.check_ip("1.2.3.4")
        assert result["error"] is not None

    def test_check_ip_success(self, monkeypatch):
        import requests
        from modules.threat_intel import AbuseIPDB

        class MockResp:
            status_code = 200
            def json(self):
                return {"data": {
                    "abuseConfidenceScore": 75,
                    "totalReports": 42,
                    "countryCode": "CN",
                    "isp": "Some ISP",
                    "domain": "example.cn",
                    "isTor": True,
                    "isPublic": True,
                    "usageType": "Data Center",
                    "lastReportedAt": "2024-01-15T12:00:00Z",
                }}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        monkeypatch.setattr("modules.threat_intel.ABUSEIPDB_API_KEY", "fakekey")
        adb = AbuseIPDB()
        result = adb.check_ip("1.2.3.4")
        assert result["abuse_score"] == 75
        assert result["total_reports"] == 42
        assert result["is_tor"] is True
        assert result["country"] == "CN"
        assert result["error"] is None



class TestBlackbird:
    def test_sites_dict_not_empty(self):
        from modules.blackbird import Blackbird
        assert len(Blackbird.SITES) > 30

    def test_site_result_dataclass(self):
        from modules.blackbird import SiteResult
        r = SiteResult(site="GitHub", url="https://github.com/test", status="found", http_code=200, response_time=0.5)
        assert r.site == "GitHub"
        assert r.status == "found"
        assert r.response_time == 0.5

    def test_get_found_filters(self):
        from modules.blackbird import Blackbird, SiteResult
        bb = Blackbird()
        bb.results = [
            SiteResult("GitHub", "https://github.com/test", "found", 200, 0.5),
            SiteResult("Reddit", "https://reddit.com/user/test", "not_found", 404, 0.3),
            SiteResult("Twitter/X", "https://x.com/test", "found", 200, 0.8),
            SiteResult("TikTok", "https://tiktok.com/@test", "error", 0, 0.0),
        ]
        found = bb.get_found()
        assert len(found) == 2
        assert all(r.status == "found" for r in found)

    def test_export_json(self, tmp_path):
        from modules.blackbird import Blackbird, SiteResult
        bb = Blackbird()
        bb.results = [
            SiteResult("GitHub", "https://github.com/testuser", "found", 200, 0.5),
            SiteResult("Reddit", "https://reddit.com/user/testuser", "not_found", 404, 0.3),
        ]
        filepath = str(tmp_path / "test_export.json")
        result_path = bb.export_json("testuser", filepath)
        assert os.path.exists(result_path)
        with open(result_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["username"] == "testuser"
        assert data["total_found"] == 1
        assert data["total_checked"] == 2

    def test_export_csv(self, tmp_path):
        from modules.blackbird import Blackbird, SiteResult
        bb = Blackbird()
        bb.results = [
            SiteResult("GitHub", "https://github.com/testuser", "found", 200, 0.5),
        ]
        filepath = str(tmp_path / "test_export.csv")
        result_path = bb.export_csv("testuser", filepath)
        assert os.path.exists(result_path)
        with open(result_path, encoding="utf-8") as f:
            content = f.read()
        assert "GitHub" in content
        assert "found" in content

    def test_export_html_xss_safe(self, tmp_path):
        from modules.blackbird import Blackbird, SiteResult
        bb = Blackbird()
        bb.results = [
            SiteResult('<script>alert(1)</script>', 'https://evil.com/<img onerror=alert(1)>', "found", 200, 0.5),
        ]
        filepath = str(tmp_path / "test_xss.html")
        bb.export_html("testuser", filepath)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;" in content

    def test_export_txt(self, tmp_path):
        from modules.blackbird import Blackbird, SiteResult
        bb = Blackbird()
        bb.results = [
            SiteResult("GitHub", "https://github.com/test", "found", 200, 0.5),
        ]
        filepath = str(tmp_path / "test.txt")
        bb.export_txt("test", filepath)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        assert "[+] GitHub" in content



class TestCryptoLookup:
    def test_detect_bitcoin_legacy(self):
        from modules.crypto_lookup import CryptoLookup
        cl = CryptoLookup()
        assert cl.detect_type("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") == "bitcoin"

    def test_detect_bitcoin_segwit(self):
        from modules.crypto_lookup import CryptoLookup
        cl = CryptoLookup()
        assert cl.detect_type("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4") == "bitcoin"

    def test_detect_ethereum(self):
        from modules.crypto_lookup import CryptoLookup
        cl = CryptoLookup()
        assert cl.detect_type("0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68") == "ethereum"

    def test_detect_unknown(self):
        from modules.crypto_lookup import CryptoLookup
        cl = CryptoLookup()
        assert cl.detect_type("not_a_crypto_address") == "unknown"
        assert cl.detect_type("") == "unknown"



class TestEmailHeaderAnalyzer:
    def test_parse_received_ip_skips_private(self):
        from modules.email_header_analyzer import _parse_received_ip
        assert _parse_received_ip("from mail.example.com (10.0.0.1)") is None
        assert _parse_received_ip("from mail.example.com (127.0.0.1)") is None
        assert _parse_received_ip("from mail.example.com (192.168.1.1)") is None

    def test_parse_received_ip_returns_public(self):
        from modules.email_header_analyzer import _parse_received_ip
        result = _parse_received_ip("from mail.example.com (203.0.113.5)")
        assert result == "203.0.113.5"

    def test_parse_received_ip_no_ip(self):
        from modules.email_header_analyzer import _parse_received_ip
        assert _parse_received_ip("from localhost by localhost") is None

    def test_parse_received_ip_allows_public_172(self):
        from modules.email_header_analyzer import _parse_received_ip
        assert _parse_received_ip("from mail.example.com (172.200.1.1)") == "172.200.1.1"
        assert _parse_received_ip("from mail.example.com (172.16.0.1)") is None
        assert _parse_received_ip("from mail.example.com (172.31.255.1)") is None

    def test_parse_received_ip_allows_public_192(self):
        from modules.email_header_analyzer import _parse_received_ip
        assert _parse_received_ip("from mail.example.com (192.0.2.1)") == "192.0.2.1"
        assert _parse_received_ip("from mail.example.com (192.168.1.1)") is None



class TestOpsecScoreExtended:
    def test_smtp_active_deduction(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_smtp({"exists": True})
        result = scorer.calculate()
        assert result["score"] < 100
        assert any("SMTP" in f["message"] for f in result["all_findings"])

    def test_website_http_deduction(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_website({"url": "http://example.com", "headers": {}, "emails": [], "technologies": []})
        result = scorer.calculate()
        assert result["score"] < 100
        assert any("HTTP" in f["message"] for f in result["all_findings"])

    def test_website_missing_headers(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_website({"url": "https://example.com", "headers": {"Server": "nginx"}, "emails": [], "technologies": []})
        result = scorer.calculate()
        assert any("security headers" in f["message"].lower() for f in result["all_findings"])

    def test_wayback_sensitive_urls(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_wayback({"interesting": ["a", "b", "c", "d", "e"], "error": None})
        result = scorer.calculate()
        assert result["score"] < 100
        assert any("Wayback" in f["message"] for f in result["all_findings"])

    def test_abuseipdb_tor_deduction(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_abuseipdb({"abuse_score": 90, "is_tor": True})
        result = scorer.calculate()
        assert any("TOR" in f["message"] for f in result["all_findings"])

    def test_dns_no_spf_deduction(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_dns({"records": {"TXT": ["google-site-verification=xyz"]}, "error": None})
        result = scorer.calculate()
        assert any("SPF" in f["message"] for f in result["all_findings"])

    def test_cert_transparency_many_subdomains(self):
        from modules.opsec_score import OpsecScorer
        scorer = OpsecScorer()
        scorer.process_cert_transparency({"subdomains": [f"sub{i}.example.com" for i in range(25)], "error": None})
        result = scorer.calculate()
        assert any("subdomain" in f["message"].lower() for f in result["all_findings"])

    def test_score_from_results_all_modules(self):
        from modules.opsec_score import score_from_results
        results = {
            "breaches": {"breach_count": 2, "breaches": ["A", "B"]},
            "smtp": {"exists": True},
            "virustotal": {"malicious": 3, "suspicious": 0},
            "abuseipdb": {"abuse_score": 50, "is_tor": False},
            "blackbird": [{"status": "found", "site": f"site{i}"} for i in range(15)],
            "whois": {"emails": ["admin@test.com"], "org": "Test Corp", "error": None},
            "shodan": {"open_ports": [22, 80, 443], "vulns": [], "error": None},
            "cert_transparency": {"subdomains": ["a.test.com", "b.test.com"], "error": None},
            "dns": {"records": {"TXT": ["v=spf1 include:_spf.google.com ~all"]}, "error": None},
            "website": {"url": "https://test.com", "headers": {"X-Frame-Options": "DENY"}, "emails": ["a@test.com"], "technologies": []},
            "wayback": {"interesting": ["admin", "login"], "error": None},
        }
        result = score_from_results(results)
        assert result["score"] < 100
        assert result["risk_level"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL")
        assert len(result["all_findings"]) > 0



class TestGraphBuilderExtended:
    def test_phone_graph(self):
        from modules.graph_builder import build_graph
        results = {
            "phone": {
                "valid": True, "country": "Austria", "carrier": "T-Mobile",
                "timezones": ["Europe/Vienna"], "error": None,
            }
        }
        graph = build_graph("+43800901051", "phone", results)
        assert len(graph["nodes"]) >= 1
        target = next(n for n in graph["nodes"] if n["type"] == "target")
        assert "+43800901051" in target["full_label"]

    def test_email_graph(self):
        from modules.graph_builder import build_graph
        results = {
            "emailrep": {
                "email": "test@example.com", "valid_mx": True, "spf": True,
                "dmarc": True, "reputation": "high", "error": None,
            }
        }
        graph = build_graph("test@example.com", "email", results)
        assert len(graph["nodes"]) >= 1

    def test_empty_results_no_crash(self):
        from modules.graph_builder import build_graph
        for scan_type in ["domain", "ip", "email", "phone", "username"]:
            graph = build_graph("target", scan_type, {})
            assert "nodes" in graph
            assert "edges" in graph
