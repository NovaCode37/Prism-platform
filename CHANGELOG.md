# Changelog

All notable changes to PRISM are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
