import os
import re
import json
from datetime import datetime
from typing import Dict, Any, Optional
from jinja2 import Environment, BaseLoader

from modules.report_i18n import make_translator

REPORT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>PRISM Report - {{ target }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  :root {
    --bg: #ffffff;
    --surf-1: #f6f8fa;
    --surf-2: #eaeef2;
    --surf-3: #d0d7de;
    --bdr-1: #d0d7de;
    --bdr-2: #b1bac4;
    --t1: #24292f;
    --t2: #424a53;
    --t3: #656d76;
    --blue: #0969da;
    --purple: #8250df;
    --green: #1a7f37;
    --red: #cf222e;
    --yellow: #9a6700;
    --grad: linear-gradient(135deg, #0969da, #8250df);
  }

  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0d1117;
      --surf-1: #161b22;
      --surf-2: #1c2128;
      --surf-3: #21262d;
      --bdr-1: #30363d;
      --bdr-2: #3d4450;
      --t1: #e6edf3;
      --t2: #b8bfc9;
      --t3: #6e7681;
      --blue: #4f8ef7;
      --purple: #7c5cfc;
      --green: #3fb950;
      --red: #f85149;
      --yellow: #d29922;
      --grad: linear-gradient(135deg, #4f8ef7, #7c5cfc);
    }
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--t1);
    font-family: 'Silkscreen', system-ui, sans-serif;
    font-size: 13px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
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
    /* xhtml2pdf ignores prefers-color-scheme, so force light theme for PDF */
    :root {
      --bg: #ffffff !important;
      --surf-1: #f6f8fa !important;
      --surf-2: #eaeef2 !important;
      --surf-3: #d0d7de !important;
      --bdr-1: #d0d7de !important;
      --bdr-2: #b1bac4 !important;
      --t1: #24292f !important;
      --t2: #424a53 !important;
      --t3: #656d76 !important;
      --blue: #0969da !important;
      --purple: #8250df !important;
      --green: #1a7f37 !important;
      --red: #cf222e !important;
      --yellow: #9a6700 !important;
      --grad: linear-gradient(135deg, #0969da, #8250df) !important;
    }
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
    <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px;">{{ t('report.target') }}</div>
    <div style="font-family:ui-monospace,monospace;font-size:13px;font-weight:600;color:var(--t1);">{{ target }}</div>
  </div>
  <div>
    <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px;">{{ t('report.scanType') }}</div>
    <div style="font-size:12px;color:var(--t2);">{{ scan_type }}</div>
  </div>
  <div>
    <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px;">{{ t('report.generated') }}</div>
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
      <div class="score-risk" style="color:{{ opsec_circle_color }}">{{ t('opsec.risk', level=opsec.risk_level) }}</div>
    </div>
  </div>
  <div class="score-bars">
    {% for key, cat in opsec.categories.items() %}
    <div class="cat-row">
      <div class="cat-name">{{ t('opsec.cat.' + key) }}</div>
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
    {{ t('opsec.findings', n=opsec.all_findings|length) }}
  </div>
  <div class="card"><div class="card-body">
    {% for f in opsec.all_findings %}
    <div class="finding">
      <span class="badge {% if f.severity in ('CRITICAL','HIGH') %}badge-high{% elif f.severity == 'MEDIUM' %}badge-med{% elif f.severity == 'LOW' %}badge-low{% else %}badge-info{% endif %}">{{ f.severity }}</span>
      <div>
        <div class="finding-msg">{{ f.message }}</div>
        <div class="finding-meta">−{{ f.deduction }} {{ t('opsec.points') }}</div>
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
    {{ t('whois.title') }}
  </div>
  <div class="card"><div class="card-body">
    <div class="kv"><span class="kv-k">{{ t('whois.registrar') }}</span><span class="kv-v">{{ results.whois.registrar or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('whois.organization') }}</span><span class="kv-v">{{ results.whois.org or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('whois.country') }}</span><span class="kv-v">{{ results.whois.country or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('whois.created') }}</span><span class="kv-v">{{ (results.whois.creation_date or 'N/A')[:10] }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('whois.expires') }}</span><span class="kv-v">{{ (results.whois.expiration_date or 'N/A')[:10] }}</span></div>
    {% if results.whois.emails %}
    <div class="kv"><span class="kv-k">{{ t('whois.emails') if t('whois.emails') != 'whois.emails' else 'Contact Emails' }}</span><span class="kv-v">{% for e in results.whois.emails %}<span class="tag tag-red">{{ e }}</span>{% endfor %}</span></div>
    {% endif %}
    {% if results.whois.name_servers %}
    <div class="kv"><span class="kv-k">{{ t('whois.nameServers') }}</span><span class="kv-v">{% for ns in results.whois.name_servers[:4] %}<span class="tag">{{ ns }}</span>{% endfor %}</span></div>
    {% endif %}
  </div></div>
</div>
{% endif %}

<!-- DNS -->
{% if results.dns and results.dns.records %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
    {{ t('dns.title') }}
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
    {{ t('geoip.title') }}
  </div>
  <div class="card"><div class="card-body">
    <div class="kv"><span class="kv-k">{{ t('geoip.ip') }}</span><span class="kv-v">{{ results.geoip.ip }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('geoip.city') }}</span><span class="kv-v">{{ results.geoip.city }}, {{ results.geoip.region }}, {{ results.geoip.country_name or results.geoip.country }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('geoip.coordinates') }}</span><span class="kv-v">{{ results.geoip.loc or 'N/A' }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('geoip.organization') }}</span><span class="kv-v">{{ results.geoip.org or 'N/A' }}</span></div>
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
    {{ t('subdomains.title', n=results.cert_transparency.subdomains|length) }}
  </div>
  <div class="card">
    <div class="card-head">{{ results.cert_transparency.subdomains|length }} &nbsp;·&nbsp; {{ results.cert_transparency.total_certs }}</div>
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
    {{ t('accounts.title', n=found_accounts|length) }}
  </div>
  <div class="card">
    <table>
      <thead><tr><th>{{ t('accounts.site') }}</th><th>{{ t('accounts.url') }}</th><th>Time</th></tr></thead>
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

<!-- Threat Intel - VirusTotal -->
{% if results.virustotal and not results.virustotal.error %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
    {{ t('virustotal.title') }}
  </div>
  <div class="card"><div class="card-body">
    <div class="kv"><span class="kv-k">{{ t('virustotal.malicious') }}</span><span class="kv-v" style="color:var(--red);font-weight:700">{{ results.virustotal.malicious }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('virustotal.suspicious') }}</span><span class="kv-v" style="color:var(--yellow)">{{ results.virustotal.suspicious }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('virustotal.harmless') }}</span><span class="kv-v" style="color:var(--green)">{{ results.virustotal.harmless }}</span></div>
    <div class="kv"><span class="kv-k">Undetected</span><span class="kv-v">{{ results.virustotal.undetected }}</span></div>
    {% if results.virustotal.country %}<div class="kv"><span class="kv-k">{{ t('geoip.country') }}</span><span class="kv-v">{{ results.virustotal.country }}</span></div>{% endif %}
    {% if results.virustotal.as_owner %}<div class="kv"><span class="kv-k">ASN</span><span class="kv-v">{{ results.virustotal.as_owner }}</span></div>{% endif %}
  </div></div>
</div>
{% endif %}

<!-- AbuseIPDB -->
{% if results.abuseipdb and not results.abuseipdb.error %}
<div class="section">
  <div class="section-title">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    {{ t('abuseipdb.title') }}
  </div>
  <div class="card"><div class="card-body">
    <div class="kv"><span class="kv-k">{{ t('abuseipdb.confidence') }}</span>
      <span class="kv-v" style="color:{% if results.abuseipdb.abuse_score>=50 %}var(--red){% elif results.abuseipdb.abuse_score>=10 %}var(--yellow){% else %}var(--green){% endif %};font-weight:700">{{ results.abuseipdb.abuse_score }}/100</span>
    </div>
    <div class="kv"><span class="kv-k">{{ t('abuseipdb.totalReports') }}</span><span class="kv-v">{{ results.abuseipdb.total_reports }}</span></div>
    <div class="kv"><span class="kv-k">{{ t('abuseipdb.isp') }}</span><span class="kv-v">{{ results.abuseipdb.isp or 'N/A' }}</span></div>
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
    {{ t('shodan.title') }}
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
        <td>{{ svc.product or '-' }}</td>
        <td style="color:var(--t3)">{{ svc.version or '-' }}</td>
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
  {{ t('report.footer') }} &nbsp;&middot;&nbsp; {{ generated_at }} &nbsp;&middot;&nbsp; PRISM v2.1.1
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

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_PDF_FONTS = (
    ("DejaVuSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ("DejaVuSansMono", "DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf"),
)
_pdf_fonts_registered = False


def _register_pdf_fonts() -> None:
    global _pdf_fonts_registered
    if _pdf_fonts_registered:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    import xhtml2pdf.default as xhtml2pdf_default

    for family, regular, bold in _PDF_FONTS:
        regular_path = os.path.join(_FONTS_DIR, regular)
        bold_path = os.path.join(_FONTS_DIR, bold)
        if not os.path.exists(regular_path):
            continue
        pdfmetrics.registerFont(TTFont(family, regular_path))
        bold_name = family
        if os.path.exists(bold_path):
            bold_name = f"{family}-Bold"
            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
        registerFontFamily(family, normal=family, bold=bold_name,
                           italic=family, boldItalic=bold_name)

        key = family.lower()
        xhtml2pdf_default.DEFAULT_FONT[key] = family
        xhtml2pdf_default.DEFAULT_FONT[f"{key}-bold"] = bold_name
        xhtml2pdf_default.DEFAULT_FONT[f"{key}-oblique"] = family
        xhtml2pdf_default.DEFAULT_FONT[f"{key}-boldoblique"] = bold_name
    _pdf_fonts_registered = True


def generate_html_report(
    target: str,
    scan_type: str,
    results: Dict[str, Any],
    opsec: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    lang: str = "en",
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
        "t": make_translator(lang),
        "lang": lang,
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


PDF_REPORT_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<title>PRISM Report - {{ target }}</title>
<style>
  @page { size: A4; margin: 1.6cm 1.4cm; }
  body { font-family: 'DejaVuSans', Helvetica, Arial, sans-serif; font-size: 10pt; color: #1a1f2b; }
  h1 { font-size: 18pt; margin: 0 0 4pt 0; color: #4f8ef7; }
  h2 { font-size: 12pt; margin: 14pt 0 6pt 0; color: #1a1f2b;
       border-bottom: 1pt solid #d0d7de; padding-bottom: 3pt; }
  h3 { font-size: 11pt; margin: 10pt 0 4pt 0; color: #4f5563; }
  .muted { color: #6e7681; font-size: 9pt; }
  .target { font-family: 'DejaVuSansMono', Courier, monospace; font-size: 11pt; color: #1a1f2b; }

  table { width: 100%; border-collapse: collapse; margin: 4pt 0 8pt 0; }
  td, th { padding: 4pt 6pt; vertical-align: top; font-size: 9.5pt;
           border-bottom: 0.5pt solid #e1e6ec; }
  th { background: #f4f6f9; text-align: left; font-weight: bold; color: #4f5563; }
  td.label { color: #6e7681; width: 32%; }
  td.value { color: #1a1f2b; font-family: 'DejaVuSansMono', Courier, monospace; font-size: 9pt; word-break: break-all; }

  .score-box { background: #f4f6f9; border: 1pt solid #d0d7de; border-radius: 4pt;
               padding: 10pt 12pt; margin-bottom: 10pt; }
  .score-num { font-size: 26pt; font-weight: bold; color: {{ opsec_circle_color }}; }
  .score-risk { font-size: 10pt; font-weight: bold; color: {{ opsec_circle_color }}; }

  .badge { display: inline-block; padding: 1pt 5pt; border-radius: 3pt;
           font-size: 8pt; font-weight: bold; color: #fff; }
  .badge-high { background: #f85149; }
  .badge-med  { background: #d29922; }
  .badge-low  { background: #3fb950; }
  .badge-info { background: #4f8ef7; }

  .finding { padding: 4pt 0; border-bottom: 0.5pt solid #e1e6ec; }
  .finding-msg { color: #1a1f2b; font-size: 10pt; }
  .finding-meta { color: #6e7681; font-size: 8.5pt; margin-top: 1pt; }

  .footer { margin-top: 18pt; padding-top: 8pt; border-top: 0.5pt solid #d0d7de;
            color: #8b95a3; font-size: 8.5pt; text-align: center; }
</style>
</head>
<body>

<h1>{{ t('report.title') }}</h1>
<div class="muted">{{ t('report.target') }}: <span class="target">{{ target }}</span>
  &nbsp;·&nbsp; {{ t('report.scanType') }}: {{ scan_type }}
  &nbsp;·&nbsp; {{ t('report.generated') }}: {{ generated_at }}</div>

{% if opsec %}
<div class="score-box">
  <table><tr>
    <td style="width: 90pt; vertical-align: middle;">
      <div class="score-num">{{ opsec.score }}</div>
      <div class="score-risk">{{ t('opsec.risk', level=opsec.risk_level) }}</div>
      <div class="muted">{{ t('opsec.score') }}</div>
    </td>
    <td style="vertical-align: middle;">
      <table>
        {% for key, cat in opsec.categories.items() %}
        <tr>
          <td class="label" style="width: 35%;">{{ t('opsec.cat.' + key) }}</td>
          <td style="width: 50%;">
            <div style="background: #d0d7de; height: 5pt; border-radius: 2pt;">
              <div style="background: {{ bar_color(cat.percent) }}; height: 5pt; width: {{ cat.percent }}%; border-radius: 2pt;"></div>
            </div>
          </td>
          <td class="value" style="text-align: right;">{{ cat.score }}/{{ cat.max }}</td>
        </tr>
        {% endfor %}
      </table>
    </td>
  </tr></table>
</div>

{% if opsec.all_findings %}
<h2>{{ t('opsec.findings', n=opsec.all_findings|length) }}</h2>
{% for f in opsec.all_findings %}
<div class="finding">
  <span class="badge {% if f.severity == 'HIGH' %}badge-high{% elif f.severity == 'MEDIUM' %}badge-med{% else %}badge-low{% endif %}">{{ f.severity }}</span>
  <span class="finding-msg">{{ f.message }}</span>
  <div class="finding-meta">−{{ f.deduction }} {{ t('opsec.points') }} · {{ t('opsec.cat.' + f.category) }}</div>
</div>
{% endfor %}
{% endif %}
{% endif %}

{% set whois = results.get('whois') %}
{% if whois and not whois.get('error') %}
<h2>{{ t('whois.title') }}</h2>
<table>
  {% if whois.registrar %}<tr><td class="label">{{ t('whois.registrar') }}</td><td class="value">{{ whois.registrar }}</td></tr>{% endif %}
  {% if whois.org %}<tr><td class="label">{{ t('whois.organization') }}</td><td class="value">{{ whois.org }}</td></tr>{% endif %}
  {% if whois.creation_date %}<tr><td class="label">{{ t('whois.created') }}</td><td class="value">{{ whois.creation_date }}</td></tr>{% endif %}
  {% if whois.expiration_date %}<tr><td class="label">{{ t('whois.expires') }}</td><td class="value">{{ whois.expiration_date }}</td></tr>{% endif %}
  {% if whois.country %}<tr><td class="label">{{ t('whois.country') }}</td><td class="value">{{ whois.country }}</td></tr>{% endif %}
  {% if whois.name_servers %}<tr><td class="label">{{ t('whois.nameServers') }}</td><td class="value">{{ whois.name_servers|join(', ') }}</td></tr>{% endif %}
</table>
{% endif %}

{% set dns = results.get('dns') %}
{% if dns and dns.get('records') %}
<h2>{{ t('dns.title') }}</h2>
<table>
  {% for rtype, vals in dns.records.items() %}
  <tr><td class="label">{{ rtype }}</td><td class="value">{{ vals|join(', ') if vals is iterable and vals is not string else vals }}</td></tr>
  {% endfor %}
</table>
{% endif %}

{% set geoip = results.get('geoip') %}
{% if geoip and not geoip.get('error') %}
<h2>{{ t('geoip.title') }}</h2>
<table>
  {% if geoip.ip %}<tr><td class="label">{{ t('geoip.ip') }}</td><td class="value">{{ geoip.ip }}</td></tr>{% endif %}
  {% if geoip.city %}<tr><td class="label">{{ t('geoip.city') }}</td><td class="value">{{ geoip.city }}</td></tr>{% endif %}
  {% if geoip.country_name or geoip.country %}<tr><td class="label">{{ t('geoip.country') }}</td><td class="value">{{ geoip.country_name or geoip.country }}</td></tr>{% endif %}
  {% if geoip.org %}<tr><td class="label">{{ t('geoip.organization') }}</td><td class="value">{{ geoip.org }}</td></tr>{% endif %}
  {% if geoip.loc %}<tr><td class="label">{{ t('geoip.coordinates') }}</td><td class="value">{{ geoip.loc }}</td></tr>{% endif %}
</table>
{% endif %}

{% set ct = results.get('cert_transparency') %}
{% if ct and ct.subdomains %}
<h2>{{ t('subdomains.title', n=ct.subdomains|length) }}</h2>
<table>
  {% for sub in ct.subdomains[:80] %}
  <tr><td class="value">{{ sub }}</td></tr>
  {% endfor %}
</table>
{% if ct.subdomains|length > 80 %}<div class="muted">{{ t('subdomains.more', n=ct.subdomains|length - 80) }}</div>{% endif %}
{% endif %}

{% set bb = results.get('blackbird') %}
{% if bb %}
{% set found = bb|selectattr('status', 'equalto', 'found')|list %}
{% if found %}
<h2>{{ t('accounts.title', n=found|length) }}</h2>
<table><tr><th>{{ t('accounts.site') }}</th><th>{{ t('accounts.url') }}</th></tr>
{% for r in found %}<tr><td>{{ r.site }}</td><td class="value">{{ r.url }}</td></tr>{% endfor %}
</table>
{% endif %}
{% endif %}

{% set vt = results.get('virustotal') %}
{% if vt and not vt.get('error') %}
<h2>{{ t('virustotal.title') }}</h2>
<table>
  {% if vt.malicious is defined %}<tr><td class="label">{{ t('virustotal.malicious') }}</td><td class="value">{{ vt.malicious }}</td></tr>{% endif %}
  {% if vt.suspicious is defined %}<tr><td class="label">{{ t('virustotal.suspicious') }}</td><td class="value">{{ vt.suspicious }}</td></tr>{% endif %}
  {% if vt.harmless is defined %}<tr><td class="label">{{ t('virustotal.harmless') }}</td><td class="value">{{ vt.harmless }}</td></tr>{% endif %}
  {% if vt.reputation is defined %}<tr><td class="label">{{ t('virustotal.reputation') }}</td><td class="value">{{ vt.reputation }}</td></tr>{% endif %}
</table>
{% endif %}

{% set abuse = results.get('abuseipdb') %}
{% if abuse and not abuse.get('error') %}
<h2>{{ t('abuseipdb.title') }}</h2>
<table>
  {% if abuse.abuseConfidenceScore is defined %}<tr><td class="label">{{ t('abuseipdb.confidence') }}</td><td class="value">{{ abuse.abuseConfidenceScore }}</td></tr>{% endif %}
  {% if abuse.totalReports is defined %}<tr><td class="label">{{ t('abuseipdb.totalReports') }}</td><td class="value">{{ abuse.totalReports }}</td></tr>{% endif %}
  {% if abuse.countryCode %}<tr><td class="label">{{ t('abuseipdb.country') }}</td><td class="value">{{ abuse.countryCode }}</td></tr>{% endif %}
  {% if abuse.isp %}<tr><td class="label">{{ t('abuseipdb.isp') }}</td><td class="value">{{ abuse.isp }}</td></tr>{% endif %}
</table>
{% endif %}

{% set shodan = results.get('shodan') %}
{% if shodan and not shodan.get('error') %}
<h2>{{ t('shodan.title') }}</h2>
<table>
  {% if shodan.ip_str %}<tr><td class="label">{{ t('shodan.ip') }}</td><td class="value">{{ shodan.ip_str }}</td></tr>{% endif %}
  {% if shodan.org %}<tr><td class="label">{{ t('shodan.organization') }}</td><td class="value">{{ shodan.org }}</td></tr>{% endif %}
  {% if shodan.os %}<tr><td class="label">{{ t('shodan.os') }}</td><td class="value">{{ shodan.os }}</td></tr>{% endif %}
  {% if shodan.ports %}<tr><td class="label">{{ t('shodan.openPorts') }}</td><td class="value">{{ shodan.ports|join(', ') }}</td></tr>{% endif %}
</table>
{% endif %}

{% set breaches = results.get('breaches') %}
{% if breaches and breaches.get('breaches') %}
<h2>{{ t('breaches.title', n=breaches.breaches|length) }}</h2>
<table><tr><th>{{ t('breaches.source') }}</th><th>{{ t('breaches.date') }}</th></tr>
{% for b in breaches.breaches %}<tr><td>{{ b.Name or b.name or b }}</td><td>{{ b.BreachDate or b.date or '' }}</td></tr>{% endfor %}
</table>
{% endif %}

{% set phone = results.get('phone') %}
{% if phone %}
<h2>{{ t('phone.title') }}</h2>
<table>
  <tr><td class="label">{{ t('phone.valid') }}</td><td class="value">{{ phone.valid }}</td></tr>
  {% if phone.country_name %}<tr><td class="label">{{ t('phone.country') }}</td><td class="value">{{ phone.country_name }}</td></tr>{% endif %}
  {% if phone.carrier %}<tr><td class="label">{{ t('phone.carrier') }}</td><td class="value">{{ phone.carrier }}</td></tr>{% endif %}
  {% if phone.line_type %}<tr><td class="label">{{ t('phone.lineType') }}</td><td class="value">{{ phone.line_type }}</td></tr>{% endif %}
  {% if phone.region %}<tr><td class="label">{{ t('phone.region') }}</td><td class="value">{{ phone.region }}</td></tr>{% endif %}
</table>
{% endif %}

<div class="footer">
  {{ t('report.footer') }} · {{ generated_at }}
</div>
</body>
</html>
"""


def generate_pdf_report(
    target: str,
    scan_type: str,
    results: Dict[str, Any],
    opsec: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    lang: str = "en",
) -> str:
    try:
        from xhtml2pdf import pisa
    except ImportError as e:
        raise ImportError(
            "xhtml2pdf is required for PDF export. Install with: pip install xhtml2pdf"
        ) from e

    _register_pdf_fonts()

    env = Environment(loader=BaseLoader(), autoescape=True)
    env.filters["tojson"] = lambda v: json.dumps(v)
    template = env.from_string(PDF_REPORT_TEMPLATE)

    context = {
        "target": target,
        "scan_type": scan_type,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "results": results,
        "opsec": opsec,
        "opsec_circle_color": _opsec_circle_color(opsec["score"]) if opsec else "#636e72",
        "cat_labels": CAT_LABELS,
        "bar_color": _bar_color,
        "t": make_translator(lang),
        "lang": lang,
    }

    html = template.render(**context)

    if output_path is None:
        results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
        os.makedirs(results_dir, exist_ok=True)
        safe_target = re.sub(r'[^a-zA-Z0-9._\-]', '_', target)[:80]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(results_dir, f"report_{safe_target}_{ts}.pdf")

    with open(output_path, "wb") as out_f:
        result = pisa.CreatePDF(src=html, dest=out_f, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf failed with {result.err} error(s)")

    return output_path
