# PRISM — Open Source Intelligence Platform

> Passive reconnaissance framework with a modern full-stack web interface.  
> Built for security research, OSINT investigations, and infosec portfolio demonstration.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?style=flat-square&logo=typescript&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)

---

## Overview

PRISM aggregates data from 10+ external intelligence sources to build a comprehensive profile of any target — domain, IP address, email, phone number, or social username. All data is presented in a real-time dashboard with relationship graphs, a GeoIP map, exportable HTML reports, and an automated OPSEC exposure score.

**Stack:**
- **Backend** — Python, FastAPI, asyncio, WebSocket, Pydantic
- **Frontend** — Next.js 14 (App Router), React, TypeScript, Tailwind CSS
- **Infrastructure** — Docker, docker-compose, GitHub Actions CI/CD
- **Tests** — pytest, 30+ test cases with monkeypatching

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
| VirusTotal | Domain/IP reputation, malware detections | VirusTotal |
| AbuseIPDB | IP abuse confidence score | AbuseIPDB |
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
| HTML Report | Self-contained PDF-ready scan report | — |
| Groq AI Summary | Natural-language findings summary via LLM | Groq |

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
| `GROQ_API_KEY` | AI summary (llama-3.1-8b) | Free tier |
| `TELEGRAM_BOT_TOKEN` | Telegram user lookup | Free |
| `LEAK_LOOKUP_API_KEY` | Breach database | Limited free |

> Certificate Transparency, Wayback Machine, DNS, WHOIS, Website Analyzer, Email Reputation, SMTP Verify, Blackbird, Maigret, Email Headers, and File Metadata all work **with zero API keys**.

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

## Legal Notice

This tool is intended **exclusively for lawful use**:
- Authorized security assessments and penetration testing
- Research on infrastructure you own or have explicit permission to test
- Academic and educational purposes

Do **not** use PRISM for unauthorized data collection, surveillance, or any activity that violates applicable law. The author assumes no liability for misuse.

---

## License

MIT
