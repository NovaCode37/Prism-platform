# Configuration

PRISM is configured via environment variables (`.env`). External provider keys are optional. Modules that need a missing provider key gracefully skip.

## API keys and anonymous mode

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

## Core auth & networking

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
| `MODULE_PROXY`       | Proxy for every outbound module request, `http(s)://` or `socks5://` ([guide](proxies.md)) |
| `ALLOW_PRIVATE_TARGETS` | `true` to allow scanning private/internal addresses (default `false`) |
| `WATCHLIST_SCHEDULER` | `true` to enable the watchlist background scheduler                     |
| `WATCHLIST_POLL_SECONDS` | How often the scheduler checks for due watchlists (default `60`)     |
| `LLM_BASE_URL`       | OpenAI-compatible chat-completions URL; overrides the provider default   |
| `LLM_API_KEY`        | Key for `LLM_BASE_URL`; falls back to `OPENROUTER_API_KEY`/`GROQ_API_KEY`|
| `LLM_MODEL`          | Model name for AI summary and chat; overrides the provider default       |
| `LLM_PROXY`          | Optional `http(s)://` or `socks5://` proxy for outbound LLM requests ([guide](proxies.md)) |

## Reverse proxy

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

## External provider keys

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

## Variables

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

---

Back to the [readme](../README.md).
