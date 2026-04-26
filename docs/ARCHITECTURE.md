# PRISM Architecture

This document explains how PRISM is organized, how data flows through the system,
and how to extend it with new modules.

---

## High-level overview

```
                ┌────────────────────────────────────────┐
                │         Frontend (Next.js 14)          │
                │  React · TypeScript · Tailwind · i18n  │
                └───────────────┬────────────────────────┘
                                │  HTTPS / WS
                                ▼
                ┌────────────────────────────────────────┐
                │       FastAPI backend (web/app.py)     │
                │  REST + WebSocket · slowapi rate limit │
                └───────────────┬────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
       ┌────────────┐    ┌────────────┐    ┌──────────────┐
       │  modules/  │    │ scan cache │    │  LLM (OAI)   │
       │  22+ OSINT │    │  on-disk   │    │ OpenRouter   │
       └─────┬──────┘    └────────────┘    └──────────────┘
             │
             ▼
   3rd-party APIs (Shodan, Censys, VT, AbuseIPDB,
   Ahmia, DarkSearch, crt.sh, Wayback, HIBP, …)
```

---

## Directory layout

| Path | Purpose |
|------|---------|
| `web/app.py` | FastAPI entry point, scan orchestration, WS streaming |
| `web/security.py` | API-key auth, rate-limit, CORS allowlist |
| `modules/*.py` | OSINT collection modules — one file per data source |
| `modules/opsec_score.py` | Aggregated 0–100 exposure score |
| `modules/graph_builder.py` | Entity → relationship graph data |
| `modules/report_generator.py` | Jinja2 HTML + WeasyPrint PDF reports |
| `frontend/src/components` | UI: Sidebar, Topbar, ScanProgress, ScanResults |
| `frontend/src/lib/i18n.tsx` | Lightweight i18n provider (en + ru) |
| `frontend/src/messages/*.json` | Locale string files |
| `tests/` | pytest suite, monkeypatched (no live API calls) |
| `docs/` | Architecture, screenshots, demo gifs |
| `.github/workflows/ci.yml` | CI: lint + tests + Docker build smoke test |

---

## Scan lifecycle

1. **POST `/api/scan`** — frontend sends `{ target, scan_type, modules[] }`
2. Backend validates target, allocates `scan_id`, persists scan stub to disk
3. `_execute_scan()` runs as a background task and streams events through `_push()`:
   - `module_start` → frontend marks module `running`
   - `module_done` → frontend marks `ok` / `error` and updates progress bar
   - `scan_complete` → final results saved to disk
4. **WS `/ws/{scan_id}`** — frontend subscribes for real-time progress
5. Module results are cached in `module_cache/` (TTL 24h) for Shodan, HLR, VirusTotal, AbuseIPDB, GeoIP
6. After all modules finish, `opsec_score.score_from_results()` aggregates findings
7. `graph_builder.build_graph()` creates the visualization graph
8. `report_generator.generate_html_report()` writes a self-contained HTML file
9. PDF endpoint (`/api/scan/{id}/report/pdf`) renders the same HTML via WeasyPrint

### Real-time progress

```
Frontend                          Backend
   │   POST /api/scan                 │
   │ ────────────────────────────────►│
   │   { scan_id }                    │  spawn task
   │ ◄────────────────────────────────│
   │   WS /ws/{scan_id}               │
   │ ────────────────────────────────►│
   │   { type: module_start, … }      │
   │ ◄────────────────────────────────│  emit per module
   │   { type: module_done,  status } │
   │ ◄────────────────────────────────│
   │             ⋮                    │
   │   { type: scan_complete }        │
   │ ◄────────────────────────────────│
   │   GET /api/scan/{id}             │  fetch full results
   │ ────────────────────────────────►│
```

---

## Adding a new module

1. Create `modules/your_module.py` with a class exposing a method `lookup()` /
   `search()` that returns a JSON-serializable `dict`. Always include
   `"error": str | None` so the UI can render gracefully.
2. Register it in `web/app.py` inside the appropriate `_execute_scan()`
   branch via `_run_module(scan_id, "your_module", obj.method, target)`.
3. Add the module id + label in `frontend/src/components/Sidebar.tsx`
   (`MODULE_MAP`).
4. Add a TypeScript shape in `frontend/src/lib/types.ts` and a tab in
   `ScanResults.tsx` if the data needs its own view.
5. Add unit tests in `tests/` (mock all network with `monkeypatch`).

### Module contract example

```python
class CensysLookup:
    def search_ip(self, ip: str) -> dict:
        # returns: { error, ip, asn, open_ports, services, total }
        ...
```

---

## OPSEC scoring

`modules/opsec_score.py` computes 0–100 risk across 4 categories:

- **Data Exposure** — emails, breaches, leaked credentials
- **Identity OPSEC** — username footprint across social networks
- **Infrastructure** — exposed ports, missing TLS, dark-web mirrors
- **Web Security** — SPF / DMARC / cert hygiene

Each finding has a severity (LOW / MEDIUM / HIGH / CRITICAL) and a deduction
weight. The frontend renders the score bars and findings tab from this output.

---

## Reports

Both HTML and PDF reports use the same Jinja2 template inside
`modules/report_generator.py`. The HTML version embeds a Leaflet map (JS).
The PDF variant strips JavaScript and is rendered with **WeasyPrint** so it
works fully offline with `@media print` styles.

---

## i18n (internationalisation)

The frontend ships a lightweight provider in `frontend/src/lib/i18n.tsx`:

- Locale stored in `localStorage` (`prism_locale`)
- Auto-detects from `navigator.language` on first run
- Strings live in `frontend/src/messages/{en,ru}.json`
- `useTranslations()` hook exposes `{ locale, setLocale, t }`

Adding a new language is as simple as dropping a new JSON file with the same
schema and adding it to the `MESSAGES` map.

---

## Security model

- **API key auth** — `X-API-Key` header or `?api_key=` query param
- **CORS allowlist** — controlled via `CORS_ORIGINS` env
- **Rate limit** — `slowapi` global + per-endpoint
- **SSRF guard** — `validate_url_not_private()` for any user-provided URLs
- **Upload size limit** — `MAX_UPLOAD_BYTES` enforced before parsing
- **Input validation** — Pydantic + custom validators (`validate_target`,
  `validate_scan_id`)
- **Security headers** — X-Frame-Options, Referrer-Policy, etc. middleware
- **Optional `DISABLE_DOCS=1`** — turn off `/docs` & `/openapi.json` in prod

---

## Tests

```
pytest tests/ -v --cov=modules --cov-report=term-missing
```

The suite uses `monkeypatch` to replace HTTP / DNS calls with deterministic
mocks. **No live network hits are made in CI.**

---

## CI/CD

`.github/workflows/ci.yml` runs on every push & PR:

1. `flake8` lint over `modules/` and `web/`
2. `pytest` with coverage on Python 3.10 & 3.11
3. Codecov upload
4. Docker image build + 10-second smoke test (`curl /`)

---

## Production deploy

The reference deployment uses:

- Nginx reverse proxy (TLS via Let's Encrypt)
- `uvicorn` workers behind systemd
- Static frontend served via `next build && next start` or a CDN
- `module_cache/` and `scan_data/` mounted on persistent volume
- Redis is optional — currently scan state is on-disk for simplicity

See `docker-compose.yml` for a one-command stack.
