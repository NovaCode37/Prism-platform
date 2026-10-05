import sys
import os
import json
import hashlib
import pytest
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

class TestEmailRepLookup:
    @pytest.fixture(autouse=True)
    def _set_hunter_key(self, monkeypatch):
        import modules.hunter as hunter_module
        monkeypatch.setattr(hunter_module, "HUNTER_API_KEY", "test-key", raising=False)

    def test_lookup_high_reputation(self, monkeypatch):
        import dns.resolver
        import requests
        from modules.hunter import EmailRepLookup
        from modules.module_status import ERROR

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
        assert result["status"] == ERROR
        assert result["error"] == "mocked"

    def test_lookup_without_api_key_is_skipped(self, monkeypatch):
        import modules.hunter as hunter_module
        from modules.module_status import SKIPPED

        monkeypatch.setattr(hunter_module, "HUNTER_API_KEY", "")
        monkeypatch.setattr(
            hunter_module.EmailRepLookup,
            "_check_mx",
            lambda *args: (_ for _ in ()).throw(AssertionError("lookup must be skipped")),
        )

        result = hunter_module.EmailRepLookup().lookup("x@example.com")

        assert result["status"] == SKIPPED
        assert result["error"] is None
        assert "HUNTER_API_KEY" in result["status_reason"]

    def test_lookup_failure_is_error(self, monkeypatch):
        from modules.hunter import EmailRepLookup
        from modules.module_status import ERROR

        monkeypatch.setattr(
            EmailRepLookup,
            "_check_mx",
            lambda *args: (_ for _ in ()).throw(RuntimeError("DNS provider failed")),
        )

        result = EmailRepLookup().lookup("x@example.com")

        assert result["status"] == ERROR
        assert result["error"] == "DNS provider failed"

    def test_provider_http_429_is_rate_limited(self, monkeypatch):
        import requests
        import modules.hunter as hunter_module
        from modules.module_status import RATE_LIMITED

        class MockResponse:
            status_code = 429

        monkeypatch.setattr(hunter_module.EmailRepLookup, "_check_mx", lambda *args: [])
        monkeypatch.setattr(hunter_module.EmailRepLookup, "_check_spf", lambda *args: False)
        monkeypatch.setattr(hunter_module.EmailRepLookup, "_check_dmarc", lambda *args: False)
        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockResponse())

        result = hunter_module.EmailRepLookup().lookup("x@example.com")

        assert result["status"] == RATE_LIMITED
        assert result["error"] is None

    def test_provider_http_failure_is_error(self, monkeypatch):
        import requests
        import modules.hunter as hunter_module
        from modules.module_status import ERROR

        class MockResponse:
            status_code = 503

        monkeypatch.setattr(hunter_module.EmailRepLookup, "_check_mx", lambda *args: [])
        monkeypatch.setattr(hunter_module.EmailRepLookup, "_check_spf", lambda *args: False)
        monkeypatch.setattr(hunter_module.EmailRepLookup, "_check_dmarc", lambda *args: False)
        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockResponse())

        result = hunter_module.EmailRepLookup().lookup("x@example.com")

        assert result["status"] == ERROR
        assert "503" in result["error"]

    def test_lookup_no_mx(self, monkeypatch):
        import dns.resolver
        import requests
        from modules.hunter import EmailRepLookup
        from modules.module_status import OK

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
        assert result["status"] == OK
        assert result["error"] is None

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
        from modules.module_status import SKIPPED

        result = SMTPVerifier().verify_email("notanemail")
        assert result["valid_format"] is False
        assert result["status"] == SKIPPED
        assert result["error"] is None
        assert result["status_reason"] == "Invalid email format"

    def test_verify_no_mx(self, monkeypatch):
        import dns.resolver
        from modules.smtp_verify import SMTPVerifier
        from modules.module_status import OK

        def mock_resolve(domain, rtype):
            raise dns.resolver.NXDOMAIN()

        monkeypatch.setattr(dns.resolver, "resolve", mock_resolve)

        result = SMTPVerifier().verify_email("user@nonexistent.fake")
        assert result["valid_format"] is True
        assert result["mx_found"] is False
        assert result["status"] == OK
        assert result["error"] is None
        assert result["status_reason"] == "Domain has no mail server"

    def test_mx_lookup_failure_is_error(self, monkeypatch):
        import dns.resolver
        from modules.smtp_verify import SMTPVerifier
        from modules.module_status import ERROR

        def mock_resolve(domain, rtype):
            raise dns.exception.Timeout("DNS timed out")

        monkeypatch.setattr(dns.resolver, "resolve", mock_resolve)

        result = SMTPVerifier().verify_email("user@example.com")

        assert result["status"] == ERROR
        assert "MX lookup failed" in result["error"]

    def test_verify_with_mx_smtp_fail(self, monkeypatch):
        import dns.resolver
        import smtplib
        from modules.smtp_verify import SMTPVerifier
        from modules.module_status import ERROR

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
        assert result["status"] == ERROR
        assert "Connection error" in result["error"]

    @pytest.mark.parametrize(
        ("response_code", "expected_exists"),
        [(451, None), (550, False)],
    )
    def test_mailbox_refusal_is_a_valid_smtp_answer(self, monkeypatch, response_code, expected_exists):
        import dns.resolver
        import smtplib
        from modules.smtp_verify import SMTPVerifier
        from modules.module_status import OK

        class MXAnswer:
            def __iter__(self):
                return iter([type("R", (), {
                    "preference": 10,
                    "exchange": type("E", (), {"__str__": lambda self: "mail.test.com."})(),
                })()])

        monkeypatch.setattr(dns.resolver, "resolve", lambda *args: MXAnswer())

        class MockSMTP:
            def __init__(self, timeout=10):
                pass
            def connect(self, host):
                return 220, b"ready"
            def ehlo_or_helo_if_needed(self):
                pass
            def mail(self, sender):
                return 250, b"ok"
            def rcpt(self, recipient):
                return response_code, b"mailbox unavailable"
            def quit(self):
                pass

        monkeypatch.setattr(smtplib, "SMTP", MockSMTP)

        result = SMTPVerifier().verify_email("missing@test.com")

        assert result["exists"] is expected_exists
        assert result["status"] == OK
        assert result["error"] is None

    def test_smtp_protocol_failure_is_error(self, monkeypatch):
        import dns.resolver
        import smtplib
        from modules.smtp_verify import SMTPVerifier
        from modules.module_status import ERROR

        class MXAnswer:
            def __iter__(self):
                return iter([type("R", (), {
                    "preference": 10,
                    "exchange": type("E", (), {"__str__": lambda self: "mail.test.com."})(),
                })()])

        monkeypatch.setattr(dns.resolver, "resolve", lambda *args: MXAnswer())

        class MockSMTP:
            def __init__(self, timeout=10):
                pass
            def connect(self, host):
                return 220, b"ready"
            def ehlo_or_helo_if_needed(self):
                raise smtplib.SMTPServerDisconnected("protocol closed")

        monkeypatch.setattr(smtplib, "SMTP", MockSMTP)

        result = SMTPVerifier().verify_email("user@test.com")

        assert result["status"] == ERROR
        assert "Server disconnected" in result["error"]

    def test_disposable_detection(self):
        from modules.smtp_verify import SMTPVerifier
        v = SMTPVerifier()
        assert v._check_disposable("mailinator.com") is True
        assert v._check_disposable("yopmail.com") is True
        assert v._check_disposable("gmail.com") is False
        assert v._check_disposable("company.com") is False

class TestCryptoLookupStatuses:
    def _lookup_with_status(self, monkeypatch, status_code):
        from modules.crypto_lookup import CryptoLookup

        class MockResponse:
            def __init__(self):
                self.status_code = status_code

            def json(self):
                return {"final_balance": 100000000, "total_received": 100000000, "total_sent": 0, "n_tx": 1}

        monkeypatch.setattr("modules.crypto_lookup.get_proxies", lambda: None)
        monkeypatch.setattr("modules.crypto_lookup.requests.get", lambda *args, **kwargs: MockResponse())
        monkeypatch.setattr(CryptoLookup, "_get_price", lambda self, coin: 0.0)
        return CryptoLookup().lookup_bitcoin("1BoatSLRHtKNngkdXEeobR76b53LETtpyT")

    def test_success_is_ok(self, monkeypatch):
        from modules.module_status import OK

        result = self._lookup_with_status(monkeypatch, 200)

        assert result["status"] == OK
        assert result["error"] is None

    def test_http_429_is_rate_limited(self, monkeypatch):
        from modules.module_status import RATE_LIMITED

        result = self._lookup_with_status(monkeypatch, 429)

        assert result["status"] == RATE_LIMITED
        assert result["error"] is None

    def test_other_http_failure_is_error(self, monkeypatch):
        from modules.module_status import ERROR

        result = self._lookup_with_status(monkeypatch, 503)

        assert result["status"] == ERROR
        assert "503" in result["error"]

    @pytest.mark.parametrize(
        ("price_status", "expected_status"),
        [(200, "ok"), (429, "rate_limited"), (503, "error")],
    )
    def test_price_provider_failures_are_annotated(self, monkeypatch, price_status, expected_status):
        from modules.crypto_lookup import CryptoLookup

        class MockResponse:
            def __init__(self, status_code):
                self.status_code = status_code

            def json(self):
                if self.status_code == 200:
                    return {"final_balance": 100000000, "total_received": 100000000, "total_sent": 0, "n_tx": 1}
                return {"bitcoin": {"usd": 50000}}

        def mock_get(url, **kwargs):
            if "coingecko" in url:
                return MockResponse(price_status)
            return MockResponse(200)

        monkeypatch.setattr("modules.crypto_lookup.get_proxies", lambda: None)
        monkeypatch.setattr("modules.crypto_lookup.requests.get", mock_get)
        monkeypatch.setattr(CryptoLookup, "_prices_cache", None)
        monkeypatch.setattr(CryptoLookup, "_prices_error", None)
        monkeypatch.setattr(CryptoLookup, "_prices_status", None)
        monkeypatch.setattr(CryptoLookup, "_prices_timestamp", 0.0)

        result = CryptoLookup().lookup_bitcoin("1BoatSLRHtKNngkdXEeobR76b53LETtpyT")

        assert result["status"] == expected_status
        if expected_status == "error":
            assert "CoinGecko" in result["error"]
        else:
            assert result["error"] is None


class TestDarkWebSearchStatuses:
    def _search_with_status(self, monkeypatch, status_code, results=None):
        from modules.darkweb_search import DarkWebSearch

        class MockResponse:
            def __init__(self):
                self.status_code = status_code

            def json(self):
                if results is None:
                    return {"results": [{"title": "example", "url": "http://example.onion", "description": "result"}]}
                return {"results": results}

        monkeypatch.setattr("modules.darkweb_search.get_proxies", lambda: None)
        monkeypatch.setattr("modules.darkweb_search.requests.get", lambda *args, **kwargs: MockResponse())
        return DarkWebSearch().search("example")

    def test_success_is_ok(self, monkeypatch):
        from modules.module_status import OK

        result = self._search_with_status(monkeypatch, 200)

        assert result["status"] == OK
        assert result["error"] is None
        assert result["results"]

    def test_successful_empty_search_is_ok(self, monkeypatch):
        from modules.module_status import OK

        result = self._search_with_status(monkeypatch, 200, results=[])

        assert result["status"] == OK
        assert result["error"] is None
        assert result["results"] == []

    def test_http_429_is_rate_limited(self, monkeypatch):
        from modules.module_status import RATE_LIMITED

        result = self._search_with_status(monkeypatch, 429)

        assert result["status"] == RATE_LIMITED
        assert result["error"] is None

    def test_other_http_failure_is_error(self, monkeypatch):
        from modules.module_status import ERROR

        result = self._search_with_status(monkeypatch, 503)

        assert result["status"] == ERROR
        assert "503" in result["error"]


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
            assert all(ord(c) < 128 or c in ' -()' for c in result["region"]),\
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

    def test_reverse_lookup_partial_failure(self, monkeypatch):
        import requests
        from modules.hlr_lookup import HLRLookup

        def mock_get(url, *args, **kwargs):
            class MockResp:
                def __init__(self, code, json_data):
                    self.status_code = code
                    self._json = json_data
                    self.text = "владелец: Иван Иванович\n<div class='comment'>Good guy</div>"
                def json(self): return self._json

            if "numlookupapi" in url:
                return MockResp(200, {"city": "Moscow", "carrier": "MTS"})
            elif "kto-zvonil.ru" in url:
                return MockResp(500, {})
            elif "zvonili.com" in url:
                raise requests.exceptions.Timeout("Timeout")
            return MockResp(404, {})

        monkeypatch.setattr(requests, "get", mock_get)
        result = HLRLookup().reverse_lookup("+79001234567")
        assert "numlookupapi.com" in result["sources"]
        assert any(f["source"] == "kto-zvonil.ru" for f in result["sources_failed"])
        assert any(f["source"] == "zvonili.com" for f in result["sources_failed"])
        assert result.get("status") != "ERROR"

    def test_reverse_lookup_all_failed(self, monkeypatch):
        import requests
        from modules.hlr_lookup import HLRLookup
        from modules.module_status import classify, ERROR

        def mock_get(*args, **kwargs):
            raise requests.exceptions.Timeout("Timeout")

        monkeypatch.setattr(requests, "get", mock_get)
        result = HLRLookup().reverse_lookup("+79001234567")
        assert len(result["sources"]) == 0
        assert len(result["sources_failed"]) == 3
        assert classify(result) == ERROR

class TestLeakLookup:
    def test_check_email_hibp_not_found(self, monkeypatch):
        import requests
        from modules.leak_lookup import LeakLookup

        class MockResp:
            status_code = 404
            def json(self):
                return []

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        ll = LeakLookup()
        ll.hibp_key = "fakekey"
        result = ll.check_email_hibp("clean@example.com")
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
        ll = LeakLookup()
        ll.hibp_key = "fakekey"
        result = ll.check_email_hibp("breached@example.com")
        assert result["breached"] is True
        assert result["total_breaches"] == 1
        assert result["breaches"][0]["name"] == "Adobe"

    def test_check_email_hibp_no_key_skips_without_request(self, monkeypatch):
        import requests
        from modules.leak_lookup import LeakLookup
        from modules.module_status import classify, SKIPPED

        def _fail(*a, **k):
            raise AssertionError("HIBP must not be called without a key")

        monkeypatch.setattr(requests, "get", _fail)
        ll = LeakLookup()
        ll.hibp_key = ""
        result = ll.check_email_hibp("x@example.com")
        assert classify(result) == SKIPPED
        assert result["error"] is None
        assert "HIBP_API_KEY" in result["status_reason"]

    def test_check_email_hibp_401(self, monkeypatch):
        import requests
        from modules.leak_lookup import LeakLookup
        from modules.module_status import classify, SKIPPED

        class MockResp:
            status_code = 401
            def json(self):
                return {}

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        ll = LeakLookup()
        ll.hibp_key = "fakekey"
        result = ll.check_email_hibp("x@example.com")
        assert classify(result) == SKIPPED
        assert result["error"] is None
        assert "HIBP" in result["status_reason"]

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
        from modules.module_status import classify, SKIPPED
        assert classify(result) == SKIPPED
        assert result["error"] is None
        assert "API key" in result["status_reason"]

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

class TestShodanHostStatus:
    def _lookup(self):
        from modules.shodan_lookup import ShodanLookup
        sh = ShodanLookup()
        sh.api_key = "fakekey"
        return sh

    def test_host_info_404_is_ok_with_empty_data(self, monkeypatch):
        import requests
        from modules.module_status import classify, OK

        class MockResp:
            status_code = 404

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        result = self._lookup().host_info("192.0.2.1")
        assert classify(result) == OK
        assert result["status"] == OK
        assert result["error"] is None
        assert result["status_reason"] == "No information available for this IP in Shodan"
        assert result["open_ports"] == []
        assert result["services"] == []
        assert result["vulns"] == []

    def test_host_info_unexpected_status_is_error(self, monkeypatch):
        import requests
        from modules.module_status import classify, ERROR

        class MockResp:
            status_code = 500

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        result = self._lookup().host_info("192.0.2.1")
        assert classify(result) == ERROR
        assert result["status"] == ERROR
        assert result["error"] == "Shodan API returned 500"
        assert result["status_reason"] == "Shodan API returned 500"

    def test_host_info_exception_is_error(self, monkeypatch):
        import requests
        from modules.module_status import classify, ERROR

        def _boom(*a, **k):
            raise requests.exceptions.ConnectionError("connection refused")

        monkeypatch.setattr(requests, "get", _boom)
        result = self._lookup().host_info("192.0.2.1")
        assert classify(result) == ERROR
        assert result["status"] == ERROR
        assert result["error"] == "connection refused"

    def test_search_unexpected_status_is_error(self, monkeypatch):
        import requests
        from modules.module_status import classify, ERROR

        class MockResp:
            status_code = 502
            text = "bad gateway"

        monkeypatch.setattr(requests, "get", lambda *a, **k: MockResp())
        result = self._lookup().search("apache")
        assert classify(result) == ERROR
        assert result["error"].startswith("Shodan API returned 502")


class TestLeakLookupStatus:
    def _lookup(self):
        from modules.leak_lookup import LeakLookup
        ll = LeakLookup()
        ll.leak_lookup_key = "fakekey"
        ll.hibp_key = "fakekey"
        return ll

    def _resp(self, status, payload=None, text=""):
        class MockResp:
            status_code = status
            def json(self):
                return payload
        MockResp.text = text
        return MockResp()

    def test_leak_lookup_not_found_is_ok(self, monkeypatch):
        import requests
        from modules.module_status import classify, OK

        resp = self._resp(200, {"message": "Not found"})
        monkeypatch.setattr(requests, "post", lambda *a, **k: resp)
        result = self._lookup().check_leak_lookup("clean@example.com")
        assert classify(result) == OK
        assert result["found"] is False
        assert result["error"] is None

    def test_leak_lookup_unknown_message_is_error(self, monkeypatch):
        import requests
        from modules.module_status import classify, ERROR

        resp = self._resp(200, {"error": "true", "message": "INVALID TYPE"})
        monkeypatch.setattr(requests, "post", lambda *a, **k: resp)
        result = self._lookup().check_leak_lookup("x@example.com")
        assert classify(result) == ERROR
        assert result["status"] == ERROR
        assert result["error"] == "INVALID TYPE"

    def test_leak_lookup_unexpected_status_is_error(self, monkeypatch):
        import requests
        from modules.module_status import classify, ERROR

        monkeypatch.setattr(requests, "post", lambda *a, **k: self._resp(500))
        result = self._lookup().check_leak_lookup("x@example.com")
        assert classify(result) == ERROR
        assert result["error"] == "API returned status 500"

    def test_leak_lookup_exception_is_error(self, monkeypatch):
        import requests
        from modules.module_status import classify, ERROR

        def _boom(*a, **k):
            raise RuntimeError("timeout")

        monkeypatch.setattr(requests, "post", _boom)
        result = self._lookup().check_leak_lookup("x@example.com")
        assert classify(result) == ERROR
        assert result["error"] == "timeout"

    @pytest.mark.parametrize("method,label", [
        ("check_email_hibp", "HIBP returned status 500"),
        ("check_email_xon", "XposedOrNot returned status 500"),
        ("check_email_leakcheck", "LeakCheck returned status 500"),
    ])
    def test_email_checks_unexpected_status_is_error(self, monkeypatch, method, label):
        import requests
        from modules.module_status import classify, ERROR

        monkeypatch.setattr(requests, "get", lambda *a, **k: self._resp(500))
        result = getattr(self._lookup(), method)("x@example.com")
        assert classify(result) == ERROR
        assert result["status"] == ERROR
        assert result["error"] == label

    @pytest.mark.parametrize("method", ["check_email_hibp", "check_email_xon", "check_email_leakcheck"])
    def test_email_checks_exception_is_error(self, monkeypatch, method):
        import requests
        from modules.module_status import classify, ERROR

        def _boom(*a, **k):
            raise requests.exceptions.ConnectionError("unreachable")

        monkeypatch.setattr(requests, "get", _boom)
        result = getattr(self._lookup(), method)("x@example.com")
        assert classify(result) == ERROR
        assert result["error"] == "unreachable"

    def test_password_pwned_unexpected_status_is_error(self, monkeypatch):
        import requests
        from modules.module_status import classify, ERROR

        monkeypatch.setattr(requests, "get", lambda *a, **k: self._resp(503))
        result = self._lookup().check_password_pwned("hunter2")
        assert classify(result) == ERROR
        assert result["error"] == "API returned status 503"

    def test_password_pwned_exception_is_error(self, monkeypatch):
        import requests
        from modules.module_status import classify, ERROR

        def _boom(*a, **k):
            raise requests.exceptions.Timeout("slow")

        monkeypatch.setattr(requests, "get", _boom)
        result = self._lookup().check_password_pwned("hunter2")
        assert classify(result) == ERROR
        assert result["error"] == "slow"


class TestVirusTotal:
    def test_no_api_key(self, monkeypatch):
        from modules.threat_intel import VirusTotal
        monkeypatch.setattr("modules.threat_intel.VIRUSTOTAL_API_KEY", "")
        vt = VirusTotal()
        result = vt.check_ip("1.2.3.4")
        from modules.module_status import classify, SKIPPED
        assert classify(result) == SKIPPED
        assert result["error"] is None
        assert "API key" in result["status_reason"]

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
        from modules.module_status import classify, SKIPPED
        assert classify(result) == SKIPPED
        assert result["error"] is None
        assert "API key" in result["status_reason"]

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

    @pytest.mark.parametrize("username", [
        "user?name",
        'user"name',
        "user:name",
        "../../../pwned",
        "a" * 300,
        "",
    ])
    def test_export_json_keeps_hostile_usernames_inside_output_dir(self, username):
        from config import OUTPUT_DIR
        from modules.blackbird import Blackbird, SiteResult
        bb = Blackbird()
        bb.results = [SiteResult("GitHub", "https://github.com/x", "found", 200, 0.5)]
        path = bb.export_json(username)
        try:
            assert os.path.exists(path)
            assert os.path.abspath(path).startswith(os.path.abspath(OUTPUT_DIR))
        finally:
            os.remove(path)

    @pytest.mark.parametrize("username", ["evil.com/#", "evil.com?", "../../../etc", "a@evil.com"])
    def test_check_site_urls_stay_on_the_expected_host(self, username):
        from urllib.parse import quote
        from yarl import URL
        from modules.blackbird import Blackbird
        for template, _type, _indicator in Blackbird.SITES.values():
            base_host = URL(template.format("x")).host
            suffix = base_host[1:] if base_host.startswith("x") else base_host
            host = URL(template.format(quote(username, safe=""))).host
            assert host.endswith(suffix)

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

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        from modules.crypto_lookup import CryptoLookup
        CryptoLookup._prices_cache = None
        CryptoLookup._prices_error = None
        yield
        CryptoLookup._prices_cache = None
        CryptoLookup._prices_error = None

    def test_single_price_request_and_429(self, monkeypatch):
        import requests
        from modules.crypto_lookup import CryptoLookup

        price_calls = 0

        class MockResp:
            def __init__(self, status_code, json_data=None):
                self.status_code = status_code
                self._json = json_data or {}
            def json(self):
                return self._json

        def mock_get(url, **kwargs):
            nonlocal price_calls
            if "coingecko.com" in url:
                price_calls += 1
                return MockResp(429)
            if "blockchain.info" in url:
                return MockResp(200, {"final_balance": 100000000, "total_received": 100000000, "total_sent": 0, "n_tx": 1})
            if "ethplorer.io" in url:
                return MockResp(200, {"ETH": {"balance": 1.5, "txCount": 2}})
            return MockResp(404)

        monkeypatch.setattr(requests, "get", mock_get)

        cl = CryptoLookup()
        btc_res = cl.lookup("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        eth_res = cl.lookup("0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68")

        assert price_calls == 1
        assert btc_res["balance_usd"] is None
        assert btc_res["price_unavailable"] == "CoinGecko returned 429"
        assert eth_res["balance_usd"] is None
        assert eth_res["price_unavailable"] == "CoinGecko returned 429"

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


class TestExtraToolsStatuses:
    def test_whois_missing_dependency_is_skipped(self, monkeypatch):
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "WHOIS_AVAILABLE", False)
        result = extra_tools.WhoisLookup().lookup("example.com")

        assert result["status"] == "skipped"
        assert result["status_reason"] == "python-whois not installed. Run: pip install python-whois"
        assert result["error"] is None

    def test_whois_success_is_ok(self, monkeypatch):
        from types import SimpleNamespace
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "WHOIS_AVAILABLE", True)
        monkeypatch.setattr(
            extra_tools,
            "whois",
            SimpleNamespace(whois=lambda domain: SimpleNamespace(
                registrar="Example Registrar",
                org="Example Org",
                country="US",
                creation_date=None,
                expiration_date=None,
                updated_date=None,
                name_servers=["NS1.EXAMPLE.COM"],
                status=["active"],
                emails=["admin@example.com"],
            )),
            raising=False,
        )

        result = extra_tools.WhoisLookup().lookup("example.com")

        assert result["status"] == "ok"
        assert result["error"] is None
        assert result["registrar"] == "Example Registrar"
        assert result["whois_status"] == ["active"]

    def test_whois_exception_is_error(self, monkeypatch):
        from types import SimpleNamespace
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "WHOIS_AVAILABLE", True)
        monkeypatch.setattr(
            extra_tools,
            "whois",
            SimpleNamespace(whois=lambda domain: (_ for _ in ()).throw(RuntimeError("lookup failed"))),
            raising=False,
        )

        result = extra_tools.WhoisLookup().lookup("example.com")

        assert result["status"] == "error"
        assert result["error"] == "lookup failed"

    def test_geoip_success_is_ok(self, monkeypatch):
        import socket
        from modules import extra_tools

        monkeypatch.setattr(socket, "gethostbyname", lambda host: "203.0.113.1")
        monkeypatch.setattr(extra_tools, "get_proxies", lambda: {})

        class Response:
            status_code = 200

            @staticmethod
            def json():
                return {"ip": "203.0.113.1", "country": "US"}

        monkeypatch.setattr(extra_tools.requests, "get", lambda *args, **kwargs: Response())
        result = extra_tools.GeoIPLookup().lookup("example.com")

        assert result["status"] == "ok"
        assert result["error"] is None
        assert result["country_name"] == "United States"

    def test_geoip_rate_limit_is_rate_limited(self, monkeypatch):
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "get_proxies", lambda: {})

        class Response:
            status_code = 429

        monkeypatch.setattr(extra_tools.requests, "get", lambda *args, **kwargs: Response())
        result = extra_tools.GeoIPLookup().lookup("203.0.113.1")

        assert result["status"] == "rate_limited"
        assert result["status_reason"] == "ipinfo API rate limit reached"
        assert result["error"] is None

    def test_geoip_http_failure_is_error(self, monkeypatch):
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "get_proxies", lambda: {})

        class Response:
            status_code = 503

        monkeypatch.setattr(extra_tools.requests, "get", lambda *args, **kwargs: Response())
        result = extra_tools.GeoIPLookup().lookup("203.0.113.1")

        assert result["status"] == "error"
        assert result["error"] == "API returned status 503"

    def test_geoip_request_exception_is_error(self, monkeypatch):
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "get_proxies", lambda: {})
        monkeypatch.setattr(
            extra_tools.requests,
            "get",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("request failed")),
        )
        result = extra_tools.GeoIPLookup().lookup("203.0.113.1")

        assert result["status"] == "error"
        assert result["error"] == "request failed"

    def test_dns_missing_dependency_is_skipped(self, monkeypatch):
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "DNS_AVAILABLE", False)
        result = extra_tools.DNSLookup().lookup("example.com")

        assert result["status"] == "skipped"
        assert result["status_reason"] == "dnspython not installed. Run: pip install dnspython"
        assert result["error"] is None

    def test_dns_success_is_ok(self, monkeypatch):
        import dns
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "DNS_AVAILABLE", True)
        monkeypatch.setattr(
            dns.resolver,
            "resolve",
            lambda domain, record_type: ["203.0.113.1"],
        )
        result = extra_tools.DNSLookup().lookup("example.com", ["A"])

        assert result["status"] == "ok"
        assert result["error"] is None
        assert result["records"] == {"A": ["203.0.113.1"]}

    def test_dns_nxdomain_is_ok_with_reason(self, monkeypatch):
        import dns
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "DNS_AVAILABLE", True)
        monkeypatch.setattr(
            dns.resolver,
            "resolve",
            lambda domain, record_type: (_ for _ in ()).throw(dns.resolver.NXDOMAIN()),
        )
        result = extra_tools.DNSLookup().lookup("missing.example", ["A", "MX"])

        assert result["status"] == "ok"
        assert result["status_reason"] == "Domain does not exist"
        assert result["records"] == {}
        assert result["error"] is None

    def test_dns_timeout_is_error(self, monkeypatch):
        import dns
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "DNS_AVAILABLE", True)
        monkeypatch.setattr(
            dns.resolver,
            "resolve",
            lambda domain, record_type: (_ for _ in ()).throw(dns.exception.Timeout()),
        )
        result = extra_tools.DNSLookup().lookup("example.com", ["A"])

        assert result["status"] == "error"
        assert result["error"] == "DNS query timeout"

    def test_dns_exception_is_error(self, monkeypatch):
        import dns
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "DNS_AVAILABLE", True)
        monkeypatch.setattr(
            dns.resolver,
            "resolve",
            lambda domain, record_type: (_ for _ in ()).throw(RuntimeError("resolver failed")),
        )
        result = extra_tools.DNSLookup().lookup("example.com", ["A"])

        assert result["status"] == "error"
        assert result["error"] == "resolver failed"

    def test_website_success_is_ok(self, monkeypatch):
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "get_proxies", lambda: {})

        class Response:
            text = "<html><title>Example</title></html>"
            headers = {"Server": "nginx"}

        monkeypatch.setattr(extra_tools.requests, "get", lambda *args, **kwargs: Response())
        result = extra_tools.WebsiteAnalyzer().analyze("example.com")

        assert result["status"] == "ok"
        assert result["error"] is None
        assert result["title"] == "Example"

    def test_website_exception_is_error(self, monkeypatch):
        from modules import extra_tools

        monkeypatch.setattr(extra_tools, "get_proxies", lambda: {})
        monkeypatch.setattr(
            extra_tools.requests,
            "get",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("site request failed")),
        )
        result = extra_tools.WebsiteAnalyzer().analyze("example.com")

        assert result["status"] == "error"
        assert result["error"] == "site request failed"
