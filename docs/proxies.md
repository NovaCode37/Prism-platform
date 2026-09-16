# Running PRISM behind a proxy

PRISM can send module and LLM traffic through an HTTP or SOCKS proxy so OSINT lookups leave your network from a controlled egress.

## `MODULE_PROXY`

Set `MODULE_PROXY` to a proxy URL. Modules that call `get_proxies()` in `modules/__init__.py` pass that URL to `requests` for both `http` and `https` schemes.

**Covers:** outbound HTTP(S) from modules that use the shared helper (HudsonRock, Lunar, and the other module clients wired through `get_with_retry` / `get_proxies`).

**Also covers Maigret:** the wrapper passes `MODULE_PROXY` as `maigret --proxy` and sets `HTTP_PROXY` / `HTTPS_PROXY` so Maigret’s database updater (plain `requests`) uses the same egress.

**Does not cover:**

- **LLM / AI summary** — use `LLM_PROXY` for the model HTTP client, not `MODULE_PROXY`.
- Browser / extension traffic from your machine (only the PRISM server’s outbound calls).

### Supported URL forms

| Form | Example | Notes |
|------|---------|--------|
| HTTP | `http://host:8080` | Plain HTTP CONNECT / absolute-form proxying |
| HTTP + auth | `http://user:pass@host:8080` | Basic auth in the URL |
| HTTPS proxy | `https://host:8443` | Supported by `requests` when the proxy speaks TLS |
| SOCKS5 | `socks5://host:1080` | Needs PySocks (shipped via `requests[socks]` in `requirements.txt`) |
| SOCKS5 + auth | `socks5://user:pass@host:1080` | Same as above |

The Docker image installs `requirements.txt`, which pins `requests[socks]`, so SOCKS works in the published image without an extra package install. Unit tests in `tests/test_socks_proxy.py` assert both `http://` and `socks5://` `MODULE_PROXY` values route through a stub proxy.

### Docker example

```bash
docker run --rm -p 8080:8080 \
  -e MODULE_PROXY=http://user:pass@proxy.example:8080 \
  -e LLM_PROXY=socks5://127.0.0.1:1080 \
  ghcr.io/novacode37/prism-platform:latest
```

If the proxy is another container on a compose network:

```yaml
services:
  prism:
    image: ghcr.io/novacode37/prism-platform:latest
    environment:
      MODULE_PROXY: http://proxy:8080
      # LLM_PROXY: socks5://proxy:1080
    ports:
      - "8080:8080"
  # proxy:
  #   image: ...
```

### Confirming the proxy is used

Setting the variable alone is not proof of egress. Prefer one of:

1. **Logging proxy** — point `MODULE_PROXY` at a proxy that logs CONNECT / request lines; trigger a module lookup and confirm the target host appears in the proxy log.
2. **Local stub** — the patterns in `tests/test_socks_proxy.py` start a one-connection listener, set `MODULE_PROXY` to it, and assert the listener saw the request.
3. **Wrong port** — set `MODULE_PROXY` to a closed local port; module requests should fail quickly with a connection error instead of succeeding over the direct path.

## `LLM_PROXY`

Optional proxy only for the OpenAI-compatible LLM client (`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`). Same URL forms as above. Independent of `MODULE_PROXY` so you can split OSINT egress from model egress.

## Reverse proxy (inbound)

That is different: `TRUST_PROXY_HEADERS` and `FORWARDED_ALLOW_IPS` control how PRISM trusts `X-Forwarded-*` when **clients** reach PRISM through nginx/Caddy. See [SECURITY.md](../SECURITY.md). Do not confuse inbound reverse-proxy headers with outbound `MODULE_PROXY`.

## See also

- Configuration table in [README.md](../README.md)
- [SECURITY.md](../SECURITY.md) — rate limits and trusted proxy headers
