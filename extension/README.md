# PRISM browser extension

One-click OSINT scans from your browser. Select a domain, IP, email, phone, or
username on any page, right-click, and scan it with your PRISM instance — the scan
runs and the results show up right inside the extension popup. No redirect, nothing
leaves your setup.

Available in all 9 PRISM languages; it follows your browser's language.

## Features

- Right-click any selected text → **Scan with PRISM**
- Or open the popup and type a target
- Live progress, OPSEC score, findings, and per-module results in the popup
- Points at your own self-hosted PRISM (or the public demo)
- Optional API key for instances behind auth

## Install

**Firefox** — install it from
[Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/prism-osint/).

**Chrome / Edge / Opera / Brave** — grab `prism-extension-chromium-*.zip` from the
[latest release](https://github.com/NovaCode37/Prism-platform/releases), unzip it,
then go to `chrome://extensions`, enable **Developer mode**, and use **Load unpacked**
on the unzipped folder.

Either way, open the popup afterwards and set **Server** to your PRISM URL
(e.g. `http://localhost:8080`). Leave it at the default to use the public demo.

### Running from source

Firefox: `about:debugging` → **This Firefox** → **Load Temporary Add-on** → pick
`manifest.json` in this folder. Chromium: **Load unpacked** on this folder directly.

## Build a package

`scripts/build_extension.py` builds a store-ready zip for each target into `dist/`:

```bash
python scripts/build_extension.py            # both
python scripts/build_extension.py chromium   # just one
```

The two builds share this folder as their source; the script only adjusts the
manifest per target. The Chromium build drops `browser_specific_settings` (Firefox
only) and the `background.scripts` fallback, since Chromium uses `service_worker`
and warns on keys it doesn't know.

## Notes

- Requires PRISM **2.6+** on the target instance (the `?target=` and API flow).
- `host_permissions` is broad so the extension can reach any instance URL you set;
  it only ever talks to the server you configure.
