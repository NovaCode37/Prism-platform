# Contributing to PRISM

Thanks for your interest in contributing! This document explains how to get started.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/<NovaCode37>/Prism-platform.git
   cd Prism-platform
   ```
3. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/my-feature
   ```

## Development Setup

### Backend

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

pip install -r requirements.txt
cp .env.example .env       # add API keys (optional)
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — it proxies API requests to `localhost:8080`.

## Project Structure

- `modules/` — OSINT scan modules (each module is a standalone class)
- `web/app.py` — FastAPI backend with WebSocket scan engine
- `web/security.py` — Auth, rate limiting, input validation
- `frontend/src/` — Next.js 14 + TypeScript + Tailwind CSS
- `tests/` — pytest test suite

## Adding a New Module

1. Create `modules/your_module.py` with a class that has a main method returning `Dict[str, Any]`
2. Add the module call to the scan pipeline in `web/app.py` (inside `_run_scan`)
3. Add a display card in `frontend/src/components/views/ScanResults.tsx`
4. Write tests in `tests/test_modules.py`

**Module template:**

```python
import requests
from typing import Dict, Any

class YourModule:
    def run(self, target: str) -> Dict[str, Any]:
        result = {"target": target, "data": None, "error": None}
        try:
            # your logic here
            result["data"] = {"key": "value"}
        except Exception as e:
            result["error"] = str(e)
        return result
```

## Code Style

- **Python** — PEP 8, type hints with `typing` module (`Dict`, `List`, etc. for Python 3.8+ compat)
- **TypeScript** — standard Next.js/React conventions
- No trailing whitespace on blank lines
- Two blank lines between top-level definitions, one blank line between methods
- No unnecessary comments — code should be self-explanatory

## Running Tests

```bash
pytest tests/ -v --cov=modules --cov-report=term-missing
```

All new modules should include tests. Use `monkeypatch` to mock external API calls.

## Pull Request Process

1. Make sure tests pass: `pytest tests/ -v`
2. Keep commits focused — one feature or fix per PR
3. Write a clear PR description explaining **what** and **why**
4. Link related issues if applicable

## Reporting Issues

Open an issue on GitHub with:
- Steps to reproduce
- Expected vs actual behavior
- Python/Node versions and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
