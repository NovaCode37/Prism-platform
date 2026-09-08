# Security Policy

PRISM performs only passive lookups, but the platform itself takes user input, talks to a couple of dozen third-party APIs, and serves a dashboard that people put on the public internet. Reports about any of that are welcome.

## Supported versions

| Version | Supported |
|---------|-----------|
| 2.8.x   | Yes |
| 2.7.x   | Security fixes only |
| < 2.7   | No |

This is a one-person project, so support means the latest minor plus the one before it. Please reproduce on the current release before reporting.

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

- Email `entropq2@gmail.com`, or
- Open a private advisory: `Security` tab, then `Report a vulnerability`

Useful to include:

1. What the issue is and what an attacker gets out of it.
2. Steps to reproduce, or a minimal proof of concept.
3. Version or commit hash.
4. Your own read on severity, and a suggested fix if you have one.

What to expect back: I read reports within a week and reply with an assessment once I have reproduced it. Fixes for anything high or critical go out as soon as they are ready, usually within a couple of weeks. I would rather say that than promise a number I cannot keep. If a report has gone quiet for more than two weeks, send a reminder.

Tell me how you want to be credited in the changelog, or say if you would rather not be.

## Scope

In scope:

- Backend: `web/app.py`, `web/security.py`, the modules under `modules/`
- Frontend under `frontend/`
- The browser extension under `extension/`
- Docker and docker-compose deployment artefacts
- Webhook delivery and signing

Out of scope:

- Bugs in the third-party services PRISM queries (Shodan, VirusTotal, Censys and the rest). Report those upstream.
- Anything that needs a maliciously modified deployment, such as an attacker-controlled `.env`.
- Findings with no working proof of concept.
- Denial of service that needs sustained traffic or a privileged network position.

## Defaults

PRISM ships with these on:

- **Header-only API auth.** `X-API-Key` or `Authorization: Bearer`. Keys in the query string are rejected.
- **No anonymous access.** With no `API_KEYS` configured the API answers `503` unless `ALLOW_ANON_API=true` is set deliberately.
- **CORS closed by default.** `ALLOWED_ORIGINS` has to list origins explicitly. There is no wildcard fallback.
- **Per-principal scan isolation.** A scan belongs to the principal derived from the API key, and reads across principals return `404`.
- **SSRF guards.** `validate_url_not_private` for user-supplied URLs, `_resolve_all_public` for webhook hosts. The webhook guard checks every address a hostname resolves to and refuses to send if any of them is private, or if the name does not resolve at all.
- **HMAC-signed webhooks** when `WEBHOOK_SECRET` is set, in `X-Prism-Secret`.
- **Response headers.** `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`.
- **Rate limiting.** `200/day` and `60/hour` globally, tighter per route, via slowapi. Keyed on the peer address unless proxy headers are explicitly trusted.
- **Proxy headers off by default.** `TRUST_PROXY_HEADERS=true` trusts `X-Forwarded-*` only from the addresses in `FORWARDED_ALLOW_IPS`.
- **Input validation.** Length cap and shell metacharacter rejection in `validate_target`, UUID check on scan IDs.
- **Non-root container.** The image runs as uid 1000. CI fails if that stops being true.
- **`DISABLE_DOCS=true`** hides `/docs`, `/redoc` and `/openapi.json`.

## Known limitations

- **`MODULE_PROXY` reaches 2 of the 22 modules that make outbound requests.** If you set it expecting every lookup to leave through the proxy, twenty of them still go out directly from the host. Tracked in [#324](https://github.com/NovaCode37/Prism-platform/issues/324). Until that lands, route the whole container's egress if the source address matters to you.
- Maigret runs as a subprocess and inherits the host's network the same way.

## Deployment

For anything reachable from outside your machine:

1. Generate long random values for `API_KEYS`. Comma-separate them for multiple tenants.
2. Set `ALLOWED_ORIGINS` to the exact frontend origins.
3. Set `WEBHOOK_SECRET` and check `X-Prism-Secret` on the receiving end.
4. Set `DISABLE_DOCS=true`.
5. Put it behind a reverse proxy that terminates TLS.
6. Set `TRUST_PROXY_HEADERS=true` only when PRISM is not directly reachable, and pin `FORWARDED_ALLOW_IPS` to the proxy.
7. Set `TRUSTED_HOSTS` to the hostnames the backend should answer on.
8. Treat `PRISM_UI_API_KEY` as public. It ships to the browser, so never put a server-side secret there.
9. Restrict outbound egress where you can. PRISM calls a lot of third parties.
10. Put `scan_data/` and `module_cache/` on storage you control. If you bind-mount them, `chown -R 1000:1000` so the non-root container can write.
11. Update the image and run `pytest -q` after dependency upgrades.

## Legal use

PRISM is for lawful, authorised OSINT. See the legal notice in [README.md](README.md). If you find the platform being used for surveillance, harassment or doxxing, tell me and I will act on it.
