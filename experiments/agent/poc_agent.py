import os
import sys

# Add root project dir to python path so we can import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config  # Reusing PRISM's config loader which calls dotenv

import time
import json
import argparse
import requests

# Fix Windows terminal encoding for emojis/arrows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

PRISM_API_URL = "http://localhost:8080/api/scan"
# Use existing LLM setup from the environment (as requested)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
MAX_STEPS = 5

if not LLM_API_KEY:
    print("Please set LLM_API_KEY or OPENAI_API_KEY in your .env file.")
    exit(1)

def run_prism_module(target: str, target_type: str, module: str) -> dict:
    """Calls the local Prism API to run a specific module against a target."""
    print(f"\n[Agent Action] Running module '{module}' on '{target}' (type: {target_type})...")
    
    payload = {"target": target, "scan_type": target_type, "modules": [module]}
    try:
        res = requests.post(PRISM_API_URL, json=payload, headers={"Content-Type": "application/json"})
        if not res.ok:
            return {"error": f"API Error: {res.text}"}
        scan_id = res.json()["scan_id"]
    except Exception as e:
        return {"error": f"Failed to start scan: {e}"}

    print(f"               Scan started (ID: {scan_id}). Waiting for results...")
    while True:
        try:
            status_res = requests.get(f"{PRISM_API_URL}/{scan_id}")
            if status_res.status_code == 200:
                data = status_res.json()
                if data["status"] in ["completed", "failed"]:
                    return data.get("results", {}).get(module, {"error": "Module returned no data"})
        except Exception:
            pass
        time.sleep(2)

def chat_with_agent(target: str, target_type: str, plan_only: bool = False):
    """Core ReAct Loop with constraints."""
    
    system_prompt = f"""You are an autonomous OSINT investigation agent for the PRISM platform.
Your ONLY target is: {target} (Type: {target_type}).

CRITICAL CONSTRAINTS:
1. ONLY analyze the exact target provided. You MUST NOT pivot to other domains, IPs, emails, or usernames you find along the way. If a lead looks worth following, suggest it to the user in the final answer, but do NOT run modules on it.
2. Every claim in your final answer MUST cite the specific module result it came from. Anything you cannot back with a result MUST be dropped. Do not hallucinate.
3. You have a maximum of {MAX_STEPS} steps.
"""
    
    if plan_only:
        system_prompt += "\nMODE: --plan is enabled. Do not call any tools. Just print a step-by-step plan of which modules you WOULD run and why."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Investigate {target}. Discover as much info as possible using available modules (e.g. dns, shodan, whois)."}
    ]

    tools = [{
        "type": "function",
        "function": {
            "name": "run_prism_module",
            "description": "Run a specific PRISM OSINT module against the target.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string", "description": "Explain WHY you are running this module and what you hope to find."},
                    "current_knowledge_summary": {"type": "string", "description": "ANTI-LOST-IN-MIDDLE: Summarize everything you have learned about the target so far. You must update this with every step."},
                    "target": {"type": "string", "description": f"MUST BE EXACTLY: {target}"},
                    "target_type": {"type": "string", "description": f"MUST BE EXACTLY: {target_type}"},
                    "module": {"type": "string", "description": "The Prism module to run (e.g., shodan, whois, dns, breaches)"},
                },
                "required": ["reasoning", "current_knowledge_summary", "target", "target_type", "module"]
            }
        }
    }]

    print(f"\n[Agent Target] {target}")
    step_count = 0

    while step_count < MAX_STEPS:
        step_count += 1
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "tools": tools if not plan_only else None
        }
        
        headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
        response = requests.post(LLM_BASE_URL, json=payload, headers=headers)
        
        if not response.ok:
            print(f"[API Error] {response.text}")
            break
            
        response_message = response.json()["choices"][0]["message"]
        messages.append(response_message)

        if response_message.get("tool_calls") and not plan_only:
            for tool_call in response_message["tool_calls"]:
                args = json.loads(tool_call["function"]["arguments"])
                print(f"\n[Step {step_count}/{MAX_STEPS} Knowledge State] {args.get('current_knowledge_summary', 'None')}")
                print(f"[Step {step_count}/{MAX_STEPS} Reasoning] {args.get('reasoning', '')}")
                
                if args["target"] != target:
                    result = {"error": f"Constraint Violation: You are only allowed to scan {target}."}
                    print(f"[Agent Action] Blocked pivot attempt to {args['target']}")
                else:
                    result = run_prism_module(args["target"], args["target_type"], args["module"])
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "content": json.dumps(result)[:2000] # Truncate to save context
                })
        else:
            print(f"\n[Agent Final Answer]\n{response_message.get('content', '')}")
            break

    if step_count >= MAX_STEPS:
        print(f"\n[Agent Final Answer]\nReached maximum step limit ({MAX_STEPS}). Terminating early.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PRISM Autonomous Agent PoC")
    parser.add_argument("target", help="The target to investigate (e.g. getprism.su)")
    parser.add_argument("--type", default="domain", help="Target type (domain, ip, email)")
    parser.add_argument("--plan", action="store_true", help="Print plan without running modules")
    
    args = parser.parse_args()
    chat_with_agent(args.target, args.type, plan_only=args.plan)
