---
title: "How to Run a Full OSINT Recon on Any Domain in One Command (Self-Hosted)"
tags: osint, cybersecurity, selfhosted, python, security
---

If you've ever needed to profile a domain — subdomains, open ports, breached emails, DNS hygiene, TLS posture — you know the pain: a dozen separate tools, a dozen output formats, and a lot of copy-paste.

Here's how to do all of it in **one command**, fully self-hosted, with no data leaving your machine.

## The tool

[PRISM](https://github.com/NovaCode37/Prism-platform) is an open-source (MIT) OSINT platform. One target → 25+ modules run in parallel: WHOIS, DNS, certificate-transparency subdomains, Shodan, breach checks, dark-web mirrors, GeoIP, and more. It gives you an entity graph and an OPSEC exposure score at the end.

## 1. Get it running

Clone the repo and install:

```bash
git clone https://github.com/NovaCode37/Prism-platform
cd Prism-platform
pip install -r requirements.txt
```

Use it straight from the CLI:

```bash
python cli.py scan example.com
```

Or run the web UI in Docker (built from the repo):

```bash
docker build -t prism .
docker run -d -p 8080:8080 -e ALLOW_ANON_API=true prism
# open http://localhost:8080
```

## 2. Scan a domain

```bash
python cli.py scan example.com --type domain
```

In ~40 seconds you get, for `example.com`:

- **Subdomains** from certificate transparency logs
- **Open ports + CVEs** (via Shodan, if you add a key)
- **DNS records** and whether SPF/DMARC are missing (spoofing risk)
- **WHOIS** exposure (contact emails, org)
- **Archived sensitive URLs** from the Wayback Machine

## 3. Read the OPSEC score

Every scan ends with a 0–100 exposure score across four categories — Data Exposure, Identity OPSEC, Infrastructure, Web Security. Lower = more exposed. It's a quick way to triage which targets need attention.

> Tip: the score only reflects modules that actually ran — if you skip Shodan/VirusTotal, treat a high score as "less data," not "clean."

## 4. Export for reporting

```bash
python cli.py scan example.com --html -o report.html
```

HTML/PDF reports, plus CSV/Markdown/JSON, and a graph export to **GraphML/GEXF** for Gephi or Maltego.

## Why self-host it

No third party sees your targets. You bring your own API keys, set your own rate limits, and everything runs on your box. For anyone doing authorized recon, that's the whole point.

Repo: https://github.com/NovaCode37/Prism-platform
Live demo (no signup): https://getprism.su

*Built and maintained in the open — issues and PRs welcome.*
