<div align="center">

# PRISM

**Self-hosted OSINT platform with 26 modules, OPSEC scoring, AI summary, and a real-time web dashboard.**

Scan a domain, IP, email, phone or username and get WHOIS, DNS, threat intel, breach data, username search, dark-web mirrors, OPSEC score, entity graphs, and HTML/PDF reports in seconds.

**[Live Demo](https://getprism.su)** · **[Docker Quick Start](#docker-recommended)** · **[Configuration](docs/CONFIGURATION.md)** · **[Architecture](docs/ARCHITECTURE.md)** · **[Security](SECURITY.md)** · **[Changelog](CHANGELOG.md)** · **[FAQ](#faq)**

[![CI](https://github.com/NovaCode37/Prism-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/NovaCode37/Prism-platform/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-2.10.0-7c5cfc?style=flat-square)](CHANGELOG.md)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-getprism.su-7c5cfc?style=flat-square&logo=firefox)](https://getprism.su)
[![Firefox Add-on](https://img.shields.io/amo/v/prism-osint?style=flat-square&logo=firefoxbrowser&logoColor=white&label=Firefox%20Add-on&color=ff7139)](https://addons.mozilla.org/en-US/firefox/addon/prism-osint/)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

</div>

> **AI analysis on the [live demo](https://getprism.su) can be slow.** The demo server sits in a region every hosted LLM provider blocks, so its AI calls are routed out through a proxy before they reach a model. It works, it is just slower than a normal instance, so give the summary a minute. A self-hosted instance with your own provider responds at full speed. See [the FAQ](#faq).

> **Also from me:** [Claude Security Skills](https://github.com/NovaCode37/claude-security-skills), eight security skills for Claude Code. Secret scanning, Python SAST, prompt-injection testing, and HTTP, JWT, Dockerfile, CORS and dependency audits. Standard library only, nothing to install.


<div align="center">

### Table of Contents

[Why PRISM?](#why-prism) • [Overview](#overview) • [How it compares](#how-it-compares) • [Use cases](#use-cases) • [Features](#features) • [Showcase](#showcase) • [Quick Start](#quick-start) • [Configuration](#configuration) • [API](#api) • [Project Structure](#project-structure) • [Running Tests](#running-tests) • [CI/CD](#cicd) • [Roadmap](#roadmap) • [Star History](#star-history) • [Legal Notice](#legal-notice) • [Support the project](#support-the-project) • [Contributing](#contributing) • [Credits](#credits) • [License](#license)

</div>

<p align="center">
  <img src="docs/gifs/main.gif" alt="PRISM Boot Animation" width="720" />
</p>

---

## Why PRISM?

- **26 modules**: WHOIS, DNS, crt.sh, Wayback Machine, Shodan, VirusTotal, AbuseIPDB, Censys, dark-web mirrors, email reputation, SMTP verify, breach lookup, Blackbird (50+ sites), Maigret (3000+ sites), Telegram, phone HLR, email headers, file metadata, and more
- **AI summary**: written summary of the findings, plus a chat you can ask follow-up questions in. Needs an LLM provider of your own.
- **Real-time dashboard**: WebSocket-driven scan progress with per-module progress, an entity graph and a GeoIP map
- **OPSEC Score**: aggregated 0-100 exposure risk score across data exposure, identity, infrastructure and web security
- **HTML, PDF, CSV & Markdown reports**: export full scan results as HTML, PDF, CSV, or Markdown (locale-aware EN/RU/DE)
- **Multi-language UI**: English, Russian, German, French, Spanish, Italian, Polish, Portuguese, and Chinese out of the box (i18n + auto-detect)
- **Standalone CLI**: run scans headlessly via `python cli.py scan example.com --json`, and manage scheduled re-scans with `python cli.py watchlist add example.com --interval 6`
- **Scan history & comparison**: browse past scans, load results, compare two scans side-by-side
- **Webhook callbacks**: get notified on scan completion with HMAC-signed payloads (SSRF-protected), Slack/Discord formatters
- **Hardened auth**: header-only API keys (`X-API-Key` / `Bearer`), no query-string secrets, strict CORS, per-principal scan isolation
- **Zero mandatory API keys**: 16 out of 26 modules work without any keys at all
- **One-command deploy**: `docker run ghcr.io/novacode37/prism-platform` with nothing to build (amd64 and arm64)
- **MIT licensed**, and adding a module means one file in `modules/`

---

## Overview

PRISM queries 20-odd external sources and puts what comes back in one place. Targets can be a domain, an IP, an email, a phone number or a username. Results land in a dashboard as they arrive, with a relationship graph, a GeoIP map, an exposure score and HTML or PDF export.

**Stack:**
- **Backend**: Python 3.10+, FastAPI, asyncio, WebSocket, Pydantic, slowapi (rate limiting), xhtml2pdf (PDF)
- **Frontend**: Next.js 15 (App Router), React, TypeScript, Tailwind CSS, Leaflet (maps)
- **AI**: OpenRouter (Nvidia Nemotron) or Groq (Llama-3) for summary and chat
- **Infrastructure**: Docker, docker-compose, GitHub Actions CI/CD
- **Tests**: pytest, 435 cases, network mocked

<p align="center">
  <img src="docs/pics/main_showcase/main_showcase.png" alt="PRISM Dashboard" width="720" />
</p>

### Architecture (high level)

```mermaid
flowchart LR
    U[User / Browser] -->|HTTPS + X-API-Key| FE[Next.js 15 Dashboard]
    FE -->|REST + WebSocket| API[FastAPI Backend]
    API --> SCH[Scan Orchestrator<br/>asyncio + queues]
    SCH --> MOD[26 OSINT Modules]
    MOD --> EXT[(External APIs<br/>Shodan / VT / Censys<br/>crt.sh / Wayback / etc.)]
    SCH --> CACHE[(Module Cache<br/>TTL JSON)]
    SCH --> STORE[(Scan Storage<br/>per-principal)]
    SCH --> WH[Webhook Dispatcher<br/>HMAC + SSRF guard]
    API --> AI[AI Summary / Chat<br/>OpenRouter / Groq]
    API --> RPT[Report Generator<br/>HTML + xhtml2pdf]
```

---

## How it compares

SpiderFoot, theHarvester, Recon-ng and Maltego all cover ground PRISM does, and several of them cover it better. theHarvester and Recon-ng are CLI tools and comfortable to script around. SpiderFoot has far more modules. Maltego's graph work is a different league.

What PRISM does that those generally do not: results stream into a browser while the scan runs, everything is one container with no keys required to get started, and the scan ends with a report you can hand to someone who is not an analyst. If you want depth and already live in a terminal, SpiderFoot or Recon-ng is probably the better tool. If you want to point something at a domain and read the answer, this is built for that.

---

## Use cases

- **Bug bounty recon**: kick off a single scan and get subdomains (crt.sh + Censys), open ports (Shodan), wayback sensitive paths, and AI-prioritized findings.
- **Phishing investigation**: pivot from a suspicious domain or email to threat intel, breach exposure, mail auth (SPF/DKIM/DMARC), and historical snapshots.
- **Brand & impersonation monitoring**: webhook-driven scans to detect new lookalike subdomains, dark-web mentions, and exposed credentials.
- **Security awareness training**: give employees their own OPSEC score across email, phone, and username so they see exposure on a 0-100 scale.
- **Academic / educational OSINT**: a self-hosted, MIT-licensed reference for teaching passive reconnaissance, geolocation, and threat intel pipelines.

---

## Features

| Module | Description | API Key |
|--------|-------------|----------|
| WHOIS | Domain registration, registrar, dates | none |
| DNS | A, MX, NS, TXT, CNAME, SOA records | none |
| Certificate Transparency | Subdomain discovery via crt.sh | none |
| Wayback Machine | Historical snapshots, sensitive URL patterns | none |
| GeoIP | IP geolocation, ASN, timezone | ipinfo.io |
| Shodan | Open ports, services, known CVEs; falls back to the keyless InternetDB dataset | Shodan (optional) |
| Censys | Host services, ASN, certificate → subdomain discovery | Censys |
| VirusTotal | Domain/IP reputation, malware detections | VirusTotal |
| AbuseIPDB | IP abuse confidence score | AbuseIPDB |
| Dark Web Checker | .onion mirrors via Ahmia + DarkSearch | none |
| Infostealer Exposure | Machines infected by stealers carrying the target's credentials (opt-in) | Hudson Rock |
| Domain Exposure | Yearly exposure trend, malware families, affected services (opt-in) | Lunar |
| Website Analyzer | Tech stack, emails, social links, metadata | none |
| Email Reputation | DNS-based email rep (MX, SPF, DMARC, disposable check) | none |
| SMTP Verify | Mailbox existence check via SMTP handshake | none |
| Breach Check | Email breach / credential leak lookup | Leak-Lookup |
| Blackbird | Username presence across 50+ platforms (async) | none |
| Maigret | Deep username search across 3000+ sites (not bundled in the Docker image) | none |
| Telegram Lookup | Username/ID lookup via Bot API + scraping | Telegram |
| Phone / HLR | Number validation, carrier, country, reverse lookup | Numverify |
| Email Headers | SPF/DKIM/DMARC analysis, routing hops, spoofing detection | none |
| File Metadata | EXIF, GPS coordinates, PDF/DOCX properties | none |
| OPSEC Score | Aggregated 0-100 exposure risk score | none |
| Entity Graph | Interactive node-relationship visualization | none |
| HTML / PDF Report | Self-contained styled report (HTML + xhtml2pdf), localized EN/RU/DE | none |
| AI Summary | Natural-language findings summary via LLM | OpenRouter / Groq |
| Webhook Callbacks | HMAC-signed POST on scan completion (SSRF-guarded) | none |

Infostealer Exposure and Domain Exposure are off unless you set `HUDSONROCK_ENABLED` or `LUNAR_ENABLED`. Both query a third party, so a default install sends them nothing. Lunar builds its report on the first request and caches it for a month, so a domain nobody has looked up yet comes back as skipped with `GENERATING_REPORT`. Scan it again once the report is ready.

---

## Showcase

<p align="center">
  <img src="docs/gifs/scan_showcase.gif" alt="Scan Progress" width="720" />
</p>

<p align="center">
  <img src="docs/pics/domain_showcase/findings_showcase.png" alt="Findings + OPSEC Score" width="720" />
</p>

<p align="center">
  <img src="docs/pics/username_showcase/ai_summ_showcase.png" alt="AI Summary" width="720" />
</p>

<h3 align="center">Browser Extension</h3>

<p align="center">Right-click any domain, email, username or IP and the full scan runs inside the popup. No tab switching, no copy-paste.</p>

<p align="center">
  <a href="https://addons.mozilla.org/en-US/firefox/addon/prism-osint/"><img src="https://img.shields.io/badge/Get%20it%20on-Firefox%20Add--ons-ff7139?style=for-the-badge&logo=firefoxbrowser&logoColor=white" alt="Get PRISM on Firefox Add-ons" /></a>
</p>

<p align="center">
  <img src="docs/extension-demo.gif" alt="PRISM browser extension demo" width="300" />
</p>

<details>
<summary><b>More screenshots (domain / IP / email / phone / username / standalone tools)</b></summary>

### Domain Scan
WHOIS, DNS, threats, Wayback, GeoIP map, entity graph.

<p align="center"><img src="docs/pics/domain_showcase/whois_showcase.png" alt="WHOIS" width="720" /></p>
<p align="center"><img src="docs/pics/domain_showcase/dns_showcase.png" alt="DNS" width="720" /></p>
<p align="center"><img src="docs/pics/domain_showcase/threats_showcase.png" alt="Threats" width="720" /></p>
<p align="center"><img src="docs/pics/domain_showcase/wayback_showcase.png" alt="Wayback" width="720" /></p>
<p align="center"><img src="docs/pics/domain_showcase/map_showcase.png" alt="GeoIP Map" width="720" /></p>
<p align="center"><img src="docs/pics/domain_showcase/graph_showcase.png" alt="Entity Graph" width="720" /></p>
<p align="center"><img src="docs/pics/domain_showcase/json_showcase.png" alt="Raw JSON" width="720" /></p>

### IP Scan
VirusTotal + AbuseIPDB threat intel, GeoIP map, entity graph.

<p align="center"><img src="docs/pics/ip_showcase/threats_showcase.png" alt="IP Threats" width="720" /></p>
<p align="center"><img src="docs/pics/ip_showcase/map_showcase.png" alt="IP Map" width="720" /></p>

### Email Scan
DNS-based reputation, SMTP mailbox verification, breach check.

<p align="center"><img src="docs/pics/email_showcase/email_showcase.png" alt="Email Rep" width="720" /></p>
<p align="center"><img src="docs/pics/email_showcase/findings_showcase.png" alt="Email Findings" width="720" /></p>

### Phone Scan
Number validation, carrier detection, country/region, timezone, reverse lookup.

<p align="center"><img src="docs/pics/phone_showcase/phone_showcase.png" alt="Phone Intel" width="720" /></p>
<p align="center"><img src="docs/pics/phone_showcase/map_showcase.png" alt="Phone Map" width="720" /></p>

### Username Scan
Blackbird async search across 50+ platforms.

<p align="center"><img src="docs/pics/username_showcase/acc_showcase.png" alt="Accounts" width="720" /></p>
<p align="center"><img src="docs/pics/username_showcase/graph_showcase.png" alt="Username Graph" width="720" /></p>

### AI Analysis
LLM-powered OSINT summary + interactive chat.

<p align="center"><img src="docs/pics/username_showcase/askai_showcase.png" alt="AI Chat" width="720" /></p>

### Standalone Tools
File Metadata (EXIF/GPS), Email Header Analyzer, Crypto Address Lookup, QR Code Decoder.

<p align="center"><img src="docs/pics/main_showcase/filemetadata_showcase.png" alt="File Metadata" width="720" /></p>
<p align="center"><img src="docs/pics/main_showcase/headers_showcase.png" alt="Email Headers" width="720" /></p>
<p align="center"><img src="docs/pics/main_showcase/crypto_showcase.png" alt="Crypto Lookup" width="720" /></p>
<p align="center"><img src="docs/pics/main_showcase/qrcode_showcase.png" alt="QR Decoder" width="720" /></p>

</details>

---

## Quick Start

### Try in 60 seconds (no setup, no API keys)

A self-contained demo preloaded with example scans. No API keys, no external lookups:

```bash
git clone https://github.com/NovaCode37/Prism-platform.git
cd Prism-platform
docker compose -f docker-compose.demo.yml up --build
```

Open **http://localhost:8080**. The Next.js UI and FastAPI backend are served by the same container. Three sample scans (a domain, an IP, and a username) are already under **Recent Scans**, showing the dashboard, OPSEC score, entity graph, map, and HTML/PDF report.

> The demo runs anonymously (`ALLOW_ANON_API=true`) on `:8080`. For authenticated production-style setup, use the Docker / Manual setups below.

### Docker (recommended)

Nothing to clone and nothing to build:

```bash
docker run -p 8080:8080 -e ALLOW_ANON_API=true ghcr.io/novacode37/prism-platform:latest
```

Images are published for `linux/amd64` and `linux/arm64`, so this works on a Raspberry Pi or an ARM VPS as well. Tags follow releases: `latest`, `2.10`, `2.10.0`, plus `edge` built from `main`.

If you need somewhere to put it, [Timeweb Cloud](https://timeweb.cloud/?i=146939) rents plain Linux servers by the month. That is a referral link: same price to you, and it pays for this project's domain.

To configure it, pass an env file instead:

```bash
curl -O https://raw.githubusercontent.com/NovaCode37/Prism-platform/main/.env.example
docker run -p 8080:8080 --env-file .env.example ghcr.io/novacode37/prism-platform:latest
```

Building it yourself works too, and is what you want if you are changing the code:

```bash
git clone https://github.com/NovaCode37/Prism-platform.git
cd Prism-platform
cp .env.example .env        # local/demo defaults to anonymous access; edit for production keys
docker compose up --build
```

Open **http://localhost:8080**. Docker builds the Next.js static export and serves it from FastAPI together with `/api/*`, `/ws/*`, and `/healthz`.

The container runs as uid 1000, not root. If you mount `./results` from a directory owned by someone else, reports will fail to write. `chown -R 1000:1000 results` on the host fixes it.

The example `.env` is intentionally easy to run: `ALLOW_ANON_API=true` and no API key is required. Before exposing PRISM beyond your machine, switch to API-key mode as shown in [API keys and anonymous mode](docs/CONFIGURATION.md#api-keys-and-anonymous-mode).

### Manual

```bash
# 1. Backend
git clone https://github.com/NovaCode37/Prism-platform.git
cd Prism-platform
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080 --reload --no-proxy-headers

# 2. Frontend (in a separate terminal, from repo root)
cd frontend
npm install
# create .env.local for the separate dev server:
#   NEXT_PUBLIC_API_URL=http://localhost:8080
#   NEXT_PUBLIC_BASE_PATH=
#   NEXT_PUBLIC_API_KEY=<only when ALLOW_ANON_API=false>
npm run dev
```

Open **http://localhost:3000**.

When you run only `uvicorn` from source, FastAPI serves `/api/*`, `/ws/*`, and `/healthz`. The root page `/` needs a built Next.js export in `frontend/out`; on a fresh checkout without that build it returns `{"detail":"Frontend build not found"}`. Use `npm run dev` as shown above, or run `npm run build` before serving the single-container style UI from FastAPI.

> For local experimentation, `.env.example` uses `ALLOW_ANON_API=true`. For any shared or public deployment, set `ALLOW_ANON_API=false`, configure `API_KEYS`, and give the UI one accepted key.

---

## Configuration

PRISM starts with no configuration: the Docker command above works as it is.
Every external provider key is optional, and a module without its key reports
itself as skipped rather than failing the scan.

The handful most people touch:

| Variable | What it does |
|----------|--------------|
| `ALLOW_ANON_API` | `true` lets anyone who can reach the server run scans. Right for a laptop, wrong for anything internet-facing |
| `API_KEYS` | Comma-separated accepted keys, each with its own isolated scan history |
| `TRUST_PROXY_HEADERS` + `FORWARDED_ALLOW_IPS` | Needed behind nginx or Caddy, so rate limiting sees the real client address |
| `PRISM_BASE_PATH` | Serve PRISM under a subpath such as `/prism` |
| `MODULE_PROXY` / `LLM_PROXY` | Route module and AI traffic through a proxy ([guide](docs/proxies.md)) |
| `OPENROUTER_API_KEY` / `GROQ_API_KEY` | Turn on the AI summary and chat |

Every variable, both auth modes in full, the nginx and Caddy examples, subpath
deployments and the provider keys with their free tiers are in
**[docs/CONFIGURATION.md](docs/CONFIGURATION.md)**.

---

## API

The backend exposes a REST + WebSocket API. Application requests require an `X-API-Key` or `Authorization: Bearer` header in API-key mode; in anonymous mode (`ALLOW_ANON_API=true`) the header can be omitted. `/healthz` stays unauthenticated. Interactive docs are served at **`/docs`** (Swagger) and **`/redoc`** when running locally (unless `DISABLE_DOCS=true`).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/scan` | Start a scan (`{ target, scan_type, modules }`) → returns `scan_id` |
| `GET`  | `/api/scan/{id}` | Scan status and results |
| `GET`  | `/api/scan/{id}/graph` | Entity relationship graph |
| `GET`  | `/api/scan/{id}/map` | GeoIP map markers |
| `GET`  | `/api/scan/{id}/report` | HTML report |
| `GET`  | `/api/scan/{id}/report/pdf` | PDF report |
| `GET`  | `/api/scans` | List past scans (per-principal) |
| `GET`  | `/healthz` | Unauthenticated health check |
| `GET`  | `/api/health` | Unauthenticated health check for uptime monitors and load balancers |
| `WS`   | `/ws/{scan_id}` | Live scan progress stream |
| `POST` | `/api/ai/summary`, `/api/ai/chat` | AI summary and Q&A |
| `POST` | `/api/url-scan`, `/api/mac-lookup`, `/api/crypto`, `/api/darkweb`, `/api/qr-decode`, `/api/email-headers`, `/api/metadata` | Standalone tools |

Authenticated example:

```bash
curl -X POST http://localhost:8080/api/scan \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"target":"example.com","scan_type":"domain"}'
```

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
│   ├── censys_lookup.py          # Censys host + certificate search
│   ├── wayback.py                # Wayback Machine snapshots + sensitive URLs
│   ├── onion_checker.py          # .onion mirror checker (Ahmia + DarkSearch)
│   ├── darkweb_search.py         # Dark-web mentions search
│   ├── blackbird.py              # Username search (async, 50+ platforms)
│   ├── maigret_wrapper.py        # Deep username search (3000+ sites)
│   ├── hlr_lookup.py             # Phone validation + reverse lookup
│   ├── hunter.py                 # DNS-based email reputation check
│   ├── smtp_verify.py            # SMTP mailbox existence verification
│   ├── leak_lookup.py            # Email breach / credential leak lookup
│   ├── telegram_lookup.py        # Telegram username/ID lookup
│   ├── email_header_analyzer.py  # SPF/DKIM/DMARC + hop analysis
│   ├── metadata_extractor.py     # EXIF/PDF/DOCX + GPS extraction
│   ├── crypto_lookup.py          # Crypto address heuristics
│   ├── qr_decoder.py             # QR image decoder
│   ├── url_scanner.py            # Standalone URL scanner
│   ├── opsec_score.py            # Exposure risk scoring (0-100)
│   ├── graph_builder.py          # Entity relationship graph data
│   ├── report_generator.py       # Jinja2 HTML report + xhtml2pdf PDF
│   └── report_i18n.py            # Report translations EN / RU / DE
│
├── web/
│   ├── app.py                    # FastAPI + WebSocket scan engine
│   └── security.py               # Auth, CORS, rate limiting, SSRF guard
│
├── frontend/                     # Next.js 15 + TypeScript + Tailwind
│   └── src/
│       ├── app/                  # App Router pages
│       ├── components/           # UI (Topbar, Sidebar, Map, Graph, ...)
│       └── lib/                  # API client, i18n, types
│
└── tests/                        # 435 pytest tests
    ├── test_modules.py
    ├── test_modules_extended.py
    ├── test_v2_1_modules.py
    └── test_webhook.py
```

---

## Running Tests

```bash
pip install pytest pytest-cov pytest-asyncio
pytest -q
# or with coverage:
pytest tests/ -v --cov=modules --cov=web --cov-report=term-missing
```

Frontend type check:

```bash
cd frontend
npx tsc --noEmit -p tsconfig.json
```

---

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`):

1. **Lint**: flake8
2. **Test**: pytest with coverage
3. **Build**: Docker image

---

## Roadmap

Everything through **2.10** has shipped. The full history, release by
release, is in the [changelog](CHANGELOG.md).

### v2.11 (planned)
- [ ] Username checks for the sites that serve identical HTML for every name: needs their APIs rather than page scraping
- [ ] *(exploring)* AI OSINT agent: autonomous multi-module investigation

> Want to contribute? Pick an open issue tagged `good first issue` or open a new one.

---

## Star History

<a href="https://www.star-history.com/?repos=NovaCode37%2FPrism-platform&type=date&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=NovaCode37/Prism-platform&type=date&theme=dark&legend=top-left&sealed_token=ZT8utF1aZvTNTDg4nFoykutgOxGg7hvj1balAUwq_EaVotNV9xbPYgRuSOzZB_QosPI1W5B0Pzes_RyKlmPH59yZeMDYwZtwDfWXCbZ7mNRxesGKrka6SQ" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=NovaCode37/Prism-platform&type=date&legend=top-left&sealed_token=ZT8utF1aZvTNTDg4nFoykutgOxGg7hvj1balAUwq_EaVotNV9xbPYgRuSOzZB_QosPI1W5B0Pzes_RyKlmPH59yZeMDYwZtwDfWXCbZ7mNRxesGKrka6SQ" />
    <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=NovaCode37/Prism-platform&type=date&legend=top-left&sealed_token=ZT8utF1aZvTNTDg4nFoykutgOxGg7hvj1balAUwq_EaVotNV9xbPYgRuSOzZB_QosPI1W5B0Pzes_RyKlmPH59yZeMDYwZtwDfWXCbZ7mNRxesGKrka6SQ" width="640" />
  </picture>
</a>

---

## Legal Notice

This tool is intended **exclusively for lawful, authorized use**:
- Security assessments and penetration testing you are authorized to perform
- Research on infrastructure, accounts, or data you own or have explicit permission to investigate
- Auditing your own digital footprint
- Academic and educational purposes

Every scan PRISM performs is passive and queries only publicly available data, but aggregating public data can still cause real harm. Do **not** use PRISM to:
- Stalk, harass, dox, or surveil any person without their consent
- Profile or track individuals you have no authorization to investigate
- Collect data in violation of applicable law or the terms of service of the platforms involved

You are responsible for how you use the results. The author assumes no liability for misuse.

---

## Support the project

If PRISM is useful to you, a ⭐ is the best free way to help. If you'd like to support development financially:

- **[DonationAlerts](https://dalink.to/novastro)**
- **[DonatePay](https://donatepay.ru/don/1532982)** (card, RU wallets, and more)
- **[SberTips](https://pay.mysbertips.ru/80561611)** (RUB)
- **Crypto:**

```
USDT (TRC20): TEdN41cTdAyNm7vrP4NYceT9sVhTB9BHho
TON:          UQAkpcYb0hKgqEwGLs08syU_4Nh-_MhwaJT3HPWqFSidLThV
BTC:          bc1qm8zvvh2ehv3m2su6u0exmcr903cf07gn0r66y6
ETH:          0x0639476A71255FD2C15dceD53e167952DcddEE8A
```

<table>
  <tr>
    <td align="center"><img src="docs/donate/usdt-trc20.png" width="120"><br><sub>USDT (TRC20)</sub></td>
    <td align="center"><img src="docs/donate/ton.png" width="120"><br><sub>TON</sub></td>
    <td align="center"><img src="docs/donate/btc.png" width="120"><br><sub>BTC</sub></td>
    <td align="center"><img src="docs/donate/eth.png" width="120"><br><sub>ETH</sub></td>
  </tr>
</table>

### Costs you nothing

These are referral links. Sign up through one and I get a cut, you pay the same as you would anyway.

- **[StealthSurf VPN](https://t.me/stealthsurf_vpn_bot?start=cea5c4bf513a)** ([web](https://i.stealthsurf.net/cea5c4bf513a)), if you want one for OSINT work
- **[Telegram Wallet](https://telegram.me/wallet/start?startapp=ref-3-MmWAj_vksZ0)**, for the crypto above without an exchange account
- **[YepShop](https://t.me/YepShopBot?start=ref_50D50292)**, VPN and proxy subscriptions, handy if you want a proxy for `MODULE_PROXY`

**Want the browser extension in your store?** The [PRISM extension](extension/) is [live on Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/prism-osint/). Publishing it to the Chrome Web Store, Yandex, or other markets costs a registration fee per store. If you want it listed in a specific one, a donation covers that and funds further development. Reach out and I'll ship it.

---

## FAQ

**Do I need API keys?**
No. 16 of 26 modules work without any keys.

**Is it free?**
Yes, MIT licensed and completely self-hosted.

**Can I run it without installing anything?**
Try the live demo, or spin it up with the one-command Docker demo.

**Which LLM does the AI summary use?**
Any OpenAI-compatible endpoint. OpenRouter, Groq, GigaChat and a local Ollama all work. Set `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `.env` to point at your own provider, plus `LLM_PROXY` if the request needs to go through a proxy. Every key you configure becomes a provider, and they are tried in order until one answers, so a blocked or rate-limited provider falls through to the next.

**How do I run the AI locally, with nothing leaving the machine?**
The compose file ships an Ollama service behind a profile, so it stays out of the way unless you ask for it:

```bash
docker compose --profile ollama up -d
docker compose exec ollama ollama pull qwen2.5:3b
```

Then point PRISM at it in `.env`. The container reaches Ollama by service name, and no key is needed:

```ini
LLM_BASE_URL=http://ollama:11434/v1/chat/completions
LLM_MODEL=qwen2.5:3b
```

Budget roughly 4 GB of RAM for a 3B model and 8 GB for a 7B one; answers are slower than a hosted provider, and nothing is sent off the machine.

**Why do some modules fail on the public demo?**
The demo is a shared-hosting instance with anonymous access and a daily scan quota, so it hits limits the average self-hosted install never will. Several modules also depend on third-party services that break on their own schedule. crt.sh regularly answers `502`, and the Wayback CDX API answers `503` under load. PRISM reports those upstream failures verbatim instead of hiding them.

**Why is AI analysis slow on the demo?**
Hosted LLM providers block the demo's hosting region at their edge, so a direct call never reaches a model. The demo works around it by routing the AI calls out through a proxy in an allowed region. That extra hop costs time, so a summary can take up to a minute or two. It is not broken, just slow, and if a request times out, generating it again usually works. PRISM tries every provider you configure and reports what each one said.

On your own instance there is no proxy hop and it responds at full speed. Point it at any OpenAI-compatible endpoint:

```ini
LLM_BASE_URL=https://your-provider/v1/chat/completions
LLM_API_KEY=...
LLM_MODEL=...
```

Or run the model yourself with nothing leaving the machine, see the Ollama answer above. Configure more than one provider and PRISM falls through to the next when one refuses.

---


## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request!
For security issues, see [SECURITY.md](SECURITY.md).

---

## Also from this project

[claude-security-skills](https://github.com/NovaCode37/claude-security-skills): eight security skills for Claude Code: secret scanning, Python SAST, prompt-injection testing, and HTTP, JWT, Dockerfile, CORS and dependency auditing. Standard library only, installable as a plugin.

---

## Development note

PRISM is built by one person, with AI assistance as part of the workflow. Everything gets reviewed and tested before it lands: 435 tests covering module mocking, SSRF and auth, and reverse-proxy behaviour. Bug reports and pull requests are welcome.

---

## Credits

PRISM stands on the shoulders of excellent open-source projects and public data sources.

**Tools & techniques**
- [Maigret](https://github.com/soxoj/maigret): username search across thousands of sites (run as a subprocess; included in requirements.txt, not in the Docker image, where the module reports itself as skipped)
- Username heuristics inspired by [Sherlock](https://github.com/sherlock-project/sherlock) and [Blackbird](https://github.com/p1ngul1n0/blackbird)

**Data sources & APIs**
- crt.sh, Wayback Machine, Shodan, VirusTotal, AbuseIPDB, Censys, Ahmia, XposedOrNot, ipinfo.io, CoinGecko, BlockCypher, blockchain.info, Ethplorer, api.qrserver.com

**Core libraries**
- Backend: FastAPI, Uvicorn, Pydantic, SQLAlchemy, slowapi, phonenumbers, dnspython, python-whois, Pillow, xhtml2pdf
- Frontend: Next.js, React, Tailwind CSS, Leaflet

Each project is the property of its respective authors and used under its own license. PRISM itself is MIT-licensed.

---

## License

MIT
