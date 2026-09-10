# Changelog

All notable changes to PRISM are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [2.9.0] — 2026-09-10

Most of this release came from contributors. Names are on the pull requests.

### Security
- **`MODULE_PROXY` reached two modules out of twenty-two.** Everything else connected directly. Anyone who set a proxy so a target would not see where the request came from was getting that for Hudson Rock and Lunar, and their own address for the other twenty, while the readme said the setting covered outbound module requests. A shared helper now routes every module that makes an HTTP call, and a walk over the syntax tree of `modules/` confirms nothing is left out (#324, #331).
- The dark-web lookups went through the same fix afterwards. They had been left out on the grounds that Tor needs a SOCKS proxy, but `onion_checker` never touches Tor: both of its requests go to ahmia.fi and darksearch.io over ordinary HTTPS, which is precisely the traffic someone sets a proxy to hide.
- **Six handlers returned the text of whatever exception they caught.** Depending on what broke that could be a filesystem path, a library internal, or a third-party URL with a key in the query string. They log the detail and answer with a fixed message now. The 4xx responses are unchanged, since those messages are written for the caller and are safe (#323, #334).
- Only `maigret` is still outside `MODULE_PROXY`, because it runs as a subprocess. That is written down in `SECURITY.md` rather than left for someone to discover.

### Added
- **Report translations for Spanish, French, Italian, Polish, Portuguese and Chinese.** Reports in those interfaces used to fall back to English. All nine locales now carry the same 57 keys (#295, #337).
- **The HTML report follows the reader's dark mode**, with light as the base so it degrades correctly. The PDF, which is built from the same HTML by a converter that ignores media queries, now comes out light instead of dark (#303, #336).
- **Scan the current page from the browser extension.** No extra permission was needed for it: the existing host permissions already cover reading the active tab's URL (#243, #332).
- **A "copy all findings" button** on the OPSEC findings list (#236, #329).
- **A `/` hint in the target field**, shown only while the field is empty (#234, #327).
- RDAP registration lookups alongside WHOIS, and tests for `graph_builder`, `detect_type`, scan-target normalization and the Slack and Discord webhook formatters.

### Fixed
- **Discord webhooks were silently dropped when a scan found enough.** Discord rejects a field value over 1024 characters, and `_send_webhook` swallows the error, so a busy scan produced no notification and no complaint. Long values are truncated now (#321, #335).
- **`<html lang>` was always `en`** whatever interface language was selected, so screen readers and translation tools were told the wrong language (#235, #328).
- **RDAP reported `292` as the registrar for github.com.** jCard properties are `[name, params, type, value]`, so reading index 2 gave the type and every contact came back as `"text"`; the registrar was read from the entity handle, which is the IANA id rather than a name.
- **Every `.ru` domain looked unregistered.** A `404` from rdap.org was read as "not registered", but plenty of zones serve no RDAP at all. The zone is checked against the bootstrap map first and the module reports `skipped`.
- **A rate-limited request reached the browser as a CORS error** rather than a `429`, because `add_middleware` wraps from the inside out and CORS had ended up innermost.
- **File work blocked the event loop in two routes**, stalling every other request including websocket scan progress while an upload was copied or the scan directory was read.
- The four `react-hooks/exhaustive-deps` warnings are gone, each by a different fix, so the loading animation does not restart on a parent re-render (#322, #338).

### Changed
- **One User-Agent everywhere**, built from `PRISM_VERSION`, replacing ten strings whose versions had drifted between 2.0 and 2.4. The browser strings that certain sites require are deliberately kept. A test fails the build if a new module inlines one (#320, #333).
- The container runs as uid 1000 rather than root, and CI checks it stays that way. Bind-mounted directories may need `chown -R 1000:1000`.
- Leaflet is pinned with subresource integrity, using the hashes published on leafletjs.com.
- The readme lost nine badges and the comparison table. Keeping accurate claims about four other projects is not a commitment worth making, and a table where one column is all green reads as advertising.

### Tests
- 326 to 387.

---

## [2.8.1] — 2026-09-07

### Security
- **A webhook could still be sent to a host that refused to resolve** — the guard checks every address a hostname resolves to and blocks private ones, but an unresolvable hostname fell through and the request went out anyway. That branch existed only so two delivery tests aiming at `hooks.example.com` would pass, which made the production behaviour a side effect of the tests. It leaves a rebinding window: answer `NXDOMAIN` while the check runs, resolve to an internal address by the time `requests` looks it up again. Any refusal from the resolver now stops the send, and the tests stub the resolver instead.
- **The container ran everything as root** — it now creates uid 1000 and drops to it. If you bind-mount `./results` from a directory owned by someone else, `chown -R 1000:1000` on the host. CI checks the image is unprivileged and can still write to all four data directories.
- **Leaflet was pulled from unpkg with no integrity attribute** — the map page trusted whatever the CDN served. Both the script and the stylesheet now carry the `sha256` hashes published on leafletjs.com, plus `crossorigin`.
- **numverify was called over plain HTTP** — the phone number and the API key travelled in the query string. It goes over HTTPS now, falling back to HTTP only when the free plan answers with error 105, which is the one case where the API itself refuses TLS.
- Secret scanning, push protection and Dependabot security updates are on for the repository. That surfaced nine advisories nobody had seen; five are closed by the dependency updates in this release.

### Added
- **RDAP module** (#306, by [@sOuL2000s](https://github.com/sOuL2000s)) — registration data over RDAP alongside WHOIS, discovering the server per TLD from the IANA bootstrap file and falling back to rdap.org. Returns registration dates, registrar, nameservers and contacts.
- **Keyboard shortcuts panel.**
- Tooltips on the standalone tool cards (#305).
- Multi-arch images on GHCR, built for `linux/amd64` and `linux/arm64` on every release tag.
- CodeQL on pushes, pull requests and weekly; a labeler; a greeting for first-time contributors; and stale handling for pull requests only, leaving issues alone.

### Fixed
- **RDAP reported `292` as the registrar** — jCard properties are `[name, params, type, value]`, so reading index 2 returned the type and every contact came back as `"text"`. The registrar was taken from the entity handle instead, which is the IANA registrar id rather than a name. The test fixture used a three-element vCard, which real RDAP never sends, so nothing caught it.
- **Every `.ru` domain looked unregistered** — a `404` from rdap.org was read as "not registered", but plenty of TLDs serve no RDAP at all. The zone is checked against the bootstrap map first and the module reports `skipped`.
- **A rate-limited request came back as a CORS error** — `add_middleware` wraps from the inside out, so CORS ended up innermost and anything short-circuited above it answered without the headers. The browser hid the `429` behind an opaque network failure. CORS is outermost now; proxy headers still run before the limiter, so the client IP behind a proxy is unchanged.
- **File work blocked the event loop in two routes** — the metadata endpoint copied the whole upload to a temp file inline, and clearing scans read every file in `scan_data` inline. Both stalled every other request while they ran, websocket scan progress included.
- The demo says plainly that AI analysis will not work there, on the page rather than only in the docs.

### Tests
- 326 → 343, covering the middleware order, the CORS headers on a rate-limited response, and each way the webhook resolver can refuse.

---

## [2.8.0] — 2026-09-02

### Fixed
- **Username search invented accounts** — most of the 50 sites were judged by HTTP status alone, so any site answering `200` for a name nobody registered was reported as a hit. Probing all of them with a nonexistent username caught ten doing exactly that: Pinterest, Spotify, Medium, 500px, Imgur, HackerRank, Kaggle, Trello, Duolingo and OnlyFans. Five of them returned a body byte-identical to a real profile's. A `200` now triggers one control request per site with a username that cannot exist, and the hit only stands if the target's page names the target while the control's page does not name the control. Sites that echo whatever name is in the URL can no longer produce a hit. Measured against 21 live sites, false positives went from ten to zero.
- **Twitch reported every username as found** — its text marker stopped appearing on the page. Markers are now cross-checked against the control response, and a marker missing from both is treated as stale, falling back to the name test.
- **A blocked site looked like an absent account** — `401`, `403`, `429` and `5xx` become `unknown` instead of `not_found`. A site that refused us tells us nothing about the account, and reporting that as absence was producing quiet false negatives.
- **The AI panel only ever tried one provider** — it picked one at import, so a configured Groq key sat unused while OpenRouter answered "Access denied by security policy". Every configured key is now a provider, tried in order until one returns a completion, each with its own model. When all fail, the response names each provider and its reason.
- **Shodan showed nothing without a paid key** — a free key gets `403` on the host endpoint and no key skipped the module outright. It now falls back to InternetDB, Shodan's keyless dataset, for ports, hostnames, tags, CPEs and CVEs. A paid key still goes to Shodan for organisation, location and banners. An invalid key is still an error rather than a silent downgrade.
- `host_info` requires an IP. It was interpolating whatever it was handed into the request path, and `validate_target` allows a slash through.

### Added
- **Ollama service in the compose file**, behind a profile so it stays out of the way. `docker compose --profile ollama up -d`, point `LLM_BASE_URL` at `http://ollama:11434/v1/chat/completions`, and the AI panel runs with nothing leaving the machine — which is the only fix when every hosted provider refuses the instance's region.
- A custom endpoint no longer needs a key: `LLM_BASE_URL` alone is enough, since Ollama has nothing to authenticate.
- `GROQ_MODEL`, and the `LLM_*` variables, documented in `.env.example` — it had none of them despite the README describing them since 2.6.0.

### Tests
- 285 → 326, covering the control-request detection, stale text markers, blocked-response handling, provider fallback, the Shodan fallback and its IP guard.

---

## [2.7.0] — 2026-09-01

### Added
- **Domain Exposure module (Lunar)** — how often a domain turns up in infostealer logs and breach data over a rolling year, split between staff and customers, with a monthly timeline and breakdowns by malware family, affected service and country. Needs no API key and returns aggregates only, but it is still a third party, so it is off unless `LUNAR_ENABLED` is set. Domain targets only; outbound requests honour `MODULE_PROXY`. Lunar builds a report on first request and caches it for a month, so a domain nobody has queried yet is reported as skipped rather than failed (#286).

### Security
- **Rate limits could be bypassed with a header** — `client_ip` read `X-Forwarded-For` and `X-Real-IP` whatever `TRUST_PROXY_HEADERS` was set to, and the limiter keys on its result. With no proxy in front, which is the default, a different header value per request landed in a fresh bucket every time, so `10/minute` on `/api/scan` and the `200/day` and `60/hour` ceilings meant nothing, and each scan bought fans out to dozens of third-party lookups. The headers are now read only when `TRUST_PROXY_HEADERS` is on. The daily scan quota was never affected: it keys on the API-key principal.
- **A username could redirect a lookup to another host** — Blackbird interpolated the username into its URL templates unescaped, and the Tumblr template carries the placeholder in the host position, so scanning `evil.com/#` sent the request to `evil.com`. `validate_target` rejects only ``[;|`$<>{}]``, so a slash or a hash reached the module untouched. Usernames are now percent-encoded before substitution.
- **A username could write outside `results/`** — Blackbird built its export filenames straight from the username, so `../../pwned` escaped the output directory. Names are now sanitised the way `maigret_wrapper` and `report_generator` already did.

### Fixed
- **JSON export failed on some usernames** — `user?name` raised `OSError` before writing anything and a name past the path limit raised `FileNotFoundError`, same root cause as the export path issue above.
- **A hanging maigret froze the scan** — the wrapper read output to EOF and then called `process.wait()`, neither with a timeout, so a maigret that stopped producing output blocked its worker for good and the scan neither finished nor reported an error. A watchdog now stops it after `MAIGRET_MAX_RUNTIME` seconds, 600 by default.
- **A failed Blackbird search looked like a clean one** — the API and CLI threw away what the module returned and read `bb.results`, storing `[]` for a search that raised, which reads the same as checking every site and finding nothing.

### Tests
- 249 → 285, covering the Lunar module, the maigret watchdog, the rate-limit key, hostile usernames in export paths, and host escapes in the username URL templates.

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
