import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestOnionChecker:
    def test_returns_error_on_empty_target(self):
        from modules.onion_checker import OnionChecker
        result = OnionChecker().check("")
        assert result["error"] == "empty target"

    def test_aggregates_unique_results(self, monkeypatch):
        from modules.onion_checker import OnionChecker

        oc = OnionChecker()
        monkeypatch.setattr(
            oc, "_search_ahmia",
            lambda q: [{"source": "ahmia", "url": "http://abc.onion"}],
        )
        monkeypatch.setattr(
            oc, "_search_darksearch",
            lambda q: [
                {"source": "darksearch", "url": "http://abc.onion"},
                {"source": "darksearch", "url": "http://xyz.onion", "title": "x"},
            ],
        )

        result = oc.check("example.com")
        assert result["error"] is None
        assert result["total_found"] == 2
        urls = {r["url"] for r in result["results"]}
        assert urls == {"http://abc.onion", "http://xyz.onion"}
        assert result["sources"] == {"ahmia": 1, "darksearch": 2}

    def test_ahmia_network_failure_handled(self, monkeypatch):
        import requests
        from modules.onion_checker import OnionChecker

        def raise_network(*a, **k):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setattr(requests, "get", raise_network)
        result = OnionChecker(timeout=1).check("example.com")
        # Should still succeed with empty results
        assert result["error"] is None
        assert result["total_found"] == 0


class TestCensysLookup:
    def test_no_credentials_returns_error(self, monkeypatch):
        monkeypatch.setattr("modules.censys_lookup.CENSYS_API_ID", "")
        monkeypatch.setattr("modules.censys_lookup.CENSYS_API_SECRET", "")
        from modules.censys_lookup import CensysLookup
        cl = CensysLookup()
        cl.api_id = ""
        cl.api_secret = ""
        result = cl.search_ip("8.8.8.8")
        assert "not set" in (result.get("error") or "")

    def test_search_ip_success(self, monkeypatch):
        import requests
        from modules.censys_lookup import CensysLookup

        class MockResp:
            status_code = 200
            def json(self):
                return {"result": {
                    "autonomous_system": {"asn": 15169, "name": "GOOGLE"},
                    "location": {"country": "US", "city": "Mountain View"},
                    "services": [
                        {"port": 80, "service_name": "HTTP", "transport_protocol": "TCP"},
                        {"port": 443, "service_name": "HTTPS", "transport_protocol": "TCP",
                         "software": [{"product": "nginx"}]},
                    ],
                }}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        cl = CensysLookup()
        cl.api_id = "id"
        cl.api_secret = "secret"
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
        cl.api_id = "id"
        cl.api_secret = "secret"
        result = cl.search_ip("1.2.3.4")
        assert "Invalid Censys credentials" in (result.get("error") or "")

    def test_search_domain_extracts_subdomains(self, monkeypatch):
        import requests
        from modules.censys_lookup import CensysLookup

        class MockResp:
            status_code = 200
            def json(self):
                return {"result": {
                    "hits": [
                        {"fingerprint_sha256": "abc", "names": ["example.com", "*.example.com"]},
                        {"fingerprint_sha256": "def", "names": ["api.example.com", "www.example.com"]},
                    ],
                    "total": 2,
                }}

        monkeypatch.setattr(requests, "post", lambda *a, **k: MockResp())
        cl = CensysLookup()
        cl.api_id = "id"
        cl.api_secret = "secret"
        result = cl.search_domain("example.com")
        assert result["error"] is None
        assert "api.example.com" in result["subdomains"]
        assert "www.example.com" in result["subdomains"]
        assert result["total"] == 2


class TestPdfReport:
    def test_pdf_generation_requires_weasyprint(self, monkeypatch):
        # If weasyprint is installed in the dev env this passes the import,
        # otherwise it raises ImportError with a helpful message.
        from modules.report_generator import generate_pdf_report
        try:
            import weasyprint  # noqa: F401
            installed = True
        except ImportError:
            installed = False

        if not installed:
            with pytest.raises(ImportError, match="weasyprint"):
                generate_pdf_report("example.com", "domain", {}, None)
