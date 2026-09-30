def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."

def format_slack(payload: dict) -> dict:
    target = payload.get("target", "unknown")
    scan_type = payload.get("scan_type", "unknown")
    status = payload.get("status", "unknown")
    results = payload.get("results", {})

    opsec = results.get("opsec") or results.get("opsec_score")
    score_text = ""
    if opsec and isinstance(opsec, dict):
        score = opsec.get("score", "?")
        risk = opsec.get("risk_level", "?")
        score_text = f"*OPSEC Score:* {score}/100 ({risk})"

    findings = []
    if results.get("virustotal", {}).get("malicious", 0) > 0:
        findings.append(f"VirusTotal: {results['virustotal']['malicious']} malicious detections")
    if results.get("breaches", {}).get("found"):
        total = results["breaches"].get("total", "?")
        breaches_list = results["breaches"].get("breaches", [])
        if breaches_list:
            names = [str(b.get("name") or b.get("title") or str(b)) for b in breaches_list[:3] if b]
            if names:
                findings.append(f"Breaches: {total} found ({', '.join(names)}{'...' if len(breaches_list) > 3 else ''})")
            else:
                findings.append(f"Breaches: {total} found")
        else:
            findings.append(f"Breaches: {total} found")
    if results.get("shodan", {}).get("vulns"):
        findings.append(f"Shodan: {len(results['shodan']['vulns'])} CVEs")

    findings_text = "\n".join(f"• {f}" for f in findings) if findings else "No notable findings"

    status_emoji = ":white_check_mark:" if status == "completed" else ":x:"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"PRISM Scan {status_emoji} {status.upper()}", "emoji": True}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Target:*\n`{target}`"},
                {"type": "mrkdwn", "text": f"*Type:*\n{scan_type.upper()}"},
            ]
        },
    ]

    if score_text:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": score_text}})

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*Notable Findings:*\n{findings_text}"}
    })

    if payload.get("started_at") and payload.get("completed_at"):
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Started: {payload['started_at']} | Completed: {payload['completed_at']}"}]
        })

    return {"blocks": blocks}

FIELD_VALUE_LIMIT = 1024

def format_discord(payload: dict) -> dict:
    target = payload.get("target", "unknown")
    scan_type = payload.get("scan_type", "unknown")
    status = payload.get("status", "unknown")
    results = payload.get("results", {})

    opsec = results.get("opsec") or results.get("opsec_score")

    if status != "completed":
        color = 0xFF0000
    elif opsec and isinstance(opsec, dict):
        score = opsec.get("score", 100)
        if score <= 30:
            color = 0xFF0000
        elif score <= 60:
            color = 0xFFAA00
        else:
            color = 0x00FF00
    else:
        color = 0x5865F2

    fields = [
        {"name": "Target", "value": f"`{target}`", "inline": True},
        {"name": "Type", "value": scan_type.upper(), "inline": True},
        {"name": "Status", "value": status.upper(), "inline": True},
    ]

    if opsec and isinstance(opsec, dict):
        fields.append({
            "name": "OPSEC Score",
            "value": f"{opsec.get('score', '?')}/100 ({opsec.get('risk_level', '?')})",
            "inline": True,
        })

    findings = []
    if results.get("virustotal", {}).get("malicious", 0) > 0:
        findings.append(f"**VirusTotal:** {results['virustotal']['malicious']} malicious")
    if results.get("breaches", {}).get("found"):
        total = results["breaches"].get("total", "?")
        breaches_list = results["breaches"].get("breaches", [])
        if breaches_list:
            names = []
            for b in breaches_list[:3]:
                if isinstance(b, dict):
                    name = b.get("name") or b.get("title") or str(b)
                else:
                    name = str(b)
                if name:
                    names.append(name)
            if names:
                suffix = "..." if len(breaches_list) > 3 else ""
                findings.append(f"**Breaches:** {total} found ({', '.join(names)}{suffix})")
            else:
                findings.append(f"**Breaches:** {total} found")
        else:
            findings.append(f"**Breaches:** {total} found")
    if results.get("shodan", {}).get("vulns"):
        findings.append(f"**Shodan CVEs:** {len(results['shodan']['vulns'])}")
    if results.get("cert_transparency", {}).get("subdomains"):
        findings.append(f"**Subdomains:** {len(results['cert_transparency']['subdomains'])}")

    if findings:
        value = "\n".join(findings)
        if len(value) > FIELD_VALUE_LIMIT:
            value = value[:FIELD_VALUE_LIMIT - 3] + "..."
        fields.append({
            "name": "Notable Findings",
            "value": value,
            "inline": False,
        })

    embed = {
        "title": _truncate(f"PRISM Scan - {target}", 256),
        "color": color,
        "fields": fields,
        "footer": {"text": "PRISM OSINT Platform"},
    }

    if payload.get("completed_at"):
        embed["timestamp"] = payload["completed_at"]

    return {"embeds": [embed]}

