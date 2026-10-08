# CLI Reference

PRISM provides a command-line interface (`cli.py`) for headlessly running scans, inspecting modules, and managing scheduled watchlists.

---

## `scan`

Run security scans against targets (domains, IPs, emails, phones, or usernames).

### Usage

```bash
python cli.py scan <target> [options]
```

### Options

* `--json`: Output results as raw JSON.
* `--html`: Generate an HTML scan report.
* `--pdf`: Generate a PDF scan report.
* `--graphml`: Export target entity graph in GraphML format.
* `--gexf`: Export target entity graph in GEXF format.
* `-m, --modules`: Specify comma-separated modules to execute. Modules are validated against the target type.
* `--verbose`: Output detailed execution logs.
* `--quiet`: Suppress output except critical errors.

### Example

```bash
python cli.py scan example.com --json
```

### Exit Codes

* `0`: Scan completed successfully with no issues.
* `1`: General runtime error or invalid parameters.
* `2`: Vulnerabilities detected above threshold.

### Skipped Modules Behavior

When a module requires an API key that is missing, it is skipped but still appears in the `--json` output with `status: skipped`:

```json
{
  "module": "shodan",
  "status": "skipped",
  "reason": "Missing API key"
}
```

---

## `modules`

List and query available OSINT modules.

### Usage

```bash
python cli.py modules [options]
```

### Options

* `--type <target_type>`: Print modules compatible with a target type (e.g., `domain`, `ip`, `email`, `phone`, `username`).

### Example

```bash
python cli.py modules --type domain
```

---

## `watchlist`

Manage background targets for scheduled periodic re-scanning.

### Usage

```bash
python cli.py watchlist <subcommand> [options]
```

### Subcommands

* `list`: Display current watched targets.
* `add <target>`: Add a target to the scheduled watchlist.
* `rm <target>`: Remove a target from the watchlist.
* `pause <target>`: Temporarily pause scheduled scans.
* `resume <target>`: Resume scheduled scans.

### Example

```bash
python cli.py watchlist add example.com
python cli.py watchlist list
```
