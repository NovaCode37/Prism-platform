from typing import Dict, Any, List

NODE_COLORS = {
    "target": "#00d4ff",
    "email": "#ff9f43",
    "domain": "#a29bfe",
    "subdomain": "#74b9ff",
    "ip": "#fd79a8",
    "account": "#55efc4",
    "technology": "#636e72",
    "vulnerability": "#d63031",
    "organization": "#fdcb6e",
    "url": "#81ecec",
}

def _node(node_id: str, label: str, node_type: str, title: str = "") -> Dict:
    return {
        "id": node_id,
        "label": label[:30] + ("…" if len(label) > 30 else ""),
        "full_label": label,
        "type": node_type,
        "color": NODE_COLORS.get(node_type, "#dfe6e9"),
        "title": title or label,
        "shape": _shape(node_type),
    }

def _edge(from_id: str, to_id: str, label: str = "", dashes: bool = False) -> Dict:
    return {
        "from": from_id,
        "to": to_id,
        "label": label,
        "dashes": dashes,
        "color": {"color": "#636e72", "highlight": "#00d4ff"},
        "smooth": {"type": "dynamic"},
    }

def _shape(node_type: str) -> str:
    shapes = {
        "target": "star",
        "email": "ellipse",
        "domain": "box",
        "subdomain": "box",
        "ip": "diamond",
        "account": "dot",
        "technology": "triangle",
        "vulnerability": "triangleDown",
        "organization": "hexagon",
        "url": "ellipse",
    }
    return shapes.get(node_type, "dot")

def build_graph(target: str, scan_type: str, results: Dict[str, Any]) -> Dict[str, Any]:
    nodes: List[Dict] = []
    edges: List[Dict] = []
    seen_nodes: set = set()

    def add_node(n: Dict) -> None:
        if n["id"] not in seen_nodes:
            seen_nodes.add(n["id"])
            nodes.append(n)

    def add_edge(e: Dict) -> None:
        edges.append(e)

    target_id = f"target::{target}"
    add_node(_node(target_id, target, "target", f"Target: {target}"))

    whois = results.get("whois", {})
    if whois and not whois.get("error"):
        if whois.get("org"):
            org_id = f"org::{whois['org']}"
            add_node(_node(org_id, whois["org"], "organization", f"Org: {whois['org']}"))
            add_edge(_edge(target_id, org_id, "registered by"))
        for email in whois.get("emails", []):
            eid = f"email::{email}"
            add_node(_node(eid, email, "email", f"WHOIS email: {email}"))
            add_edge(_edge(target_id, eid, "WHOIS contact"))
        for ns in whois.get("name_servers", [])[:4]:
            nid = f"domain::{ns}"
            add_node(_node(nid, ns, "domain", f"Name Server: {ns}"))
            add_edge(_edge(target_id, nid, "nameserver"))

    geoip = results.get("geoip", {})
    if geoip and not geoip.get("error") and geoip.get("ip"):
        ip_id = f"ip::{geoip['ip']}"
        loc = f"{geoip.get('city', '')}, {geoip.get('country', '')}".strip(", ")
        add_node(_node(ip_id, geoip["ip"], "ip", f"IP: {geoip['ip']} | {loc} | {geoip.get('org', '')}"))
        add_edge(_edge(target_id, ip_id, "resolves to"))
        if geoip.get("org"):
            org_id = f"org::{geoip['org']}"
            add_node(_node(org_id, geoip["org"], "organization", f"ISP/ASN: {geoip['org']}"))
            add_edge(_edge(ip_id, org_id, "hosted by"))

    ct = results.get("cert_transparency", {})
    if ct and not ct.get("error"):
        for sub in ct.get("subdomains", [])[:15]:
            if sub == target:
                continue
            sid = f"subdomain::{sub}"
            add_node(_node(sid, sub, "subdomain", f"Subdomain (CT logs): {sub}"))
            add_edge(_edge(target_id, sid, "subdomain"))

    hunter = results.get("hunter", {})
    if hunter and not hunter.get("error"):
        for email_obj in hunter.get("emails", [])[:10]:
            email = email_obj if isinstance(email_obj, str) else email_obj.get("value", "")
            if not email:
                continue
            eid = f"email::{email}"
            add_node(_node(eid, email, "email", f"Hunter.io: {email}"))
            add_edge(_edge(target_id, eid, "email found"))

    website = results.get("website", {})
    if website and not website.get("error"):
        for email in website.get("emails", [])[:5]:
            eid = f"email::{email}"
            add_node(_node(eid, email, "email", f"Found in HTML: {email}"))
            add_edge(_edge(target_id, eid, "on website", dashes=True))
        for tech in website.get("technologies", []):
            tid = f"tech::{tech}"
            add_node(_node(tid, tech, "technology", f"Technology: {tech}"))
            add_edge(_edge(target_id, tid, "uses"))
        for social in website.get("social_links", [])[:8]:
            handle = f"{social['platform']}/@{social['username']}"
            aid = f"account::{handle}"
            add_node(_node(aid, handle, "account", f"Social: {handle}"))
            add_edge(_edge(target_id, aid, "social"))

    blackbird = results.get("blackbird", [])
    if blackbird:
        found_accounts = [r for r in blackbird if isinstance(r, dict) and r.get("status") == "found"]
        for acc in found_accounts[:15]:
            handle = f"{acc.get('site', '?')}/@{target}"
            aid = f"account::{acc.get('site', '?')}"
            add_node(_node(aid, acc["site"], "account", f"Account: {acc.get('url', '')}"))
            add_edge(_edge(target_id, aid, "profile"))

    shodan = results.get("shodan", {})
    if shodan and not shodan.get("error"):
        sh_ip = shodan.get("ip", target)
        sh_id = f"ip::{sh_ip}"
        if sh_id not in seen_nodes:
            add_node(_node(sh_id, sh_ip, "ip", f"Shodan IP: {sh_ip}"))
            add_edge(_edge(target_id, sh_id, "resolves to"))
        for vuln in shodan.get("vulns", [])[:5]:
            vid = f"vuln::{vuln}"
            add_node(_node(vid, vuln, "vulnerability", f"CVE: {vuln}"))
            add_edge(_edge(sh_id, vid, "vulnerable to"))

    breaches = results.get("breaches", {})
    if breaches and not breaches.get("error"):
        breach_names = breaches.get("breaches", [])
        for breach in breach_names[:8]:
            name = breach if isinstance(breach, str) else breach.get("Name", str(breach))
            bid = f"breach::{name}"
            add_node(_node(bid, name, "vulnerability", f"Data Breach: {name}"))
            add_edge(_edge(target_id, bid, "breached"))

    return {"nodes": nodes, "edges": edges}
