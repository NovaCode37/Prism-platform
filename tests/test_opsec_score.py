import os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.opsec_score import OpsecScorer, score_from_results, RISK_LEVELS


class TestScoreFromResults:
    def test_clean_target_scores_high(self):
        result = score_from_results({})
        assert 86 <= result["score"] <= 100
        assert result["risk_level"] == "MINIMAL"

    @pytest.mark.parametrize("breach_count,expected_deduction", [
        (1, 8),
        (2, 15),
        (4, 15),
        (5, 25),
        (10, 25),
    ])
    def test_breach_deductions(self, breach_count, expected_deduction):
        result = score_from_results({"breaches": {"breach_count": breach_count}})
        assert result["categories"]["data_exposure"]["score"] == 35 - expected_deduction

    def test_smtp_deduction(self):
        result = score_from_results({"smtp": {"exists": True}})
        assert result["categories"]["data_exposure"]["score"] == 30  # 35 - 5

    def test_virustotal_malicious_deductions(self):
        result = score_from_results({"virustotal": {"malicious": 1}})
        assert result["categories"]["data_exposure"]["score"] == 15  # 35 - 20
        result2 = score_from_results({"virustotal": {"malicious": 5}})
        assert result2["categories"]["data_exposure"]["score"] == 5   # 35 - 30

    @pytest.mark.parametrize("abuse_score,expected", [
        (90, 10),   # 35 - 25
        (50, 20),   # 35 - 15
        (20, 28),   # 35 - 7
        (5, 35),    # no deduction
    ])
    def test_abuseipdb_score_deductions(self, abuse_score, expected):
        result = score_from_results({"abuseipdb": {"abuse_score": abuse_score}})
        assert result["categories"]["data_exposure"]["score"] == expected

    @pytest.mark.parametrize("found_count,expected", [
        (1, 22),   # 25 - 3
        (5, 18),   # 25 - 7
        (10, 12),  # 25 - 13
        (20, 5),   # 25 - 20
    ])
    def test_blackbird_deductions(self, found_count, expected):
        results = [{"status": "found"}] * found_count
        result = score_from_results({"blackbird": results})
        assert result["categories"]["identity_opsec"]["score"] == expected

    @pytest.mark.parametrize("email_count,expected", [
        (1, 22),   # 25 - 3
        (3, 17),   # 25 - 8
        (10, 10),  # 25 - 15
    ])
    def test_hunter_deductions(self, email_count, expected):
        emails = [f"u{i}@acme.com" for i in range(email_count)]
        result = score_from_results({"hunter": {"emails": emails}})
        assert result["categories"]["identity_opsec"]["score"] == expected

    def test_whois_deductions(self):
        result = score_from_results({"whois": {"emails": ["a@b.com"], "org": "Acme Corp"}})
        assert result["categories"]["infrastructure"]["score"] == 14  # 25 - 8 - 3

    def test_shodan_vulns_deduction(self):
        result = score_from_results({"shodan": {"vulns": ["CVE-2024-0001"], "open_ports": []}})
        assert result["categories"]["infrastructure"]["score"] == 5  # 25 - 20

    def test_cert_transparency_deduction(self):
        result = score_from_results({"cert_transparency": {"subdomains": [f"s{i}.x.com" for i in range(20)]}})
        assert result["categories"]["infrastructure"]["score"] == 20  # 25 - 5

    def test_dns_no_spf_deduction(self):
        result = score_from_results({"dns": {"records": {"TXT": ["v=spf1 -all"]}}})
        assert result["categories"]["infrastructure"]["score"] == 25  # has SPF
        result2 = score_from_results({"dns": {"records": {"TXT": ["dkim=something"]}}})
        assert result2["categories"]["infrastructure"]["score"] == 20  # 25 - 5

    def test_website_http_deduction(self):
        result = score_from_results({"website": {"url": "http://example.com", "headers": {"x-frame-options": "DENY", "x-content-type-options": "nosniff"}, "emails": [], "technologies": []}})
        assert result["categories"]["web_security"]["score"] == 7  # 15 - 8

    def test_wayback_deduction(self):
        result = score_from_results({"wayback": {"interesting": ["/admin", "/wp-admin", "/backup", "/config", "/.git"]}})
        assert result["categories"]["web_security"]["score"] == 7  # 15 - 8

    def test_multiple_findings_cumulative(self):
        result = score_from_results({
            "breaches": {"breach_count": 5},      # data_exposure: -25 → 10
            "smtp": {"exists": True},              # data_exposure: -5  → 5
            "whois": {"emails": ["a@b.com"]},     # infrastructure: -8  → 17
            "shodan": {"open_ports": [22]},       # infrastructure: -12 →  5 (sensitive ports)
            "website": {"url": "http://x.com", "headers": {"x-frame-options": "DENY", "x-content-type-options": "nosniff"}, "emails": [], "technologies": []},  # web_security: -8 → 7
        })
        assert result["categories"]["data_exposure"]["score"] == 5
        assert result["categories"]["infrastructure"]["score"] == 5
        assert result["categories"]["web_security"]["score"] == 7
        assert result["categories"]["identity_opsec"]["score"] == 25
        assert 0 < result["score"] < 100

    def test_none_or_empty_results_skipped(self):
        result = score_from_results({
            "breaches": None,
            "smtp": {},
            "virustotal": None,
            "abuseipdb": {},
            "blackbird": None,
            "hunter": None,
            "whois": None,
            "shodan": {},
            "website": {},
        })
        assert result["score"] == 100
        assert result["risk_level"] == "MINIMAL"

    def test_error_results_skipped(self):
        result = score_from_results({
            "virustotal": {"error": "API limit"},
            "abuseipdb": {"error": "bad IP"},
            "shodan": {"error": "no results"},
            "cert_transparency": {"error": "timeout"},
            "dns": {"error": "NXDOMAIN"},
            "website": {"error": "connection refused"},
            "wayback": {"error": "404"},
        })
        assert result["score"] == 100

    def test_category_never_below_zero(self):
        result = score_from_results({
            "website": {"url": "http://x.com", "headers": {}, "emails": ["a@x.com", "b@x.com", "c@x.com", "d@x.com", "e@x.com"], "technologies": ["php", "asp.net"]},
            "wayback": {"interesting": ["/admin", "/backup", "/wp-admin", "/config", "/.env"]},
        })
        assert result["categories"]["web_security"]["score"] >= 0  # was 15, -8 -5 -4 -3 = -5 → clamped to 0

    def test_overall_score_never_below_zero(self):
        result = score_from_results({
            "breaches": {"breach_count": 5},     # -25
            "virustotal": {"malicious": 5},       # -30
            "abuseipdb": {"abuse_score": 90},      # -25 (data_exposure already 0)
            "blackbird": [{"status": "found"}] * 20,   # -20
            "hunter": {"emails": [f"u{i}@x.com" for i in range(10)]},  # -15
            "whois": {"emails": ["a@b.com"], "org": "Acme"},   # -11
            "shodan": {"vulns": ["CVE-1"], "open_ports": [21, 22, 3389]},  # -20 -12
            "dns": {"records": {}},                 # -5
            "website": {"url": "http://x.com", "headers": {}, "emails": ["a@x.com"], "technologies": ["php"]},
            "wayback": {"interesting": ["/admin", "/backup", "/config"]},
        })
        assert result["score"] >= 0

    @pytest.mark.parametrize("deductions,expected_band", [
        ({}, "MINIMAL"),
        ({"breaches": {"breach_count": 5}}, "LOW"),     # ~85 → LOW (71-85)
        ({"breaches": {"breach_count": 5}, "smtp": {"exists": True},
          "whois": {"emails": ["a@b.com"]}}, None),     # just check in-range
    ])
    def test_risk_level_bands(self, deductions, expected_band):
        result = score_from_results(deductions)
        risk_labels = {v[0] for v in RISK_LEVELS.values()}
        assert result["risk_level"] in risk_labels
        if expected_band:
            assert result["risk_level"] == expected_band
        assert 0 <= result["score"] <= 100

    def test_result_has_all_expected_keys(self):
        result = score_from_results({"breaches": {"breach_count": 1}})
        assert "score" in result
        assert "risk_level" in result
        assert "categories" in result
        for cat in ("data_exposure", "identity_opsec", "infrastructure", "web_security"):
            assert cat in result["categories"]
            c = result["categories"][cat]
            assert "score" in c
            assert "max" in c
            assert "percent" in c
            assert "findings" in c
        assert "all_findings" in result
        assert isinstance(result["all_findings"], list)

    def test_findings_sorted_by_severity(self):
        result = score_from_results({
            "smtp": {"exists": True},
            "breaches": {"breach_count": 1},
        })
        severities = [f["severity"] for f in result["all_findings"]]
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        assert severities == sorted(severities, key=lambda s: order.get(s, 5))