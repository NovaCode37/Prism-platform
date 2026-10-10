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

- `--json`: Output results as raw JSON.

- `--html`: Generate an HTML scan report.

- `--pdf`: Generate a PDF scan report.

- `--graphml`: Export target entity graph in GraphML format.

- `--gexf`: Export target entity graph in GEXF format.

- `-t, --type <target_type>`: Specify target type (auto-detected if omitted).

- `-m, --modules`: Specify comma-separated modules to execute. Modules are validated against the target type.

- `-v, --verbose`: Output detailed execution logs.

- `-q, --quiet`: Suppress output except critical errors.

- `-o, --output <base_name>`: Write output to file(s). With more than one format flag, each file gets its own proper extension from the base name (e.g., `-o out --json --html` writes `out.json` and `out.html`).

### Example
```bash
python cli.py scan example.com --json --html -o report
```
### Exit Codes
- `0`: Scan completed successfully.

- `1`: General runtime/scan error or interrupted by `Ctrl+C`.

- `2`: Unknown module name passed to `-m` (argparse also uses `2` for bad arguments).

### Skipped Modules Behavior
When a module is skipped (e.g., missing API key), results are keyed by module name containing `status`, `status_reason`, and other fields:

```json
{
  "shodan": {
    "status": "skipped",
    "status_reason": "Missing API key",
    "error": null
  }
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
- `-t, --type <target_type>`: Print modules compatible with a target type (e.g., `domain`, `ip`, `email`, `phone`, `username`).

- `--json`: Output available modules as raw JSON.

### Example
```bash
python cli.py modules --type domain --json
```
---
## `watchlist`
Manage background targets for scheduled periodic re-scanning.

### Usage

```bash
python cli.py watchlist <subcommand> [options]
```
### Subcommands
- `list`: Display current watched targets (`--json` supported).

- `add <target>`: Add a target to the scheduled watchlist. Supports `-t/--type`, `-m`, `--interval` (hours, default 24), and `--webhook`.

- `rm <entry_id>`: Remove a target from the watchlist by its entry ID.

- `pause <entry_id>`: Temporarily pause scheduled scans by entry ID.

- `resume <entry_id>`: Resume scheduled scans by entry ID.

### Example
```bash
python cli.py watchlist add example.com --interval 12 --webhook https://example.com/hook
python cli.py watchlist list --json
```
