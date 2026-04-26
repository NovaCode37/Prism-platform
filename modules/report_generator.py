import os
import re
import json
from datetime import datetime
from typing import Dict, Any, Optional
from jinja2 import Environment, BaseLoader

REPORT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>PRISM Report — {{ target }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  :root {
    --bg:       #0d1117;
    --surf-1:   #161b22;
    --surf-2:   #1c2128;
    --surf-3:   #21262d;
    --bdr-1:    #30363d;
    --bdr-2:    #3d4450;
    --t1:       #e6edf3;
    --t2:       #b8bfc9;
    --t3:       #6e7681;
    --blue:     #4f8ef7;
    --purple:   #7c5cfc;
    --green:    #3fb950;
    --red:      #f85149;
    --yellow:   #d29922;
    --grad:     linear-gradient(135deg, #4f8ef7, #7c5cfc);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--t1); font-family: 'Silkscreen', system-ui, sans-serif; font-size: 13px; line-height: 1.6; -webkit-font-smoothing: antialiased; }
  a { color: var(--blue); text-decoration: none; }
  a:hover { text-decoration: underline; }

  /* ── Topbar ── */
  .topbar {
    height: 48px; display: flex; align-items: center; gap: 10px;
    padding: 0 20px; border-bottom: 1px solid var(--bdr-1);
    background: var(--surf-1); position: sticky; top: 0; z-index: 10;
  }
  .topbar-brand { font-size: 15px; font-weight: 700; letter-spacing: -.3px; color: var(--t1); }
  .topbar-badge {
    font-size: 9px; font-weight: 700; letter-spacing: .1em;
    padding: 2px 6px; border-radius: 999px; color: #fff;
    background: var(--grad);
  }
  .topbar-meta { margin-left: auto; font-size: 11px; color: var(--t3); text-align: right; }

  /* ── Layout ── */
  .container { max-width: 1000px; margin: 0 auto; padding: 28px 20px; }

  /* ── Score banner ── */
  .score-banner {
    background: var(--surf-1); border: 1px solid var(--bdr-1);
    border-radius: 10px; padding: 20px 24px; margin-bottom: 24px;
    display: flex; align-items: center; gap: 28px; flex-wrap: wrap;
  }
  .score-left { display: flex; align-items: center; gap: 14px; }
  .score-num { font-size: 36px; font-weight: 800; line-height: 1; }
  .score-sub { font-size: 10px; color: var(--t3); margin-top: 2px; }
  .score-risk { font-size: 11px; font-weight: 700; margin-top: 2px; }
  .score-bars { flex: 1; min-width: 260px; display: grid; gap: 7px; }
  .cat-row { display: flex; align-items: center; gap: 10px; }
  .cat-name { width: 140px; font-size: 11px; color: var(--t3); }
  .bar-track { flex: 1; background: var(--surf-3); border-radius: 3px; height: 6px; }
  .bar-fill  { height: 100%; border-radius: 3px; }
  .cat-score { width: 44px; text-align: right; font-size: 11px; font-weight: 600; font-variant-numeric: tabular-nums; }

  /* ── Section ── */
  .section { margin-bottom: 24px; }
  .section-title {
    font-size: 11px; font-weight: 600; color: var(--t3);
    text-transform: uppercase; letter-spacing: .08em;
    padding-bottom: 7px; margin-bottom: 12px;
    border-bottom: 1px solid var(--bdr-1);
    display: flex; align-items: center; gap: 6px;
  }
  .section-title svg { opacity: .6; }

  /* ── Card ── */
  .card {
    background: var(--surf-1); border: 1px solid var(--bdr-1);
    border-radius: 8px; overflow: hidden; margin-bottom: 10px;
  }
  .card-body { padding: 14px 16px; }
  .card-head {
    padding: 7px 14px; background: var(--surf-2); border-bottom: 1px solid var(--bdr-1);
    font-size: 10px; font-weight: 600; color: var(--t3);
    text-transform: uppercase; letter-spacing: .08em;
    display: flex; align-items: center; gap: 5px;
  }

  /* ── KV rows ── */
  .kv { display: flex; gap: 12px; padding: 6px 0; border-bottom: 1px solid var(--bdr-1); font-size: 12px; }
  .kv:last-child { border-bottom: none; }
  .kv-k { color: var(--t3); width: 148px; flex-shrink: 0; }
  .kv-v { color: var(--t1); font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace; font-size: 11px; word-break: break-all; }

  /* ── Findings ── */
  .finding { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-bottom: 1px solid var(--bdr-1); }
  .finding:last-child { border-bottom: none; }
  .badge { display: inline-flex; align-items: center; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; flex-shrink: 0; }
  .badge-high   { background: rgba(248,81,73,.15);  color: var(--red); }
  .badge-med    { background: rgba(210,153,34,.15); color: var(--yellow); }
  .badge-low    { background: rgba(63,185,80,.15);  color: var(--green); }
  .badge-info   { background: rgba(79,142,247,.12); color: var(--blue); }
  .finding-msg  { font-size: 12px; color: var(--t1); }
  .finding-meta { font-size: 10px; color: var(--t3); margin-top: 1px; }

  /* ── Tables ── */
  table { width: 100%; border-collapse: collapse; }
  th { padding: 6px 12px; text-align: left; font-size: 10px; font-weight: 600; color: var(--t3); text-transform: uppercase; letter-spacing: .06em; background: var(--surf-2); border-bottom: 1px solid var(--bdr-1); }
  td { padding: 7px 12px; font-size: 12px; border-bottom: 1px solid var(--bdr-1); }
  tr:last-child td { border-bottom: none; }

  /* ── Tags ── */
  .tag     { display: inline-block; background: var(--surf-3); border: 1px solid var(--bdr-1); border-radius: 4px; padding: 1px 7px; font-size: 10px; margin: 2px; color: var(--t2); font-family: ui-monospace, monospace; }
  .tag-red { border-color: rgba(248,81,73,.4); color: var(--red); background: rgba(248,81,73,.07); }
  .tag-blue{ border-color: rgba(79,142,247,.35); color: var(--blue); background: rgba(79,142,247,.07); }

  /* ── Footer ── */
  .footer { text-align: center; color: var(--t3); font-size: 11px; padding: 28px 20px; border-top: 1px solid var(--bdr-1); margin-top: 36px; }

  /* ── Print / PDF ── */
  @media print {
    @page { margin: 12mm 10mm; size: A4; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; color-adjust: exact !important; }
    body { font-size: 11px !important; }
    .topbar { position: static !important; }
    .card, .score-banner, .section { break-inside: avoid; }
  }
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute"><defs>
  <linearGradient id="lg" x1="0" y1="0" x2="52" y2="44" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#4f8ef7"/>
    <stop offset="100%" stop-color="#7c5cfc"/>
  </linearGradient>
</defs></svg>

<!-- Topbar -->
<div class="topbar">
  <svg width="26" height="22" viewBox="0 0 52 44" fill="none">
    <path d="M2 22C2 22 13 6 26 6C39 6 50 22 50 22C50 22 39 38 26 38C13 38 2 22 2 22Z" stroke="url(#lg)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="26" cy="22" r="9" stroke="url(#lg)" stroke-width="2"/>
    <circle cx="26" cy="22" r="4.5" stroke="url(#lg)" stroke-width="1.2" opacity="0.6"/>
    <circle cx="26" cy="22" r="2.2" fill="url(#lg)"/>
    <line x1="26" y1="13" x2="26" y2="17" stroke="url(#lg)" stroke-width="1.8" stroke-linecap="round"/>
    <line x1="26" y1="27" x2="26" y2="31" stroke="url(#lg)" stroke-width="1.8" stroke-linecap="round"/>
    <line x1="17" y1="22" x2="21" y2="22" stroke="url(#lg)" stroke-width="1.8" stroke-linecap="round"/>
    <line x1="31" y1="22" x2="35" y2="22" stroke="url(#lg)" stroke-width="1.8" stroke-linecap="round"/>
    <path d="M36 10 A16 16 0 0 1 44 22" stroke="url(#lg)" stroke-width="1.5" stroke-linecap="round" opacity="0.45"/>
  </svg>
  <span class="topbar-brand">PRISM</span>
  <span class="topbar-badge">v2.0</span>
  <div class="topbar-meta">
    Intelligence Report &nbsp;·&nbsp; {{ generated_at }}
  </div>
</div>

<div class="container">

<!-- Scan info banner -->
<div style="margin-bottom:20px;padding:12px 16px;background:var(--surf-1);border:1px solid var(--bdr-1);border-radius:8px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
  <div>
    <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px;">Target</div>
    <div style="font-family:ui-monospace,monospace;font-size:13px;font-weight:600;color:var(--t1);">{{ target }}</div>
  </div>
  <div>
    <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px;">Type</div>
    <div style="font-size:12px;color:var(--t2);">{{ scan_type }}</div>
  </div>
  <div>
    <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px;">Generated</div>
    <div style="font-size:12px;color:var(--t2);">{{ generated_at }}</div>
  </div>
</div>

{% if opsec %}
<!-- OPSEC Score -->
<div class="score-banner">
  <div class="score-left">
    <div>
      <div class="score-num" style="color:{{ opsec_circle_color }}">{{ opsec.score }}</div>
      <div class="score-sub">/ 100 OPSEC</div>
      <div class="score-risk" style="color:{{ opsec_circle_color }}">{{ opsec.risk_level }} RISK</div>
    </div>
  </div>
  <div class="score-bars">
    {% for key, cat in opsec.categories.items() %}
    <div class="cat-row">
      <div class="cat-name">{{ cat_labels[key] }}</div>
      <div class="bar-track">
        <div class="bar-fill" style="width:{{ cat.percent }}%;background:{{ bar_color(cat.percent) }};"></div>
      </div>
      <div class="cat-score" style="color:{{ bar_color(cat.percent) }}">{{ cat.score }}/{{ cat.max }}</div>
    </div>
    {% endfor %}
  </div>
</div>

{% if opsec.all_findings %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    Security Findings
  </div>
  <div class="card"><div class="card-body">
    {% for f in opsec.all_findings %}
    <div class="finding">
      <span class="badge {% if f.severity in ('CRITICAL','HIGH') %}badge-high{% elif f.severity == 'MEDIUM' %}badge-med{% elif f.severity == 'LOW' %}badge-low{% else %}badge-info{% endif %}">{{ f.severity }}</span>
      <div>
        <div class="finding-msg">{{ f.message }}</div>
        <div class="finding-meta">−{{ f.deduction }} pts</div>
      </div>
    </div>
    {% endfor %}
  </div></div>
</div>
{% endif %}
{% endif %}

<!-- WHOIS -->
{% if results.whois and not results.whois.error %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
    WHOIS Registration
  </div>
  <div class="card"><div class="card-body">
    <div class="kv"><span class="kv-k">Registrar</span><span class="kv-v">{{ results.whois.registrar or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">Organization</span><span class="kv-v">{{ results.whois.org or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">Country</span><span class="kv-v">{{ results.whois.country or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">Created</span><span class="kv-v">{{ (results.whois.creation_date or 'N/A')[:10] }}</span></div>
    <div class="kv"><span class="kv-k">Expires</span><span class="kv-v">{{ (results.whois.expiration_date or 'N/A')[:10] }}</span></div>
    {% if results.whois.emails %}
    <div class="kv"><span class="kv-k">Contact Emails</span><span class="kv-v">{% for e in results.whois.emails %}<span class="tag tag-red">{{ e }}</span>{% endfor %}</span></div>
    {% endif %}
    {% if results.whois.name_servers %}
    <div class="kv"><span class="kv-k">Name Servers</span><span class="kv-v">{% for ns in results.whois.name_servers[:4] %}<span class="tag">{{ ns }}</span>{% endfor %}</span></div>
    {% endif %}
  </div></div>
</div>
{% endif %}

<!-- DNS -->
{% if results.dns and results.dns.records %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
    DNS Records
  </div>
  <div class="card">
    <div class="card-head">Record types</div>
    <div class="card-body">
    {% for rtype, records in results.dns.records.items() %}{% if records %}
    <div style="margin-bottom:10px;">
      <div style="color:var(--blue);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">{{ rtype }}</div>
      {% for r in records %}
      <div style="font-family:ui-monospace,monospace;font-size:11px;color:var(--t2);padding:2px 0;">{% if r is mapping %}{{ r | tojson }}{% else %}{{ r }}{% endif %}</div>
      {% endfor %}
    </div>
    {% endif %}{% endfor %}
    </div>
  </div>
</div>
{% endif %}

<!-- GeoIP -->
{% if results.geoip and not results.geoip.error %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
    Geolocation
  </div>
  <div class="card"><div class="card-body">
    <div class="kv"><span class="kv-k">IP Address</span><span class="kv-v">{{ results.geoip.ip }}</span></div>
    <div class="kv"><span class="kv-k">Location</span><span class="kv-v">{{ results.geoip.city }}, {{ results.geoip.region }}, {{ results.geoip.country_name or results.geoip.country }}</span></div>
    <div class="kv"><span class="kv-k">Coordinates</span><span class="kv-v">{{ results.geoip.loc or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">Organization</span><span class="kv-v">{{ results.geoip.org or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">Timezone</span><span class="kv-v">{{ results.geoip.timezone or 'N/A' }}</span></div>
  </div>
  {% if results.geoip.loc %}
  <div id="report-map" style="width:100%;height:320px;border-radius:0 0 8px 8px;margin-top:0;"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
  (function(){
    var loc = "{{ results.geoip.loc }}".split(",");
    var lat = parseFloat(loc[0]), lng = parseFloat(loc[1]);
    var map = L.map('report-map', {zoomControl:true, scrollWheelZoom:false, attributionControl:false}).setView([lat,lng], 11);
    L.control.attribution({prefix:false}).addTo(map);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com">CARTO</a>',
      subdomains: 'abcd', maxZoom: 19
    }).addTo(map);
    var icon = L.divIcon({
      html: '<div style="width:14px;height:14px;background:#4f8ef7;border:2px solid #fff;border-radius:50%;box-shadow:0 0 8px rgba(79,142,247,.8);"></div>',
      iconSize:[14,14], iconAnchor:[7,7], className:''
    });
    L.marker([lat,lng],{icon:icon}).addTo(map)
      .bindPopup('<b>{{ results.geoip.ip }}</b><br>{{ results.geoip.city }}, {{ results.geoip.country_name or results.geoip.country }}<br>{{ results.geoip.org }}');
  })();
  </script>
  {% endif %}
  </div>
</div>
{% endif %}

<!-- Certificate Transparency -->
{% if results.cert_transparency and results.cert_transparency.subdomains %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
    Certificate Transparency &mdash; Subdomains
  </div>
  <div class="card">
    <div class="card-head">{{ results.cert_transparency.subdomains|length }} subdomains &nbsp;·&nbsp; {{ results.cert_transparency.total_certs }} certificates</div>
    <div class="card-body">
      {% for sub in results.cert_transparency.subdomains %}<span class="tag tag-blue">{{ sub }}</span>{% endfor %}
    </div>
  </div>
</div>
{% endif %}

<!-- Username Search (Blackbird) -->
{% if results.blackbird %}
{% set found_accounts = results.blackbird | selectattr("status","equalto","found") | list %}
{% if found_accounts %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
    Username Search &mdash; {{ found_accounts|length }} Account(s) Found
  </div>
  <div class="card">
    <table>
      <thead><tr><th>Platform</th><th>Profile URL</th><th>Response</th></tr></thead>
      <tbody>
      {% for r in found_accounts %}
      <tr>
        <td style="font-weight:500">{{ r.site }}</td>
        <td><a href="{{ r.url }}">{{ r.url }}</a></td>
        <td style="color:var(--t3)">{{ "%.2f"|format(r.response_time) }}s</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endif %}
{% endif %}

<!-- Threat Intel — VirusTotal -->
{% if results.virustotal and not results.virustotal.error %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
    VirusTotal Reputation
  </div>
  <div class="card"><div class="card-body">
    <div class="kv"><span class="kv-k">Malicious</span><span class="kv-v" style="color:var(--red);font-weight:700">{{ results.virustotal.malicious }}</span></div>
    <div class="kv"><span class="kv-k">Suspicious</span><span class="kv-v" style="color:var(--yellow)">{{ results.virustotal.suspicious }}</span></div>
    <div class="kv"><span class="kv-k">Harmless</span><span class="kv-v" style="color:var(--green)">{{ results.virustotal.harmless }}</span></div>
    <div class="kv"><span class="kv-k">Undetected</span><span class="kv-v">{{ results.virustotal.undetected }}</span></div>
    {% if results.virustotal.country %}<div class="kv"><span class="kv-k">Country</span><span class="kv-v">{{ results.virustotal.country }}</span></div>{% endif %}
    {% if results.virustotal.as_owner %}<div class="kv"><span class="kv-k">ASN</span><span class="kv-v">{{ results.virustotal.as_owner }}</span></div>{% endif %}
  </div></div>
</div>
{% endif %}

<!-- AbuseIPDB -->
{% if results.abuseipdb and not results.abuseipdb.error %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    AbuseIPDB
  </div>
  <div class="card"><div class="card-body">
    <div class="kv"><span class="kv-k">Abuse Score</span>
      <span class="kv-v" style="color:{% if results.abuseipdb.abuse_score>=50 %}var(--red){% elif results.abuseipdb.abuse_score>=10 %}var(--yellow){% else %}var(--green){% endif %};font-weight:700">{{ results.abuseipdb.abuse_score }}/100</span>
    </div>
    <div class="kv"><span class="kv-k">Total Reports</span><span class="kv-v">{{ results.abuseipdb.total_reports }}</span></div>
    <div class="kv"><span class="kv-k">ISP</span><span class="kv-v">{{ results.abuseipdb.isp or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">Usage Type</span><span class="kv-v">{{ results.abuseipdb.usage_type or 'N/A' }}</span></div>
    {% if results.abuseipdb.is_tor %}<div class="kv"><span class="kv-k">TOR Node</span><span class="kv-v" style="color:var(--red);font-weight:600">YES</span></div>{% endif %}
  </div></div>
</div>
{% endif %}

<!-- Shodan -->
{% if results.shodan and not results.shodan.error %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    Shodan &mdash; Open Ports &amp; Services
  </div>
  <div class="card">
    {% if results.shodan.open_ports or results.shodan.vulns %}
    <div class="card-body" style="border-bottom:1px solid var(--bdr-1);">
      {% if results.shodan.open_ports %}
      <div style="margin-bottom:8px;">
        <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">Open Ports</div>
        {% for p in results.shodan.open_ports %}
        <span class="tag {% if p in [21,22,23,3389,5900,445,3306,5432,27017,6379] %}tag-red{% endif %}">{{ p }}</span>
        {% endfor %}
      </div>
      {% endif %}
      {% if results.shodan.vulns %}
      <div>
        <div style="font-size:10px;color:var(--red);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">CVEs Found</div>
        {% for v in results.shodan.vulns %}<span class="tag tag-red">{{ v }}</span>{% endfor %}
      </div>
      {% endif %}
    </div>
    {% endif %}
    {% if results.shodan.services %}
    <table>
      <thead><tr><th>Port</th><th>Product</th><th>Version</th></tr></thead>
      <tbody>
      {% for svc in results.shodan.services %}
      <tr>
        <td style="font-family:ui-monospace,monospace;font-size:11px">{{ svc.port }}/{{ svc.transport }}</td>
        <td>{{ svc.product or '—' }}</td>
        <td style="color:var(--t3)">{{ svc.version or '—' }}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% endif %}
  </div>
</div>
{% endif %}

<!-- Wayback Machine -->
{% if results.wayback %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    Wayback Machine
  </div>
  <div class="card">
    {% if results.wayback.snapshots %}
    <div class="card-head">{{ results.wayback.total_snapshots }} snapshots &nbsp;·&nbsp; First: {{ results.wayback.first_snapshot }} &nbsp;·&nbsp; Last: {{ results.wayback.last_snapshot }}</div>
    {% endif %}
    {% if results.wayback.interesting %}
    <div class="card-body">
      <div style="font-size:10px;color:var(--red);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;font-weight:600;">Sensitive URLs in Archive</div>
      {% for url in results.wayback.interesting[:10] %}
      <div style="font-family:ui-monospace,monospace;font-size:11px;padding:2px 0;"><a href="{{ url }}">{{ url }}</a></div>
      {% endfor %}
    </div>
    {% endif %}
  </div>
</div>
{% endif %}

<!-- Website Analysis -->
{% if results.website and not results.website.error %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
    Website Analysis
  </div>
  <div class="card"><div class="card-body">
    {% if results.website.title %}<div class="kv"><span class="kv-k">Title</span><span class="kv-v">{{ results.website.title }}</span></div>{% endif %}
    {% if results.website.technologies %}
    <div class="kv"><span class="kv-k">Technologies</span><span class="kv-v">{% for t in results.website.technologies %}<span class="tag">{{ t }}</span>{% endfor %}</span></div>
    {% endif %}
    {% if results.website.emails %}
    <div class="kv"><span class="kv-k">Emails Found</span><span class="kv-v">{% for e in results.website.emails %}<span class="tag tag-red">{{ e }}</span>{% endfor %}</span></div>
    {% endif %}
    {% if results.website.social_links %}
    <div class="kv"><span class="kv-k">Social Links</span><span class="kv-v">{% for s in results.website.social_links %}<span class="tag tag-blue">{{ s.platform }}/@{{ s.username }}</span>{% endfor %}</span></div>
    {% endif %}
  </div></div>
</div>
{% endif %}

<div class="footer">
  PRISM v2.0 &nbsp;&middot;&nbsp; {{ generated_at }} &nbsp;&middot;&nbsp; For authorized security research only.
</div>

</div>
</body>
</html>"""

def _bar_color(pct: int) -> str:
    if pct >= 75:
        return "#3fb950"
    if pct >= 50:
        return "#d29922"
    return "#f85149"

def _opsec_circle_color(score: int) -> str:
    if score >= 71:
        return "#3fb950"
    if score >= 51:
        return "#d29922"
    return "#f85149"

CAT_LABELS = {
    "data_exposure": "Data Exposure",
    "identity_opsec": "Identity OPSEC",
    "infrastructure": "Infrastructure",
    "web_security": "Web Security",
}

def generate_html_report(
    target: str,
    scan_type: str,
    results: Dict[str, Any],
    opsec: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> str:
    env = Environment(loader=BaseLoader(), autoescape=True)
    env.filters["tojson"] = lambda v: json.dumps(v)
    template = env.from_string(REPORT_TEMPLATE)

    context = {
        "target": target,
        "scan_type": scan_type,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "results": results,
        "opsec": opsec,
        "opsec_circle_color": _opsec_circle_color(opsec["score"]) if opsec else "#636e72",
        "cat_labels": CAT_LABELS,
        "bar_color": _bar_color,
    }

    html = template.render(**context)

    if output_path is None:
        results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
        os.makedirs(results_dir, exist_ok=True)
        safe_target = re.sub(r'[^a-zA-Z0-9._\-]', '_', target)[:80]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(results_dir, f"report_{safe_target}_{ts}.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def generate_pdf_report(
    target: str,
    scan_type: str,
    results: Dict[str, Any],
    opsec: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Generate a PDF version of the scan report using WeasyPrint.

    WeasyPrint does not execute JavaScript, so the interactive Leaflet map
    is omitted. All other report data (OPSEC score, findings, WHOIS, DNS,
    threat intel, etc.) is preserved.
    """
    try:
        from weasyprint import HTML
    except ImportError as e:
        raise ImportError(
            "weasyprint is required for PDF export. Install with: pip install weasyprint"
        ) from e

    env = Environment(loader=BaseLoader(), autoescape=True)
    env.filters["tojson"] = lambda v: json.dumps(v)
    template = env.from_string(REPORT_TEMPLATE)

    context = {
        "target": target,
        "scan_type": scan_type,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "results": results,
        "opsec": opsec,
        "opsec_circle_color": _opsec_circle_color(opsec["score"]) if opsec else "#636e72",
        "cat_labels": CAT_LABELS,
        "bar_color": _bar_color,
    }

    html = template.render(**context)
    # Strip Leaflet JS/CSS that WeasyPrint cannot render
    html = re.sub(r'<link[^>]*leaflet[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<script[^>]*leaflet[^>]*></script>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<div id="report-map"[^>]*></div>', '', html)

    if output_path is None:
        results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
        os.makedirs(results_dir, exist_ok=True)
        safe_target = re.sub(r'[^a-zA-Z0-9._\-]', '_', target)[:80]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(results_dir, f"report_{safe_target}_{ts}.pdf")

    HTML(string=html).write_pdf(output_path)
    return output_path
