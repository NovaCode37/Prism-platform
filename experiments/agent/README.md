# PRISM Agent PoC

This directory contains a standalone Proof-of-Concept for an autonomous OSINT agent that wraps the existing PRISM modules in a ReAct loop.

## Constraints Respected
- **Standalone:** This is not integrated into `web/` or `cli.py`.
- **No Pivoting:** The agent is hard-restricted to only scan the initial target provided by the user. If it attempts to pivot, the script blocks the tool call.
- **Hard Step Limit:** Configured to a maximum of 5 loops (`MAX_STEPS`).
- **Citation Constraint:** The system prompt forces the LLM to cite which module provided which piece of data in its final answer, dropping unbacked claims.
- **Shared LLM Config:** Reuses `LLM_BASE_URL` and `LLM_API_KEY` from the existing project configuration.
- **Planning Mode:** A `--plan` mode exists to safely print what the LLM intends to do without actually executing scans.

## Usage

You must have the Prism API backend running locally (`http://localhost:8080/api/scan`).

### 1. Plan Mode (Safe)
Outputs the modules it would run without actually running them:
```bash
python poc_agent.py "getprism.su" --plan
```

### 2. Autonomous Scan Mode
Allows the agent to autonomously call the API up to `MAX_STEPS` times:
```bash
python poc_agent.py "getprism.su" --type domain
```
