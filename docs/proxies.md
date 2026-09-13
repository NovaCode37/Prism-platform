# Running PRISM Behind a Proxy

This guide explains how to configure PRISM to route outbound requests through a proxy server. This is useful for:

- **OSINT investigations** where you need to mask your source IP address
- **Corporate environments** that require all outbound traffic to go through a proxy
- **Geographic restrictions** when accessing region-locked services

## What `MODULE_PROXY` Does

The `MODULE_PROXY` environment variable configures a proxy for **all outbound HTTP/HTTPS requests** made by PRISM's modules (Shodan, VirusTotal, Censys, Hudson Rock, Lunar, etc.).

### What Traffic Is Covered

When `MODULE_PROXY` is set, the following traffic is routed through the proxy:

- ✅ All module API calls (Shodan, VirusTotal, Censys, AbuseIPDB, etc.)
- ✅ Hudson Rock infostealer queries
- ✅ Lunar domain exposure queries
- ✅ AI summary generation (if using `LLM_PROXY` for LLM requests)

### What Is NOT Covered

- ❌ **Maigret**: Runs as a subprocess and uses the host's network directly. To proxy Maigret traffic, route the entire container's egress at the network level.
- ❌ **Frontend build requests**: Next.js build-time requests are not proxied.
- ❌ **Health checks**: Local health check requests bypass the proxy.

## Supported Proxy Formats

PRISM supports the following proxy URL formats:

### HTTP/HTTPS Proxies

```
http://host:port
http://user:pass@host:port
https://host:port
https://user:pass@host:port
```

### SOCKS5 Proxies

```
socks5://host:port
socks5://user:pass@host:port
```

**Note**: SOCKS5 proxies require the `PySocks` package. The official Docker image does **not** include PySocks by default. If you need SOCKS5 support, you have two options:

1. **Use an HTTP/HTTPS proxy instead** (recommended)
2. **Build a custom image** with PySocks:
   ```dockerfile
   FROM novacode37/prism-platform:latest
   RUN pip install pysocks
   ```

## Configuration Examples

### Using Docker Run

#### Basic HTTP Proxy

```bash
docker run -d \
  -p 8080:8080 \
  -e MODULE_PROXY="http://proxy.example.com:8080" \
  -e API_KEYS="your-api-key" \
  -v ./results:/app/results \
  novacode37/prism-platform:latest
```

#### Authenticated Proxy

```bash
docker run -d \
  -p 8080:8080 \
  -e MODULE_PROXY="http://username:password@proxy.example.com:8080" \
  -e API_KEYS="your-api-key" \
  -v ./results:/app/results \
  novacode37/prism-platform:latest
```

#### With LLM Proxy (Separate from Module Proxy)

```bash
docker run -d \
  -p 8080:8080 \
  -e MODULE_PROXY="http://proxy.example.com:8080" \
  -e LLM_PROXY="http://llm-proxy.example.com:8080" \
  -e API_KEYS="your-api-key" \
  -e OPENROUTER_API_KEY="your-openrouter-key" \
  -v ./results:/app/results \
  novacode37/prism-platform:latest
```

### Using Docker Compose

Create or update your `.env` file:

```env
MODULE_PROXY=http://proxy.example.com:8080
API_KEYS=your-api-key
```

Then run:

```bash
docker compose up -d
```

Or specify the proxy inline:

```yaml
services:
  osint:
    build:
      context: .
    ports:
      - "8080:8080"
    environment:
      - MODULE_PROXY=http://proxy.example.com:8080
      - API_KEYS=${API_KEYS}
    volumes:
      - ./results:/app/results
    restart: unless-stopped
```

## Verifying the Proxy Is Working

Do not assume the proxy is working just because the variable is set. Here are methods to verify:

### Method 1: Use a Request Logging Proxy

Set up a local proxy that logs requests, such as [mitmproxy](https://mitmproxy.org/):

```bash
# Install mitmproxy
pip install mitmproxy

# Start mitmproxy (listens on port 8080)
mitmproxy --mode regular

# In another terminal, run PRISM pointing to mitmproxy
docker run -d \
  -p 8081:8080 \
  -e MODULE_PROXY="http://host.docker.internal:8080" \
  -e API_KEYS="test-key" \
  novacode37/prism-platform:latest
```

Now trigger a scan in PRISM. You should see the outbound requests appear in mitmproxy's interface.

### Method 2: Check External IP

If your proxy provides a different exit IP, verify by checking the IP seen by external services:

```bash
# Run a quick test with curl through the same proxy
curl -x http://proxy.example.com:8080 https://api.ipify.org
```

Compare this with your actual IP. They should differ if the proxy is working.

### Method 3: Module-Specific Testing

Run a scan against a known target and monitor your proxy's access logs:

```bash
# Example: Run a Shodan lookup
curl -H "X-API-Key: your-key" \
  "http://localhost:8080/api/modules/shodan?target=example.com"
```

Check your proxy server's logs for the outbound request to `api.shodan.io`.

## Separate LLM Proxy

If you need to route LLM (AI summary) requests through a different proxy than module requests, use `LLM_PROXY`:

```env
MODULE_PROXY=http://module-proxy.example.com:8080
LLM_PROXY=http://llm-proxy.example.com:8080
```

This is useful when:
- Your LLM provider requires a specific proxy
- You want to separate OSINT traffic from AI traffic for logging purposes
- Different network policies apply to different services

## Troubleshooting

### Modules Still Show My Real IP

1. **Verify the proxy URL format**: Ensure it includes the protocol (`http://` or `socks5://`)
2. **Check for typos**: Common mistakes include missing `@` in authenticated URLs
3. **Test connectivity**: Ensure the proxy is reachable from the container
4. **Maigret exception**: Remember that Maigret bypasses `MODULE_PROXY`

### Connection Errors

If modules fail with connection errors:

1. **Proxy authentication**: Verify username/password are correct and properly URL-encoded
2. **Firewall rules**: Ensure the container can reach the proxy host
3. **Proxy protocol mismatch**: Don't use `https://` for an HTTP proxy

### SOCKS5 Not Working

The official image does not include PySocks. Either:
1. Switch to an HTTP/HTTPS proxy
2. Build a custom image with `pip install pysocks`

## Related Documentation

- [README.md](../README.md) - Configuration reference including `MODULE_PROXY`
- [SECURITY.md](./SECURITY.md) - Security considerations and known limitations
- [Deployment Guide](./ARCHITECTURE.md) - Architecture and deployment patterns

## Quick Reference

| Variable | Purpose | Format Example |
|----------|---------|----------------|
| `MODULE_PROXY` | Proxy for all module API calls | `http://user:pass@proxy:8080` |
| `LLM_PROXY` | Proxy for LLM/AI requests only | `http://llm-proxy:8080` |
| `TRUST_PROXY_HEADERS` | Trust `X-Forwarded-*` from reverse proxies | `true` or `false` |

---

**Last updated**: 2026  
**Applies to**: PRISM Platform v2.9.0+
