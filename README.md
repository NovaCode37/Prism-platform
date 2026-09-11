<div align="center">

# PRISM

**Self-hosted OSINT platform with 22+ modules, OPSEC scoring, AI summary, and a real-time web dashboard.**

Scan a domain, IP, email, phone or username and get WHOIS, DNS, threat intel, breach data, username search, dark-web mirrors, OPSEC score, entity graphs, and HTML/PDF reports in seconds.

**[Live Demo](https://getprism.su)** · **[Docker Quick Start](#docker-recommended)** · **[Architecture](docs/ARCHITECTURE.md)** · **[Security](SECURITY.md)** · **[Changelog](CHANGELOG.md)** · **[FAQ](#faq)**

[![CI](https://github.com/NovaCode37/Prism-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/NovaCode37/Prism-platform/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-2.8.1-7c5cfc?style=flat-square)](CHANGELOG.md)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-getprism.su-7c5cfc?style=flat-square&logo=firefox)](https://getprism.su)
[![Firefox Add-on](https://img.shields.io/amo/v/prism-osint?style=flat-square&logo=firefoxbrowser&logoColor=white&label=Firefox%20Add-on&color=ff7139)](https://addons.mozilla.org/en-US/firefox/addon/prism-osint/)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

</div>

> **AI analysis does not work on the [live demo](https://getprism.su).** It runs on shared hosting whose region every hosted LLM provider refuses at their edge, so the request never reaches a model. That panel is the only thing affected. Every other module works, and on a self-hosted instance with your own provider the AI works normally. See [the FAQ](#faq) for why.


<div align="center">

### Table of Contents

[Why PRISM?](#why-prism) • [Overview](#overview) • [How it compares](#how-it-compares) • [Use cases](#use-cases) • [Features](#features) • [Showcase](#showcase) • [Quick Start](#quick-start) • [Configuration](#configuration) • [API](#api) • [Project Structure](#project-structure) • [Running Tests](#running-tests) • [CI/CD](#cicd) • [Roadmap](#roadmap) • [Star History](#star-history) • [Legal Notice](#legal-notice) • [Support the project](#support-the-project) • [Contributing](#contributing) • [Credits](#credits) • [License](#license)

</div>

<p align="center">
  <img src="docs/gifs/main.gif" alt="PRISM Boot Animation" width="720" />
</p>

---

## Why PRISM?

- **22+ modules**: WHOIS, DNS, crt.sh, Wayback Machine, Shodan, VirusTotal, AbuseIPDB, Censys, dark-web mirrors, email reputation, SMTP verify, breach lookup, Blackbird (50+ sites), Maigret (3000+ sites), Telegram, phone HLR, email headers, file metadata, and more
- **AI summary**: written summary of the findings, plus a chat you can ask follow-up questions in. Needs an LLM provider of your own.
- **Real-time dashboard**: WebSocket-driven scan progress with per-module progress, an entity graph and a GeoIP map
- **OPSEC Score**: aggregated 0-100 exposure risk score across data exposure, identity, infrastructure and web security
- **HTML, PDF, CSV & Markdown reports**: export full scan results as HTML, PDF, CSV, or Markdown (locale-aware EN/RU/DE)
- **Multi-language UI**: English, Russian, German, French, Spanish, Italian, Polish, Portuguese, and Chinese out of the box (i18n + auto-detect)
- **Standalone CLI**: run scans headlessly via `python cli.py scan example.com --json`, and manage scheduled re-scans with `python cli.py watchlist add example.com --interval 6`
- **Scan history & comparison**: browse past scans, load results, compare two scans side-by-side
- **Webhook callbacks**: get notified on scan completion with HMAC-signed payloads (SSRF-protected), Slack/Discord formatters
- **Hardened auth**: header-only API keys (`X-API-Key` / `Bearer`), no query-string secrets, strict CORS, per-principal scan isolation
- **Zero mandatory API keys**: 14 out of 22 modules work without any keys at all
- **One-command deploy**: `docker run ghcr.io/novacode37/prism-platform` with nothing to build (amd64 and arm64)
- **MIT licensed**, and adding a module means one file in `modules/`

---

## Overview

PRISM queries 20-odd external sources and puts what comes back in one place. Targets can be a domain, an IP, an email, a phone number or a username. Results land in a dashboard as they arrive, with a relationship graph, a GeoIP map, an exposure score and HTML or PDF export.

**Stack:**
- **Backend**: Python 3.10+, FastAPI, asyncio, WebSocket, Pydantic, slowapi (rate limiting), xhtml2pdf (PDF)
- **Frontend**: Next.js 14 (App Router), React, TypeScript, Tailwind CSS, Leaflet (maps)
- **AI**: OpenRouter (Nvidia Nemotron) or Groq (Llama-3) for summary and chat
- **Infrastructure**: Docker, docker-compose, GitHub Actions CI/CD
- **Tests**: pytest, 361 cases, network mocked

<p align="center">
  <img src="docs/pics/main_showcase/main_showcase.png" alt="PRISM Dashboard" width="720" />
</p>

### Architecture (high level)

```mermaid
flowchart LR
    U[User / Browser] -->|HTTPS + X-API-Key| FE[Next.js 14 Dashboard]
    FE -->|REST + WebSocket| API[FastAPI Backend]
    API --> SCH[Scan Orchestrator<br/>asyncio + queues]
    SCH --> MOD[22+ OSINT Modules]
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
| Maigret | Deep username search across 3000+ sites | none |
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

Images are published for `linux/amd64` and `linux/arm64`, so this works on a Raspberry Pi or an ARM VPS as well. Tags follow releases: `latest`, `2.9`, `2.9.0`, plus `edge` built from `main`.

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

The example `.env` is intentionally easy to run: `ALLOW_ANON_API=true` and no API key is required. Before exposing PRISM beyond your machine, switch to API-key mode as shown in [API keys and anonymous mode](#api-keys-and-anonymous-mode).

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

PRISM is configured via environment variables (`.env`). External provider keys are optional. Modules that need a missing provider key gracefully skip.

### API keys and anonymous mode

PRISM has two API access modes. The `/healthz` endpoint is always unauthenticated for container and reverse-proxy health checks; application endpoints under `/api/*` and `/ws/*` follow the mode below.

**Anonymous local/demo mode** is meant for a laptop, a private test VM, or the demo compose file. Anyone who can reach the HTTP server can start scans and use tools.

```env
ALLOW_ANON_API=true
API_KEYS=
API_KEY=
PRISM_UI_API_KEY=
```

**API-key mode** is the recommended mode for shared, reverse-proxied, or internet-facing deployments. `API_KEYS` is preferred because it supports multiple accepted keys; `API_KEY` is kept as a legacy single-key option. Each accepted key maps to its own principal, so scan history is isolated per key.

```env
ALLOW_ANON_API=false
API_KEYS=replace-with-a-long-random-ui-key
API_KEY=
PRISM_UI_API_KEY=replace-with-the-same-long-random-ui-key
```

Clients authenticate with either `X-API-Key: <key>` or `Authorization: Bearer <key>`. When Docker serves the Next.js UI from FastAPI, set `PRISM_UI_API_KEY` to one key that is also present in `API_KEYS` so the browser can call the API. This value is injected into public frontend config, so treat it as a browser-visible UI key, not as a private server secret. For extra users or automation, add more comma-separated entries to `API_KEYS`. If you run `npm run dev` separately, put the same kind of UI key into `frontend/.env.local` as `NEXT_PUBLIC_API_KEY`.

Common auth errors:

| Error | Meaning | Fix |
|-------|---------|-----|
| `HTTP 503: API auth is not configured on server.` | No `API_KEYS`/`API_KEY` were loaded and `ALLOW_ANON_API` is not `true`. | Set `ALLOW_ANON_API=true` for local anonymous mode, or configure `API_KEYS` and restart. |
| `HTTP 401: Invalid or missing API key.` | The backend has keys configured, but the request did not send a matching key. | Set `PRISM_UI_API_KEY` / `NEXT_PUBLIC_API_KEY`, or send `X-API-Key` / `Authorization: Bearer`. |

After changing `.env` for Docker, recreate the container so the backend and runtime UI config see the new values:

```bash
docker compose up -d --force-recreate
```

### Core auth & networking

| Variable             | Purpose                                                                 |
|----------------------|-------------------------------------------------------------------------|
| `API_KEYS`           | Comma-separated accepted API keys; preferred for API-key mode           |
| `API_KEY`            | Single accepted API key; legacy option                                  |
| `ALLOW_ANON_API`     | `true` to allow unauthenticated API access; local/demo only             |
| `PRISM_DEMO_MODE`    | `true` to show the public demo notice in the UI                         |
| `ALLOWED_ORIGINS`    | Comma-separated CORS origins; empty/unset = no cross-origin             |
| `PRISM_BASE_PATH`    | Public API/WS path prefix when mounted under a subpath, e.g. `/prism`   |
| `PRISM_UI_API_KEY`   | Public browser UI key injected into the Docker-served UI                |
| `PRISM_FRONTEND_DIR` | Optional static Next.js export path (default `frontend/out`)            |
| `NEXT_PUBLIC_API_URL`| Optional external API origin for frontend builds/runtime config         |
| `NEXT_PUBLIC_BASE_PATH` | Next.js build-time asset prefix for subpath deployments              |
| `TRUST_PROXY_HEADERS`| `true` to trust forwarded headers from configured reverse proxies       |
| `FORWARDED_ALLOW_IPS`| Comma-separated proxy IPs allowed to set `X-Forwarded-*` headers        |
| `TRUSTED_HOSTS`      | Optional comma-separated allowed `Host` values for the backend          |
| `HEALTHCHECK_HOST`   | Optional Host header override for Docker health checks                  |
| `MAX_UPLOAD_MB`      | Max upload size for file-based tools (default `20`)                     |
| `MAX_STORED_SCANS`   | In-memory scan cap before disk-only mode (default `200`)                |
| `CACHE_TTL_HOURS`    | Per-module cache TTL (default `24`)                                     |
| `WEBHOOK_SECRET`     | If set, signs webhook callbacks with `X-Prism-Secret`                   |
| `DISABLE_DOCS`       | `true` to disable `/docs`, `/redoc`, `/openapi.json` in production      |
| `SCAN_QUOTA_PER_DAY` | Daily scans per caller; `0`/unset = unlimited                            |
| `HUDSONROCK_ENABLED` | `true` to enable the infostealer-exposure module (queries Hudson Rock) |
| `LUNAR_ENABLED`      | `true` to enable the domain-exposure module (queries Lunar)             |
| `MODULE_PROXY`       | Proxy for every outbound module request |
| `ALLOW_PRIVATE_TARGETS` | `true` to allow scanning private/internal addresses (default `false`) |
| `WATCHLIST_SCHEDULER` | `true` to enable the watchlist background scheduler                     |
| `WATCHLIST_POLL_SECONDS` | How often the scheduler checks for due watchlists (default `60`)     |
| `LLM_BASE_URL`       | OpenAI-compatible chat-completions URL; overrides the provider default   |
| `LLM_API_KEY`        | Key for `LLM_BASE_URL`; falls back to `OPENROUTER_API_KEY`/`GROQ_API_KEY`|
| `LLM_MODEL`          | Model name for AI summary and chat; overrides the provider default       |
| `LLM_PROXY`          | Optional `http(s)://` or `socks5://` proxy for outbound LLM requests     |

### Reverse proxy

The supported Docker topology is a single container: FastAPI serves the exported Next.js UI plus `/api/*`, `/ws/*`, and `/healthz` on the same public origin. Keep `NEXT_PUBLIC_API_URL` empty for same-origin deployments. For subpath deployments, set `PRISM_BASE_PATH` at runtime and build the image with the same `NEXT_PUBLIC_BASE_PATH`.

Root deployment (`https://prism.example.com`):

```env
PRISM_BASE_PATH=
TRUST_PROXY_HEADERS=true
FORWARDED_ALLOW_IPS=172.18.0.1
TRUSTED_HOSTS=prism.example.com
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_BASE_PATH=
```

Subpath deployment (`https://example.com/prism`), with the proxy stripping `/prism` before forwarding to the backend:

```env
PRISM_BASE_PATH=/prism
TRUST_PROXY_HEADERS=true
FORWARDED_ALLOW_IPS=172.18.0.1
TRUSTED_HOSTS=example.com
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_BASE_PATH=/prism
```

After changing `NEXT_PUBLIC_BASE_PATH`, rebuild the image because Next.js asset paths are fixed at build time:

```bash
NEXT_PUBLIC_BASE_PATH=/prism docker compose build
docker compose up
```

Minimal nginx proxy for the single container:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /api/ {
    proxy_pass http://127.0.0.1:8080/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /ws/ {
    proxy_pass http://127.0.0.1:8080/ws/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

For `/prism`, proxy `/prism/`, `/prism/api/`, and `/prism/ws/` to the container while stripping the prefix. The legacy FastAPI HTML dashboard has been removed.

Minimal Caddy example:

```caddyfile
prism.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

### External provider keys

| Variable                          | Service                              | Free Tier        |
|-----------------------------------|--------------------------------------|------------------|
| `NUMVERIFY_API_KEY`               | Phone validation & carrier           | 100 req/mo       |
| `IPINFO_API_KEY`                  | GeoIP location                       | 50k req/mo       |
| `VIRUSTOTAL_API_KEY`              | Threat intelligence                  | 500 req/day      |
| `ABUSEIPDB_API_KEY`               | IP abuse score                       | 1000 req/day     |
| `SHODAN_API_KEY`                  | Port scan + CVE lookup               | Free tier        |
| `CENSYS_API_ID` + `CENSYS_API_SECRET` | Host & certificate search        | 250 req/mo       |
| `OPENROUTER_API_KEY`              | AI summary (Nvidia Nemotron)         | Free tier        |
| `GROQ_API_KEY`                    | AI fallback (Llama-3 instant)        | Free tier        |
| `TELEGRAM_BOT_TOKEN`              | Telegram user lookup                 | Free             |
| `LEAK_LOOKUP_API_KEY`             | Breach database                      | Limited free     |

### Variables

| Variable             | What it enables                                   | Required? | Where to Get               |
| :--------------------| :------------------------------------------------ | :-------- | :------------------------- |
| `API_KEYS`           | Preferred comma-separated accepted API keys for API-key mode | Auth mode only | Generate long random strings |
| `API_KEY`            | Legacy single accepted API key for API-key mode | Auth mode only | Generate a long random string |
| `ALLOW_ANON_API`     | Allows unauthenticated local/demo API requests without a key | No | `true` for local/demo, `false` for production |
| `PRISM_DEMO_MODE`    | Shows the public demo notice in the UI | No | `true` only for the demo compose setup |
| `NUMVERIFY_API_KEY`  | Validates phone numbers                           | No   | Numverify dashboard             |
| `LEAK_LOOKUP_API_KEY`| Searches Data Breaches for Leaked Credentials     | No   | LeakLookup API dashboard        |
| `HIBP_API_KEY`       | Checks if Email/Passwords have been compromised   | No   | HIBP Developer Portal           |
| `IPINFO_API_KEY`     | Fetches geolocation and ASN details for IP addresses| No | IPInfo.io Dashboard             |
| `VIRUSTOTAL_API_KEY` | Scans file hashes and URLs for malware            | No   | VirusTotal API Dashboard        | 
| `ABUSEIPDB_API_KEY`  |Checks if an IP address has been reported for malicious activity | No | AbuseIPDB Dashboard  |
| `SHODAN_API_KEY`     |Searches for internet-connected devices and open ports | No | Shodan Developer Dashboard     |
| `TELEGRAM_BOT_TOKEN` | Sends automated scan alerts and reports directly to a Telegram channel | No | Telegram BotFather |
| `CENSYS_API_ID`      | Authenticates attack surface and internet-wide scanning queries | No | Censys Search Console |
| `CENSYS_API_SECRET`  | Paired with CENSYS_API_ID for Censys data access | No | Censys Search Console |
| `ALLOWED_ORIGINS`    | Configures CORS settings to restrict which frontend domains can talk to your backend | No | Set to a comma-separated list of domains |
| `PRISM_BASE_PATH`    | Public backend path prefix for reverse proxy subpath deployments | No | Set to `/prism` or leave empty |
| `PRISM_UI_API_KEY`   | Public browser UI key injected into the Docker-served UI | No | Use an accepted UI-scoped value from `API_KEYS` |
| `PRISM_FRONTEND_DIR` | Static Next.js export directory served by FastAPI | No | Defaults to `frontend/out` |
| `NEXT_PUBLIC_API_URL`| External API origin for frontend builds/runtime config | No | Leave empty for same-origin Docker |
| `NEXT_PUBLIC_BASE_PATH` | Build-time Next.js base path for subpath deployments | No | Match `PRISM_BASE_PATH`, then rebuild |
| `TRUST_PROXY_HEADERS`| Enables trusted `X-Forwarded-*` handling behind a reverse proxy | No | Set to true only behind trusted proxy |
| `FORWARDED_ALLOW_IPS`| Proxy source IPs allowed to set forwarded headers | No | Comma-separated IPs or `*` for trusted private networks |
| `TRUSTED_HOSTS`      | Restricts accepted backend Host headers | No | Comma-separated public hostnames |
| `HEALTHCHECK_HOST`   | Host header sent by Docker health checks | No | Defaults to first `TRUSTED_HOSTS` entry or localhost |
| `OPENROUTER_API_KEY` | AI summary & chat via OpenRouter (preferred LLM provider) | No | OpenRouter dashboard|
| `GROQ_API_KEY`       | AI summary & chat via Groq (fallback LLM provider) | No | Groq Console |
| `MAX_STORED_SCANS`   |Max scans kept in memory before old ones are evicted (default 200) | No | Set An Integer Value |
| `DISABLE_DOCS`       | Disables the /docs and /redoc API documentation pages | No | Set to True/False |
| `WEBHOOK_SECRET`     | Adds an X-Prism-Secret header to webhook callbacks for verification | No | Generate a Placeholder string |
| `MAX_UPLOAD_MB`      |Sets the maximum file size limit for uploads, defaults to 20MB if missing.| No| Set an integer value |
| `WEBHOOK_FORMAT`     |Configures the format for webhook data payloads. | No | Set to raw, slack, or discord|
| `CACHE_TTL_HOURS`    |Module cache TTL in hours | No | Set an integer value |

---

> Certificate Transparency, Wayback Machine, DNS, WHOIS, Website Analyzer, Email Reputation, SMTP Verify, Blackbird, Maigret, Email Headers, File Metadata, and **Dark Web Checker** all work **with zero API keys**.

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
├── frontend/                     # Next.js 14 + TypeScript + Tailwind
│   └── src/
│       ├── app/                  # App Router pages
│       ├── components/           # UI (Topbar, Sidebar, Map, Graph, ...)
│       └── lib/                  # API client, i18n, types
│
└── tests/                        # 361 pytest tests
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

### v2.2 (released)
- [x] Multilingual report rendering (EN / RU / DE) via `report_i18n`
- [x] Webhook callbacks with HMAC signing + SSRF guard
- [x] Multi-marker Leaflet GeoIP map (replaces single-iframe map)
- [x] Hardened auth: header-only API keys, no query-string secrets
- [x] Strict CORS by default; `ALLOW_ANON_API` opt-in for anonymous mode
- [x] Phone map: removed coordinate fabrication, only explicit lat/lng
- [x] Authenticated HTML/PDF report download via blob fetch
- [x] Test suite expanded to **102 cases**

### v2.3 (released)
- [x] Scan history panel + side-by-side scan comparison (diff view)
- [x] CSV & Markdown report export (alongside HTML/PDF)
- [x] French (FR) & Spanish (ES) locales: UI now ships EN / RU / DE / FR / ES
- [x] Standalone CLI (`python cli.py scan <target> --json|--html|--pdf`)
- [x] Slack / Discord webhook formatters (`WEBHOOK_FORMAT=slack|discord`)
- [x] Rate-limit response headers, keyboard shortcuts, scan duration, copy-all-emails
- [x] Graceful module degradation: `skipped` / `rate_limited` statuses instead of hard errors
- [x] IP / Subnet calculator standalone tool
- [x] One-command demo (`docker compose -f docker-compose.demo.yml up`) with seeded scans
- [x] Reliable Leaflet map rendering + Unicode (Cyrillic) fonts in PDF export

### v2.4 (released)
- [x] GitHub user / organization recon module (profile, languages, repos, commit-metadata emails)
- [x] Hash Identifier and Base64 / URL encoder standalone tools
- [x] Per-module refresh: re-run a single module from its result card
- [x] Approximate region-level GeoIP map for phone scans
- [x] Scan history: sorted newest-first, auto-refresh, "Clear history", localized
- [x] Friendly empty states (graph tab) and more rotating sidebar tips
- [x] Hardening: Unicode (DejaVu) fonts in PDF, robust startup env parsing, apt-retry Docker builds

### v2.5 (released)
- [x] Scheduled scans + continuous monitoring / watchlists with diff alerting
- [x] Entity graph export to GEXF / GraphML (Gephi / Maltego)
- [x] Per-API-key quotas and usage-stats endpoint
- [x] Additional locale (ZH): 9 languages, with dark / light theme toggle
- [x] SSRF hardening for scan/watchlist targets + maigret path-traversal fix

### v2.6 (released)
- [x] Browser extension for one-click scans: **[live on Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/prism-osint/)** ([source](extension/))
- [x] Configurable LLM provider (`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` / `LLM_PROXY`): any OpenAI-compatible endpoint
- [x] Accessibility pass: reduced-motion, aria-live progress, scan-type ARIA labels

### v2.7 (released)
- [x] Domain exposure module (Lunar): yearly exposure trend, malware families, affected services; opt-in
- [x] Rate limits keyed on the peer address unless proxy headers are trusted
- [x] Username sanitised in Blackbird export paths and lookup URLs
- [x] Watchdog on maigret runs so a stalled process no longer hangs the scan

### v2.8 (released)
- [x] Username search confirmed against a control request: soft-404 sites no longer report accounts that do not exist
- [x] Blocked sites reported as `unknown` instead of counted as absent
- [x] Every configured LLM provider tried in turn, with Ollama shipped in the compose file behind a profile
- [x] Shodan falls back to the keyless InternetDB dataset when no paid key answers

### v2.9 (released)
- [x] Report translations for the six interface languages that still fell back to English (#295)
- [x] `MODULE_PROXY` honoured by every module that makes an outbound request, not just two
- [x] Scan the current page from the browser extension
- [x] HTML report follows the reader's dark mode
- [x] One User-Agent across every module, built from the version

### v2.10 (planned)
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
No. 14 of 22 modules work without any keys.

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

**Why is AI analysis dead on the demo?**
Hosted LLM providers refuse the demo's hosting region at their edge, so the call is rejected before it reaches a model. It is an IP-level block, not a bug and not a missing key. PRISM tries every provider you configure and reports what each one said.

The demo sits on shared hosting, which rules out the two normal workarounds: there is no room to run a local model, and no second machine to proxy through. So it stays broken there, and only there.

On your own instance it works. Point it at any OpenAI-compatible endpoint:

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

PRISM is built by one person, with AI assistance as part of the workflow. Everything gets reviewed and tested before it lands: 361 tests covering module mocking, SSRF and auth, and reverse-proxy behaviour. Bug reports and pull requests are welcome.

---

## Credits

PRISM stands on the shoulders of excellent open-source projects and public data sources.

**Tools & techniques**
- [Maigret](https://github.com/soxoj/maigret): username search across thousands of sites (run as a subprocess)
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
