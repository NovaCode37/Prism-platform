import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestOnionChecker:
    def test_returns_error_on_empty_target(self):
        from modules.onion_checker import OnionChecker
        from modules.module_status import classify, ERROR
        result = OnionChecker().check("")
        assert classify(result) == ERROR
        assert result["error"] == "empty target"

    def test_aggregates_unique_relevant_results(self, monkeypatch):
        from modules.onion_checker import OnionChecker
        from modules.module_status import classify, OK

        oc = OnionChecker()
        monkeypatch.setattr(
            oc, "_search_ahmia",
            lambda q, session=None: ([
                {"source": "ahmia", "url": "http://abc.onion", "snippet": "example.com leak dump"},
                {"source": "ahmia", "url": "http://xyz.onion", "snippet": "example.com credentials"},
                {"source": "ahmia", "url": "http://unrelated.onion", "snippet": "random market"},
            ], None),
        )

        result = oc.check("example.com")
        assert classify(result) == OK
        assert result["error"] is None
        assert result["total_found"] == 2
        urls = {r["url"] for r in result["results"]}
        assert urls == {"http://abc.onion", "http://xyz.onion"}
        assert "http://unrelated.onion" not in urls
        assert result["sources"] == {"ahmia": 3}

    def test_ahmia_token_extraction_and_search(self, monkeypatch):
        import requests
        from modules.onion_checker import OnionChecker
        from modules.module_status import classify, OK

        class MockResp:
            def __init__(self, text, status_code=200):
                self.text = text
                self.status_code = status_code

        def fake_get(self, url, params=None, *a, **k):
            if "search" in url:
                assert params is not None
                assert params.get("q") == "bitcoin"
                assert params.get("85f590") == "986a59"
                html = '<li class="result"><a href="http://bitcoindump56charsxyz.onion/info">dump</a></li>'
                return MockResp(html)
            # home page with rotating hidden token
            return MockResp('<html><form action="/search/"><input type="hidden" name="85f590" value="986a59"></form></html>')

        monkeypatch.setattr(requests.Session, "get", fake_get)
        oc = OnionChecker(timeout=5)
        result = oc.check("bitcoin")
        assert classify(result) == OK
        assert result["total_found"] == 1
        assert result["results"][0]["url"] == "http://bitcoindump56charsxyz.onion/info"

    def test_ahmia_failure_reports_error_status(self, monkeypatch):
        import requests
        from modules.onion_checker import OnionChecker
        from modules.module_status import classify, ERROR

        def raise_network(*a, **k):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setattr(requests.Session, "get", raise_network)
        result = OnionChecker(timeout=1).check("example.com")

        assert classify(result) == ERROR
        assert result["error"] is not None
        assert "Ahmia request failed" in result["error"]
        assert result["total_found"] == 0


class TestCensysLookup:
    def test_no_credentials_returns_skipped(self):
        from modules.censys_lookup import CensysLookup
        from modules.module_status import classify, SKIPPED
        cl = CensysLookup()
        cl.pat = ""
        cl.org_id = ""
        result = cl.search_ip("8.8.8.8")
        assert classify(result) == SKIPPED
        assert result.get("error") is None
        assert "API key" in result.get("status_reason", "")

    def test_search_ip_success(self, monkeypatch):
        import requests
        from modules.censys_lookup import CensysLookup

        class MockResp:
            status_code = 200
            def json(self):
                return {"result": {"resource": {
                    "ip": "8.8.8.8",
                    "autonomous_system": {"asn": 15169, "name": "GOOGLE"},
                    "location": {"country": "US", "city": "Mountain View"},
                    "services": [
                        {"port": 80, "protocol": "HTTP", "transport_protocol": "TCP"},
                        {"port": 443, "protocol": "HTTPS", "transport_protocol": "TCP"},
                    ],
                }}}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        cl = CensysLookup()
        cl.pat = "censys_token"
        cl.org_id = "org123"
        result = cl.search_ip("8.8.8.8")
        assert result["error"] is None
        assert result["asn"] == 15169
        assert result["country"] == "US"
        assert 80 in result["open_ports"]
        assert 443 in result["open_ports"]
        assert result["total"] == 2

    def test_search_ip_invalid_credentials(self, monkeypatch):
        import requests
        from modules.censys_lookup import CensysLookup

        class MockResp:
            status_code = 401
            def json(self):
                return {}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        cl = CensysLookup()
        cl.pat = "censys_token"
        cl.org_id = "org123"
        result = cl.search_ip("1.2.3.4")
        assert "Invalid Censys token" in (result.get("error") or "")

    def test_search_domain_skipped_on_platform(self):
        from modules.censys_lookup import CensysLookup
        from modules.module_status import classify, SKIPPED
        cl = CensysLookup()
        cl.pat = "censys_token"
        cl.org_id = "org123"
        result = cl.search_domain("example.com")
        assert classify(result) == SKIPPED


class TestPdfReport:
    def test_pdf_generation_requires_xhtml2pdf(self, monkeypatch):
        import builtins

        from modules.report_generator import generate_pdf_report

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "xhtml2pdf" or name.startswith("xhtml2pdf."):
                raise ImportError("xhtml2pdf not installed")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(ImportError, match="xhtml2pdf"):
            generate_pdf_report("example.com", "domain", {}, None)
