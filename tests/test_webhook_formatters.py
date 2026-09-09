import pytest

from modules.webhook_formatters import format_slack, format_discord, FIELD_VALUE_LIMIT


class TestSlackFormatter:
    def test_completed_scan_payload(self):
        payload = {
            "target": "example.com",
            "scan_type": "domain",
            "status": "completed",
            "results": {
                "opsec_score": {"score": 85, "risk_level": "LOW"},
                "virustotal": {"malicious": 2},
                "breaches": {"found": True, "total": 3},
                "shodan": {"vulns": ["CVE-2021-44228"]},
            },
            "started_at": "2026-01-01T12:00:00Z",
            "completed_at": "2026-01-01T12:00:18Z",
        }

        result = format_slack(payload)

        assert "blocks" in result
        blocks = result["blocks"]

        assert blocks[0]["type"] == "header"
        assert "PRISM Scan" in blocks[0]["text"]["text"]
        assert ":white_check_mark:" in blocks[0]["text"]["text"]

        assert blocks[1]["type"] == "section"
        fields = blocks[1]["fields"]
        assert fields[0]["text"] == "*Target:*\n`example.com`"
        assert fields[1]["text"] == "*Type:*\nDOMAIN"

        score_block = blocks[2]
        assert "*OPSEC Score:* 85/100 (LOW)" in score_block["text"]["text"]

        findings_block = blocks[3]
        assert "VirusTotal: 2 malicious detections" in findings_block["text"]["text"]
        assert "Breaches: 3 found" in findings_block["text"]["text"]
        assert "Shodan: 1 CVEs" in findings_block["text"]["text"]

        context_block = blocks[4]
        assert "Started: 2026-01-01T12:00:00Z | Completed: 2026-01-01T12:00:18Z" in context_block["elements"][0]["text"]

    def test_failed_scan_payload(self):
        payload = {
            "target": "evil.com",
            "scan_type": "domain",
            "status": "failed",
            "results": {},
            "started_at": "2026-01-01T12:00:00Z",
            "completed_at": "2026-01-01T12:00:18Z",
        }

        result = format_slack(payload)

        blocks = result["blocks"]
        assert blocks[0]["type"] == "header"
        assert ":x:" in blocks[0]["text"]["text"]

        score_blocks = [b for b in blocks if b.get("text") and "*OPSEC Score:*" in b["text"]["text"]]
        assert len(score_blocks) == 0

        findings_blocks = [b for b in blocks if b.get("type") == "section" and b.get("text") and "Notable Findings" in b["text"]["text"]]
        assert len(findings_blocks) == 1
        assert "No notable findings" in findings_blocks[0]["text"]["text"]

    def test_missing_keys(self):
        payload = {"results": {}}

        result = format_slack(payload)

        blocks = result["blocks"]
        assert blocks[0]["text"]["text"] == "PRISM Scan :x: UNKNOWN"

        fields = blocks[1]["fields"]
        assert fields[0]["text"] == "*Target:*\n`unknown`"
        assert fields[1]["text"] == "*Type:*\nUNKNOWN"

        findings_blocks = [b for b in blocks if b.get("type") == "section" and b.get("text") and "Notable Findings" in b["text"]["text"]]
        assert len(findings_blocks) == 1
        assert "No notable findings" in findings_blocks[0]["text"]["text"]

    def test_missing_opsec_score(self):
        payload = {
            "target": "example.com",
            "scan_type": "domain",
            "status": "completed",
            "results": {"virustotal": {"malicious": 1}},
        }

        result = format_slack(payload)

        score_blocks = [b for b in result["blocks"] if b.get("text") and "*OPSEC Score:*" in b["text"]["text"]]
        assert len(score_blocks) == 0


class TestDiscordFormatter:
    def test_completed_scan_payload(self):
        payload = {
            "target": "example.com",
            "scan_type": "domain",
            "status": "completed",
            "results": {
                "opsec_score": {"score": 72, "risk_level": "LOW"},
                "virustotal": {"malicious": 1},
                "breaches": {"found": True, "total": 2},
                "shodan": {"vulns": ["CVE-2021-44228"]},
                "cert_transparency": {"subdomains": ["www.example.com", "api.example.com"]},
            },
            "completed_at": "2026-01-01T12:00:18Z",
        }

        result = format_discord(payload)

        assert "embeds" in result
        embed = result["embeds"][0]

        assert embed["title"] == "PRISM Scan - example.com"
        assert embed["color"] == 0x00FF00

        fields = embed["fields"]
        assert fields[0]["name"] == "Target"
        assert fields[0]["value"] == "`example.com`"
        assert fields[1]["name"] == "Type"
        assert fields[1]["value"] == "DOMAIN"
        assert fields[2]["name"] == "Status"
        assert fields[2]["value"] == "COMPLETED"

        opsec_field = next(f for f in fields if f["name"] == "OPSEC Score")
        assert opsec_field["value"] == "72/100 (LOW)"

        findings_field = next(f for f in fields if f["name"] == "Notable Findings")
        assert "**VirusTotal:** 1 malicious" in findings_field["value"]
        assert "**Breaches:** 2 found" in findings_field["value"]
        assert "**Shodan CVEs:** 1" in findings_field["value"]
        assert "**Subdomains:** 2" in findings_field["value"]

        assert embed["timestamp"] == "2026-01-01T12:00:18Z"
        assert embed["footer"]["text"] == "PRISM OSINT Platform"

    def test_completed_scan_high_risk(self):
        payload = {
            "target": "bad.com",
            "scan_type": "ip",
            "status": "completed",
            "results": {"opsec_score": {"score": 25, "risk_level": "HIGH"}},
        }

        result = format_discord(payload)
        assert result["embeds"][0]["color"] == 0xFF0000

    def test_completed_scan_medium_risk(self):
        payload = {
            "target": "medium.com",
            "scan_type": "ip",
            "status": "completed",
            "results": {"opsec_score": {"score": 55, "risk_level": "MEDIUM"}},
        }

        result = format_discord(payload)
        assert result["embeds"][0]["color"] == 0xFFAA00

    def test_failed_scan_payload(self):
        payload = {
            "target": "evil.com",
            "scan_type": "domain",
            "status": "failed",
            "results": {},
        }

        result = format_discord(payload)
        embed = result["embeds"][0]

        assert embed["color"] == 0xFF0000
        fields = embed["fields"]
        assert fields[0]["value"] == "`evil.com`"
        assert fields[1]["value"] == "DOMAIN"
        assert fields[2]["value"] == "FAILED"

        opsec_fields = [f for f in fields if f["name"] == "OPSEC Score"]
        assert len(opsec_fields) == 0

    def test_missing_keys(self):
        payload = {"results": {}}

        result = format_discord(payload)
        embed = result["embeds"][0]

        assert embed["color"] == 0xFF0000
        fields = embed["fields"]
        assert fields[0]["value"] == "`unknown`"
        assert fields[1]["value"] == "UNKNOWN"
        assert fields[2]["value"] == "UNKNOWN"

        opsec_fields = [f for f in fields if f["name"] == "OPSEC Score"]
        assert len(opsec_fields) == 0

    def test_missing_opsec_score(self):
        payload = {
            "target": "example.com",
            "scan_type": "domain",
            "status": "completed",
            "results": {},
        }

        result = format_discord(payload)
        embed = result["embeds"][0]

        assert embed["color"] == 0x5865F2
        fields = embed["fields"]
        opsec_fields = [f for f in fields if f["name"] == "OPSEC Score"]
        assert len(opsec_fields) == 0

    def test_field_value_truncation(self):
        long_text = "x" * 1500

        payload = {
            "target": "example.com",
            "scan_type": "domain",
            "status": "completed",
            "results": {
                "opsec_score": {"score": 85, "risk_level": "LOW"},
                "breaches": {"found": True, "total": 999, "breaches": [long_text]},
            },
        }

        result = format_discord(payload)
        embed = result["embeds"][0]

        fields = embed["fields"]
        findings_field = next((f for f in fields if f["name"] == "Notable Findings"), None)

        assert findings_field is not None
        assert len(findings_field["value"]) <= FIELD_VALUE_LIMIT
        assert findings_field["value"].endswith("...")

    def test_discord_empty_results(self):
        payload = {
            "target": "empty.com",
            "scan_type": "domain",
            "status": "completed",
            "results": {},
        }

        result = format_discord(payload)
        embed = result["embeds"][0]

        assert embed["title"] == "PRISM Scan - empty.com"
        fields = embed["fields"]
        assert len(fields) == 3
        assert all(f["inline"] for f in fields)
        assert fields[0]["name"] == "Target"
        assert fields[0]["value"] == "`empty.com`"
        assert fields[1]["name"] == "Type"
        assert fields[1]["value"] == "DOMAIN"
        assert fields[2]["name"] == "Status"
        assert fields[2]["value"] == "COMPLETED"

    def test_discord_with_timestamp_only(self):
        payload = {
            "target": "example.com",
            "scan_type": "domain",
            "status": "completed",
            "results": {},
            "completed_at": "2026-01-01T12:00:18Z",
        }

        result = format_discord(payload)
        embed = result["embeds"][0]

        assert embed["timestamp"] == "2026-01-01T12:00:18Z"
        assert embed["title"] == "PRISM Scan - example.com"

    def test_discord_no_timestamp(self):
        payload = {
            "target": "example.com",
            "scan_type": "domain",
            "status": "completed",
            "results": {},
        }

        result = format_discord(payload)
        embed = result["embeds"][0]

        assert "timestamp" not in embed

    def test_discord_opsec_score_only(self):
        payload = {
            "target": "example.com",
            "scan_type": "domain",
            "status": "completed",
            "results": {"opsec_score": {"score": 95, "risk_level": "MINIMAL"}},
        }

        result = format_discord(payload)
        embed = result["embeds"][0]

        assert embed["color"] == 0x00FF00
        fields = embed["fields"]
        opsec_field = next(f for f in fields if f["name"] == "OPSEC Score")
        assert opsec_field["value"] == "95/100 (MINIMAL)"

        findings_fields = [f for f in fields if f["name"] == "Notable Findings"]
        assert len(findings_fields) == 0

