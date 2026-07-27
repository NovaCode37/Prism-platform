# Changelog

All notable changes to PRISM are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [2.6.0] — 2026-07-27

### Added
- **Browser extension (Manifest V3)** — highlight or right-click any domain, IP, email, phone, or username and a full scan runs inside the extension popup, with live progress and result cards, no tab-switching. Points at your own PRISM instance or the public demo, optional API key, localized into all 9 languages. [Live on Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/prism-osint/).
- **Configurable LLM provider** — `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and `LLM_PROXY` env vars let the AI summary/chat target any OpenAI-compatible endpoint (OpenRouter, Groq, Gemini, local Ollama, …) or route through a proxy, without touching code.
- **Watchlists** — pause/resume for individual watchlists, a "Send test webhook" button, JSON/CSV export of watchlist alerts, and human-readable alert labels (with the raw fingerprint kept as a fallback).
- **Results quality-of-life** — a Copy button on the raw JSON tab (#195), `/` keyboard shortcut to focus the target input (#196), a clear button on the target field (#197), a legend on the entity graph (#205), and a "Report an issue" link in the topbar (#202).
- **Donations** — DonationAlerts and crypto (USDT/TON/BTC/ETH) options with QR codes.

### Accessibility
- `aria-label` + `aria-pressed` on the scan-type toggle buttons (#198).
- `aria-live` region so screen readers announce scan progress as modules finish (#182).
- Respect `prefers-reduced-motion` — animations and transitions are neutralized when the OS/browser requests reduced motion (#136).

### Fixed
- **Rate limiting behind a proxy** — the limiter now keys on the real client IP (`X-Forwarded-For`) instead of collapsing every visitor to the proxy address, which was tripping shared 429s on the demo.
- **LLM error handling** — provider errors returned as a plain string no longer crash with `'str' object has no attribute 'get'`; non-JSON provider responses now surface a readable message. The AI panel also raises its per-user limit to 10/minute.
- A clearer message when a PRISM instance requires an API key, a spinner on the Run Scan button while the request is in flight, and the Watchlists screen fully localized into all languages.

### Changed
- The public demo now explains, in the UI, why some third-party modules (crt.sh, Wayback) can return 5xx and why AI analysis may be blocked from certain hosting regions.
- Documented the 2.5.0 and new `LLM_*` environment variables in the README (#194).

### Tests
- Unit tests for the OPSEC score calculator.

---

## [2.5.0] — 2026-07-04

### Added
- **Watchlists & scheduled scans** — save a target to re-scan on a schedule and get alerted only when results actually change (new open ports, subdomains, breaches, DNS records). Diff alerting ignores volatile fields (timestamps, response times) so you see real changes, not noise. Optional webhook notifications. New `POST/GET/DELETE /api/watchlist` + `GET /api/watchlist/{id}/alerts` endpoints, a background scheduler, and a Watchlists UI in the topbar.
- **Entity graph export to GraphML / GEXF** — export the entity graph of any scan for Gephi or Maltego, via the Graph tab or `GET /api/scan/{id}/graph/export?fmt=graphml|gexf`.
- **Per-API-key quotas + usage endpoint** — optional daily scan quota per API key (`SCAN_QUOTA_PER_DAY`), enforced with a 429, plus a `GET /api/usage` endpoint reporting used / limit / remaining / reset time.
- **Chinese (Simplified) locale** — full `zh` translation; PRISM now ships in 9 languages with browser-language auto-detection.
- **CLI `--quiet` and `--version` flags** — `--quiet` suppresses banners/progress for clean piping; `--version` prints the version (#127).
- **Copy as cURL** button on scan results (#124), **Gravatar recon module** for email scans (#125), and per-value **empty-state placeholders** in results (#144).
- Additional **good-first-issue** contributions: `--output` CLI flag, custom 404 page (#112), aria-labels on icon buttons (#135), Italian / Portuguese / Polish locales, `/api/health` endpoint (#128), and expanded Base64/URL-encoder and module-status test coverage.

### Security
- **SSRF hardening** — scan targets (and watchlist targets) that resolve to private, loopback, link-local, or cloud-metadata addresses are blocked by default; self-hosters can allow them with `ALLOW_PRIVATE_TARGETS=true`.
- **Maigret path-traversal fix** — usernames are sanitized before being used in output filenames, and passed after a `--` separator so a `-`-prefixed username can't be parsed as a flag.

### Changed
- **Readability** — the UI now uses the Inter sans-serif font instead of the Silkscreen pixel font (kept only for the PRISM logo wordmark), and the low-contrast dark-theme secondary text color was raised to meet readable contrast for field labels, inactive tabs, and placeholders (#130).
- **Scan targets are normalized** before type detection — leading `http(s)://`, trailing slashes, and case are stripped so `HTTPS://Example.COM/` scans cleanly (#142).
- The frontend now runs in CI (typecheck, lint, tests, build).

### Fixed
- **Mobile: the target field couldn't be used** — the landing screen's `target://` box was a decorative element, not a real input, so tapping it never brought up the keyboard (especially on iOS). It is now a real input that auto-detects the target type and starts a scan directly from the home screen.

---

## [2.4.0] — 2026-06-17

### Added
- **GitHub user/organization recon module** — given a username it returns the public profile, top languages, repo/star counts, and emails leaked in commit metadata; works without a token and degrades to `rate_limited` when the API throttles (#95).
- **Base64 & URL encoder/decoder** standalone tool.
- More rotating sidebar tips, localized across all five languages (#74).
- **Graceful degradation for key-dependent modules** — a standard status enum (`ok` / `skipped` / `rate_limited` / `error`) in `modules/module_status.py`; Shodan, VirusTotal, AbuseIPDB, Censys, Leak-Lookup/HIBP and Telegram now report `skipped` when an API key is absent and `rate_limited` on HTTP 429 instead of failing, with per-module status badges in the dashboard (#61).
- **`HIBP_API_KEY` config option** — the HIBP breach lookup reads a real key and skips up-front when it is absent, instead of always hitting an unauthenticated 401 (#61).
- **One-command demo** — `docker compose -f docker-compose.demo.yml up` boots PRISM with preloaded sample scans, no API keys required (#63).
- **IP / Subnet calculator** standalone tool (#45).
- **Hash Identifier** standalone tool — detects MD5 / SHA-1 / SHA-256 / SHA-512 from length and charset (#76).
- **Per-module refresh** — a refresh button on each result card re-runs just that module and updates its result (#104).
- **Approximate region-level GeoIP map for phone scans** — geocodes the operator region and highlights the area (clearly labelled "approximate") instead of leaving the map blank.
- **Bundled Unicode fonts (DejaVu Sans/Mono)** for PDF reports.
- **Project polish** — README API reference + environment-variables table, FAQ, Table of Contents, `LICENSE` (MIT), `CITATION.cff`, `SUPPORT.md`, `CODEOWNERS`, `.editorconfig`, `.gitattributes`, `.dockerignore`, Sponsor/funding config, and Bug/Feature issue forms.

### Changed
- **Scan history** is now sorted by date (newest first), auto-refreshes after a scan completes, and its labels are localized in all five languages.
- The scan engine caches only genuinely successful (`ok`) results, so a missing key is not frozen in cache once configured (#61).
- The Censys tab is hidden when the module is skipped (no API key) instead of showing an empty card.
- Removed the default Leaflet attribution flag from all maps.
- The Graph tab shows a clear, localized empty state instead of a blank area (#77).
- The Dockerfile retries `apt-get` downloads (`Acquire::Retries`), making builds more robust on flaky networks (#121).

### Fixed
- **PDF reports rendered non-Latin text (e.g. Cyrillic) as empty grey boxes** — bundled DejaVu fonts now render Unicode correctly.
- **GeoIP map sometimes rendered blank** — the map recalculates its size after the layout settles.
- **New scans could be missing from history** — the list was capped before sorting; it now sorts by date, then caps.
- **Sidebar "Modules" label showed the raw i18n key** (duplicate `sidebar.modules`) — fixed and localized.
- **Empty numeric env vars crashed startup** — `CACHE_TTL_HOURS`, `MAX_STORED_SCANS` and `MAX_UPLOAD_MB` fall back to their defaults when set to an empty value (#122).

---

## [2.3.0] — 2026-06-03

### Added
- **Scan history** — collapsible History panel in sidebar fetches past scans from `/api/scans` and loads results on click (#38).
- **Scan comparison mode** — select two scans from history and view a side-by-side diff table with added/removed/changed fields (#58).
- **CSV export** — flattened Module/Key/Value CSV download with BOM for Excel compatibility (#43).
- **Markdown export** — structured `.md` report with OPSEC score, WHOIS, DNS, subdomains, and accounts (#55).
- **French (FR) locale** — full UI translation including new toolPanels, tips, scanTypes, and module labels (#14).
- **Spanish (ES) locale** — full UI translation with the same coverage (#28).
- **Standalone CLI** — `python cli.py scan <target>` with `--json`, `--html`, `--pdf` output, module selection, and auto-type detection (#39).
- **Slack/Discord webhook formatters** — `WEBHOOK_FORMAT=slack|discord` env var transforms payloads to Block Kit or embed format (#35).
- **Rate-limit response headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` via slowapi built-in handler (#37).
- **Keyboard shortcuts** — ArrowLeft/ArrowRight cycles result tabs, skips inputs (#33).
- **Copy all emails** — aggregates emails from WHOIS, emailrep, breaches, and scan target into one-click copy (#34).
- **Scan duration** — displays elapsed time in results header (#29).
- **Username filter** — search input in accounts tab to filter platforms (#44).
- **Loading skeleton** — pulse-animated placeholder shown during scan progress (#54).
- **ESLint config** — `next/core-web-vitals` ruleset for frontend (#36).
- **GitHub PR template** — standardized pull request description format (#48).
- **Minor fixes**.

### Changed
- Sidebar refactored to use i18n module labels (`sidebar.modules.<id>`) and localized scan type buttons.
- `_rate_limit_exceeded_handler` replaces inline lambda for proper 429 response headers.


---

## [2.2.0] — 2026-05-26

### Added
- Multilingual report translation layer via `modules/report_i18n.py` for ENG/RUS/DET report rendering.
- New map i18n keys for precision metadata (`precision`, `approximate`) across ENG/RUS/DET locales.

### Changed
- Frontend map rendering switched from single-marker OSM iframe to Leaflet multi-marker rendering in `ScanResults`.
- Frontend version labels updated to `v2.2.0` in topbar and loading screen.
- Backend and frontend application versions bumped to `2.2.0`.

### Fixed
- `#27` map view now renders all discovered locations instead of only the first marker.
- `#26` Wayback sensitive URL findings are included in dashboard flow (`wayback.interesting`) and displayed in results.
- `#25` phone map no longer fabricates coordinates from region/country guesses; marker is shown only for explicit coordinates.
- `#21` API key is no longer accepted via query string and permissive wildcard CORS default is removed.
- `#20` auth bypass with missing API keys is removed by default; anonymous mode requires explicit `ALLOW_ANON_API=true`.
- Comment/docstring cleanup completed across source files with build-safe manual TSX repairs.

---

## [2.1.1] — 2026-05-18

### Added
- **Webhook callback support** — pass an optional `webhook_url` in
  `POST /api/scan`; a `POST` is delivered to that URL when the scan
  reaches a terminal state. Signed with `X-Prism-Secret` when
  `WEBHOOK_SECRET` is set. Private/loopback hosts are rejected.
  Docs: `docs/ARCHITECTURE.md` (issue #18).
- **OPSEC category tooltips** — hover over a category in the score bar
  to see a one-line explanation of what it measures (issue #17).
- **Alt+T keyboard shortcut** to toggle dark/light theme. Topbar
  tooltip updated with the hint (issue #15).
- **German (DE) locale** — full UI translation; language switcher now
  cycles EN → RU → DE and auto-detects from `navigator.language`
  (issue #12).
- AI summary copy button refactored to share the global
  `copyValue` + toast mechanism (PR #19 follow-up).

### Changed
- **PDF export** switched from WeasyPrint (52.5, broken on Windows
  without GTK) to **xhtml2pdf** (pure-Python). A dedicated
  PDF-friendly template is used so output is stable across OSes.

### Fixed
- PDF export endpoint no longer returns `501` / install errors on
  Windows. Generated PDFs render OPSEC score, findings, WHOIS, DNS,
  GeoIP, subdomains, threat intel and phone data correctly.

---

## [2.1.0] — 2026-04-26

### Added
- **Module-level scan progress bar** — real-time `5/8 modules · 62%`
  visual indicator with per-module status chips (issue #9).
- **PDF report export** — `GET /api/scan/{id}/report/pdf` renders the
  HTML report with WeasyPrint. Frontend "PDF Report" button (issue #8).
- **Censys integration** — host services + certificate-based subdomain
  discovery via Censys Search API v2 (issue #3).
- **Dark-web `.onion` mirror checker** — aggregates Ahmia + DarkSearch
  for any domain or organization name (issue #2).
- **i18n / multi-language UI** — English & Russian out of the box,
  language switcher in the topbar, auto-detection from
  `navigator.language` (issue #1).
- **One-click copy buttons** across scan results
  (target, IP, emails, DNS records, subdomains, account URLs, ports).
- **Architecture documentation** — `docs/ARCHITECTURE.md`.
- **Roadmap & Star History** sections in README.

### Changed
- README rewritten for v2.1: refreshed badges, module table, key list,
  features list, roadmap section.
- "Print PDF" button now downloads a server-rendered PDF instead of
  invoking the browser print dialog.
- 22+ modules, 14 of which work with **zero API keys**.

### Fixed
- Merge conflict in `ScanResults.tsx` header that broke the build on
  certain mirror checkouts.
- Module progress in `ScanProgress` no longer relies on log parsing.

---

## [2.0.0] — 2026-04-08

### Added
- Initial public release.
- 20+ OSINT modules across 5 scan types (domain, ip, email, phone, username).
- Real-time WebSocket dashboard.
- AI summary + chat via OpenRouter (Nvidia Nemotron).
- HTML scan reports.
- OPSEC scoring (0–100) with categorical breakdown.
- Entity relationship graph and GeoIP map.
- Docker / docker-compose deploy.
