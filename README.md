# PRISM — Open Source Intelligence Platform

> All-in-one passive reconnaissance framework with a real-time web dashboard, AI-powered analysis, and 22+ OSINT modules.  
> Scan any domain, IP, email, phone, or username — get WHOIS, DNS, threat intel, breach data, username search, dark-web mirrors, OPSEC score, entity graphs, and HTML/PDF reports in seconds.

**Live Demo: [getprism.su](https://getprism.su)**  ·  **Docs: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [CONTRIBUTING.md](CONTRIBUTING.md)**

[![CI](https://github.com/NovaCode37/Prism-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/NovaCode37/Prism-platform/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](Dockerfile)
[![GitHub stars](https://img.shields.io/github/stars/NovaCode37/Prism-platform?style=flat-square&logo=github&color=yellow)](https://github.com/NovaCode37/Prism-platform/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/NovaCode37/Prism-platform?style=flat-square&logo=github)](https://github.com/NovaCode37/Prism-platform/network/members)

<p align="center">
  <img src="docs/gifs/main.gif" alt="PRISM Boot Animation" width="720" />
</p>

---

## Why PRISM?

- **22+ modules** — WHOIS, DNS, crt.sh, Wayback Machine, Shodan, VirusTotal, AbuseIPDB, **Censys**, **Dark Web (Ahmia + DarkSearch)**, email reputation, SMTP verify, breach lookup, Blackbird (50+ sites), Maigret (3000+ sites), Telegram, phone HLR, email headers, file metadata, and more
- **AI-powered analysis** — automated executive summary, risk assessment, and interactive Q&A chat via LLM (OpenRouter / Nvidia Nemotron)
- **Real-time dashboard** — WebSocket-driven scan progress with **module-level progress bar (5/8 · 62%)**, interactive entity relationship graph, GeoIP map with coordinates
- **OPSEC Score** — aggregated 0–100 exposure risk score based on all collected data
- **HTML & PDF reports** — export full scan results as a styled, self-contained HTML or print-ready PDF
- **Multi-language UI** — English & Russian out of the box (i18n)
- **Zero mandatory API keys** — 14 out of 22 modules work without any keys at all
- **One-command deploy** — `docker compose up --build` and you're running
- **Fully open source** — MIT license, extensible module architecture, contributor-friendly

---

## Overview

PRISM aggregates data from **20+ external intelligence sources** to build a comprehensive profile of any target — domain, IP address, email, phone number, or social username. All data is presented in a real-time dashboard with relationship graphs, a GeoIP map, exportable HTML reports, and an automated OPSEC exposure score.

**Stack:**
- **Backend** — Python, FastAPI, asyncio, WebSocket, Pydantic, WeasyPrint (PDF)
- **Frontend** — Next.js 14 (App Router), React, TypeScript, Tailwind CSS
- **AI** — OpenRouter API (Nvidia Nemotron) for summary and chat
- **Infrastructure** — Docker, docker-compose, GitHub Actions CI/CD
- **Tests** — pytest, 30+ test cases with monkeypatching

<p align="center">
  <img src="docs/pics/main_showcase/main_showcase.png" alt="PRISM Dashboard" width="720" />
</p>

---

## Features

| Module | Description | API Key |
|--------|-------------|----------|
| WHOIS | Domain registration, registrar, dates | — |
| DNS | A, MX, NS, TXT, CNAME, SOA records | — |
| Certificate Transparency | Subdomain discovery via crt.sh | — |
| Wayback Machine | Historical snapshots, sensitive URL patterns | — |
| GeoIP | IP geolocation, ASN, timezone | ipinfo.io |
| Shodan | Open ports, services, known CVEs | Shodan |
| Censys | Host services, ASN, certificate → subdomain discovery | Censys |
| VirusTotal | Domain/IP reputation, malware detections | VirusTotal |
| AbuseIPDB | IP abuse confidence score | AbuseIPDB |
| Dark Web Checker | .onion mirrors via Ahmia + DarkSearch | — |
| Website Analyzer | Tech stack, emails, social links, metadata | — |
| Email Reputation | DNS-based email rep (MX, SPF, DMARC, disposable check) | — |
| SMTP Verify | Mailbox existence check via SMTP handshake | — |
| Breach Check | Email breach / credential leak lookup | Leak-Lookup |
| Blackbird | Username presence across 50+ platforms (async) | — |
| Maigret | Deep username search across 3000+ sites | — |
| Telegram Lookup | Username/ID lookup via Bot API + scraping | Telegram |
| Phone / HLR | Number validation, carrier, country, reverse lookup | Numverify |
| Email Headers | SPF/DKIM/DMARC analysis, routing hops, spoofing detection | — |
| File Metadata | EXIF, GPS coordinates, PDF/DOCX properties | — |
| OPSEC Score | Aggregated 0–100 exposure risk score | — |
| Entity Graph | Interactive node-relationship visualization | — |
| HTML / PDF Report | Self-contained styled report (HTML + WeasyPrint PDF) | — |
| AI Summary | Natural-language findings summary via LLM | OpenRouter |

---

## Showcase

### Scan in Progress

<p align="center">
  <img src="docs/gifs/scan_showcase.gif" alt="Email Scan Progress" width="720" />
</p>

### Domain Scan

WHOIS registration, DNS records, OPSEC findings, VirusTotal threats, Wayback Machine snapshots, GeoIP map, and entity graph — all in one scan.

<details>
<summary><b>Findings & OPSEC Score</b></summary>
<p align="center"><img src="docs/pics/domain_showcase/findings_showcase.png" alt="Domain Findings" width="720" /></p>
</details>

<details>
<summary><b>WHOIS Registration</b></summary>
<p align="center"><img src="docs/pics/domain_showcase/whois_showcase.png" alt="WHOIS" width="720" /></p>
</details>

<details>
<summary><b>DNS Records</b></summary>
<p align="center"><img src="docs/pics/domain_showcase/dns_showcase.png" alt="DNS" width="720" /></p>
</details>

<details>
<summary><b>Threat Intelligence (VirusTotal)</b></summary>
<p align="center"><img src="docs/pics/domain_showcase/threats_showcase.png" alt="Threats" width="720" /></p>
</details>

<details>
<summary><b>Wayback Machine</b></summary>
<p align="center"><img src="docs/pics/domain_showcase/wayback_showcase.png" alt="Wayback" width="720" /></p>
</details>

<details>
<summary><b>GeoIP Map</b></summary>
<p align="center"><img src="docs/pics/domain_showcase/map_showcase.png" alt="GeoIP Map" width="720" /></p>
</details>

<details>
<summary><b>Entity Graph</b></summary>
<p align="center"><img src="docs/pics/domain_showcase/graph_showcase.png" alt="Entity Graph" width="720" /></p>
</details>

<details>
<summary><b>Raw JSON</b></summary>
<p align="center"><img src="docs/pics/domain_showcase/json_showcase.png" alt="JSON Results" width="720" /></p>
</details>

### IP Scan

VirusTotal + AbuseIPDB threat intel, GeoIP map with coordinates, and entity graph.

<details>
<summary><b>Threat Intelligence (VirusTotal + AbuseIPDB)</b></summary>
<p align="center"><img src="docs/pics/ip_showcase/threats_showcase.png" alt="IP Threats" width="720" /></p>
</details>

<details>
<summary><b>GeoIP Map</b></summary>
<p align="center"><img src="docs/pics/ip_showcase/map_showcase.png" alt="IP Map" width="720" /></p>
</details>

### Email Scan

DNS-based reputation (MX, SPF, DMARC), SMTP mailbox verification, and breach check.

<details>
<summary><b>Email Reputation + SMTP Verification</b></summary>
<p align="center"><img src="docs/pics/email_showcase/email_showcase.png" alt="Email Rep" width="720" /></p>
</details>

<details>
<summary><b>Findings</b></summary>
<p align="center"><img src="docs/pics/email_showcase/findings_showcase.png" alt="Email Findings" width="720" /></p>
</details>

### Phone Scan

Number validation, carrier detection, country/region, timezone, and reverse lookup.

<details>
<summary><b>Phone Intelligence</b></summary>
<p align="center"><img src="docs/pics/phone_showcase/phone_showcase.png" alt="Phone Intel" width="720" /></p>
</details>

<details>
<summary><b>GeoIP Map</b></summary>
<p align="center"><img src="docs/pics/phone_showcase/map_showcase.png" alt="Phone Map" width="720" /></p>
</details>

### Username Scan

Blackbird async search across 50+ platforms with response times.

<details>
<summary><b>Accounts Found</b></summary>
<p align="center"><img src="docs/pics/username_showcase/acc_showcase.png" alt="Accounts" width="720" /></p>
</details>

<details>
<summary><b>Entity Graph</b></summary>
<p align="center"><img src="docs/pics/username_showcase/graph_showcase.png" alt="Username Graph" width="720" /></p>
</details>

### AI Analysis (OpenRouter)

LLM-powered OSINT summary with risk assessment and recommended next investigation steps. Interactive chat for follow-up questions.

<details>
<summary><b>AI Summary</b></summary>
<p align="center"><img src="docs/pics/username_showcase/ai_summ_showcase.png" alt="AI Summary" width="720" /></p>
</details>

<details>
<summary><b>Ask the AI</b></summary>
<p align="center"><img src="docs/pics/username_showcase/askai_showcase.png" alt="AI Chat" width="720" /></p>
</details>

### Standalone Tools

File Metadata (EXIF/GPS), Email Header Analyzer, Crypto Address Lookup, and QR Code Decoder.

<details>
<summary><b>File Metadata & GEOINT</b></summary>
<p align="center"><img src="docs/pics/main_showcase/filemetadata_showcase.png" alt="File Metadata" width="720" /></p>
</details>

<details>
<summary><b>Email Header Analyzer</b></summary>
<p align="center"><img src="docs/pics/main_showcase/headers_showcase.png" alt="Email Headers" width="720" /></p>
</details>

<details>
<summary><b>Crypto Address Lookup</b></summary>
<p align="center"><img src="docs/pics/main_showcase/crypto_showcase.png" alt="Crypto Lookup" width="720" /></p>
</details>

<details>
<summary><b>QR Code Decoder</b></summary>
<p align="center"><img src="docs/pics/main_showcase/qrcode_showcase.png" alt="QR Decoder" width="720" /></p>
</details>

---

## Quick Start

### Docker (recommended)

```bash
cp .env.example .env        # add your API keys
docker compose up --build
```

Open **http://localhost:3000** (frontend) and **http://localhost:8080** (API).

### Manual

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

---

## API Keys

Copy `.env.example` → `.env`. All keys are optional — modules gracefully skip if a key is missing.

| Variable | Service | Free Tier |
|----------|---------|-----------|
| `NUMVERIFY_API_KEY` | Phone validation & carrier | 100 req/mo |
| `IPINFO_API_KEY` | GeoIP location | 50k req/mo |
| `VIRUSTOTAL_API_KEY` | Threat intelligence | 500 req/day |
| `ABUSEIPDB_API_KEY` | IP abuse score | 1000 req/day |
| `SHODAN_API_KEY` | Port scan + CVE lookup | Free tier |
| `OPENROUTER_API_KEY` | AI summary (Nvidia Nemotron) | Free tier |
| `TELEGRAM_BOT_TOKEN` | Telegram user lookup | Free |
| `LEAK_LOOKUP_API_KEY` | Breach database | Limited free |
| `CENSYS_API_ID` + `CENSYS_API_SECRET` | Host & certificate search | 250 req/mo |

> Certificate Transparency, Wayback Machine, DNS, WHOIS, Website Analyzer, Email Reputation, SMTP Verify, Blackbird, Maigret, Email Headers, File Metadata, and **Dark Web Checker** all work **with zero API keys**.

---

## Project Structure

```
prism/
├── config.py                     # Environment + API key loader
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── modules/
│   ├── extra_tools.py            # WHOIS, GeoIP, DNS, Website Analyzer
│   ├── cert_transparency.py      # Subdomain discovery via crt.sh
│   ├── threat_intel.py           # VirusTotal + AbuseIPDB
│   ├── shodan_lookup.py          # Shodan host intelligence
│   ├── wayback.py                # Wayback Machine snapshots
│   ├── blackbird.py              # Username search (async, 50+ platforms)
│   ├── maigret_wrapper.py        # Deep username search (3000+ sites)
│   ├── hlr_lookup.py             # Phone validation + reverse lookup
│   ├── hunter.py                 # DNS-based email reputation check
│   ├── telegram_lookup.py        # Telegram username/ID lookup
│   ├── email_header_analyzer.py  # SPF/DKIM/DMARC + hop analysis
│   ├── metadata_extractor.py     # EXIF/PDF/DOCX + GPS extraction
│   ├── opsec_score.py            # Exposure risk scoring (0–100)
│   ├── report_generator.py       # Jinja2 HTML report
│   └── graph_builder.py          # Entity relationship graph data
│
├── web/
│   └── app.py                    # FastAPI + WebSocket scan engine
│
├── frontend/                     # Next.js 14 + TypeScript + Tailwind
│   └── src/
│       ├── app/                  # App Router pages
│       ├── components/           # UI components (Topbar, Sidebar, views)
│       └── lib/                  # API client, types
│
└── tests/
    └── test_modules.py           # pytest suite, 30+ tests
```

---

## Running Tests

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=modules --cov-report=term-missing
```

---

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`):

1. **Lint** — flake8
2. **Test** — pytest with coverage
3. **Build** — Docker image

---

## Roadmap

### v2.1 (current)
- [x] Module-level scan progress bar with completion %
- [x] PDF report export (WeasyPrint)
- [x] Censys integration (host + certificate search)
- [x] Dark-web `.onion` mirror checker (Ahmia + DarkSearch)
- [x] i18n — English & Russian UI
- [x] One-click copy buttons across results
- [x] Mobile-responsive layout

### v2.2 (planned)
- [ ] Scheduled scans with diff alerting
- [ ] Webhook / Slack / Discord notifications
- [ ] Scan history & comparison view
- [ ] More languages (DE, FR, ES, ZH)
- [ ] Browser extension for one-click scans
- [ ] Public REST API with token-based auth

> Want to contribute? Pick an open issue tagged `good first issue` or open a new one.

---

## Star History

<a href="https://www.star-history.com/#NovaCode37/Prism-platform&Date">
  <img src="https://api.star-history.com/svg?repos=NovaCode37/Prism-platform&type=Date" alt="Star History Chart" width="640" />
</a>

---

## Legal Notice

This tool is intended **exclusively for lawful use**:
- Authorized security assessments and penetration testing
- Research on infrastructure you own or have explicit permission to test
- Academic and educational purposes

Do **not** use PRISM for unauthorized data collection, surveillance, or any activity that violates applicable law. The author assumes no liability for misuse.

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

---

## License

MIT
