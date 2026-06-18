# Security Policy

PRISM is a self-hosted OSINT platform. Even though every scan it performs is **passive**, the platform itself processes user inputs, talks to many third-party APIs, and exposes a public-facing dashboard. I take its security posture seriously.

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 2.3.x   | Active support     |
| 2.2.x   | Security fixes only |
| < 2.2   | Unsupported        |

Please upgrade to the latest `2.3.x` release before reporting any issue.

## Reporting a Vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

- Email: `entropq2@gmail.com` (preferred)
- Or: open a private security advisory via GitHub →
  `Security` → `Report a vulnerability`

Include in your report:

1. A clear description of the issue and impact.
2. Steps to reproduce (or a minimal proof-of-concept).
3. Affected version / commit hash.
4. Your assessment of severity (low / medium / high / critical) and any suggested mitigation.

I aim to:

- Acknowledge new reports within **72 hours**.
- Provide an initial assessment within **7 days**.
- Ship a fix or mitigation for confirmed issues within **30 days** for high/critical severity.

If you'd like credit in the changelog, mention how you'd like to be attributed (name, handle, link).

## Scope

In scope:

- The PRISM backend (`web/app.py`, `web/security.py`, scan modules under `modules/`).
- The PRISM frontend (`frontend/`).
- Default Docker / docker-compose deployment artifacts.
- Webhook delivery and signing.

Out of scope:

- Vulnerabilities in third-party services PRISM consults (Shodan, VirusTotal, Censys, etc.) — please report those upstream.
- Issues that require a maliciously modified deployment (e.g. attacker-controlled `.env`).
- Theoretical issues without a working PoC.
- Rate-limiting or DoS that requires sustained traffic from a privileged network position.

## Hardening defaults (since v2.2)

PRISM ships with the following defaults to reduce attack surface:

- **Header-only API auth** — `X-API-Key` or `Authorization: Bearer …`. Query-string keys are **rejected**.
- **No anonymous access by default** — without configured `API_KEYS`, the API responds with `503` unless `ALLOW_ANON_API=true` is explicitly set.
- **Strict CORS** — `ALLOWED_ORIGINS` must be explicitly listed; wildcard is not enabled by default.
- **Per-principal scan isolation** — each scan is owned by a principal derived from the API key; cross-principal reads return `404`.
- **SSRF guards** on:
  - `validate_url_not_private` for user-supplied URLs.
  - `_resolve_all_public` for webhook callback hosts (rejects private/loopback/reserved/link-local/multicast/unspecified addresses).
- **HMAC-signed webhooks** when `WEBHOOK_SECRET` is set (`X-Prism-Secret` header).
- **Security response headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`.
- **Rate limiting** — global defaults `200/day, 60/hour` and per-route limits via `slowapi`.
- **Trusted proxy headers are opt-in** — `TRUST_PROXY_HEADERS=true` only trusts `X-Forwarded-*` values from `FORWARDED_ALLOW_IPS`.
- **Input validation** — target length cap, forbidden shell metacharacters in `validate_target`, UUID format check on scan IDs.
- **Optional `DISABLE_DOCS=true`** to hide `/docs`, `/redoc`, `/openapi.json` in production.

## Recommended deployment hardening

For production deployments I recommend:

1. Generate strong, unique values for `API_KEYS` (multiple tenants → comma-separated).
2. Set `ALLOWED_ORIGINS` to the exact frontend origin(s).
3. Set `WEBHOOK_SECRET` and validate the `X-Prism-Secret` header on the receiving side.
4. Set `DISABLE_DOCS=true`.
5. Run behind a reverse proxy (nginx, Caddy, Cloudflare) terminating TLS.
6. Set `TRUST_PROXY_HEADERS=true` only when PRISM is not directly reachable, and restrict `FORWARDED_ALLOW_IPS` to the reverse proxy source IPs.
7. Set `TRUSTED_HOSTS` to the public hostname(s) accepted by the backend.
8. Treat `PRISM_UI_API_KEY` as public browser configuration; do not use a server-only secret for it.
9. Restrict outbound network egress where possible (PRISM does call many third-party APIs).
10. Mount `scan_data/` and `module_cache/` on persistent, access-controlled storage.
11. Keep your Docker images updated and run `pytest -q` after every dependency upgrade.

## Legal use

PRISM is for **lawful, authorized** OSINT only. See the *Legal Notice* in [README.md](README.md). Reports about the platform being misused for unauthorized surveillance, harassment, or doxxing are welcome and I will act on them.
