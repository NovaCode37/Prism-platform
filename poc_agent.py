import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

# Fix Windows terminal encoding for emojis/arrows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables (mostly to grab an LLM API key if one exists)
load_dotenv()

PRISM_API_URL = "http://localhost:8080/api/scan"
# Use OpenAI, OpenRouter, or Groq
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

if not LLM_API_KEY:
    print("Please set LLM_API_KEY or OPENAI_API_KEY in your environment/ .env file.")
    exit(1)

def run_prism_module(target: str, target_type: str, module: str) -> dict:
    """
    Calls the local Prism API to run a specific module against a target.
    """
    print(f"\n[Agent Action] Running module '{module}' on '{target}' (type: {target_type})...")
    
    # 1. Start the scan
    payload = {
        "target": target,
        "scan_type": target_type,
        "modules": [module]
    }
    
    try:
        res = requests.post(PRISM_API_URL, json=payload, headers={"Content-Type": "application/json"})
        res.raise_for_status()
        scan_id = res.json()["scan_id"]
    except Exception as e:
        return {"error": f"Failed to start scan: {e}"}

    # 2. Poll for completion (simple blocking loop for the PoC)
    print(f"               Scan started (ID: {scan_id}). Waiting for results...")
    while True:
        status_res = requests.get(f"{PRISM_API_URL}/{scan_id}")
        if status_res.status_code == 200:
            data = status_res.json()
            if data["status"] in ["completed", "failed"]:
                # Extract just the data for the module we asked for to save tokens
                return data.get("results", {}).get(module, {"error": "Module returned no data"})
        time.sleep(2)


def chat_with_agent(prompt: str):
    """
    Core ReAct Loop: LLM -> Tool Call -> Execute -> LLM -> Final Answer
    """
    system_prompt = (
        "You are an autonomous OSINT investigation agent. You have access to a tool "
        "called 'run_prism_module' that can run specific OSINT scans against a target.\n"
        "Valid target_types: 'domain', 'ip', 'email', 'phone', 'username'.\n"
        "Valid modules: 'whois', 'dns', 'shodan', 'virustotal', 'abuseipdb', 'breaches', 'hlr', etc.\n"
        "Formulate a plan, run the necessary modules one by one, and provide a final comprehensive answer."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_prism_module",
                "description": "Run a specific OSINT module against a target via the Prism platform.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {"type": "string", "description": "Explain WHY you are running this module and what you hope to find."},
                        "target": {"type": "string", "description": "The target to scan (e.g., example.com, 1.1.1.1)"},
                        "target_type": {"type": "string", "description": "One of: domain, ip, email, phone, username"},
                        "module": {"type": "string", "description": "The Prism module to run (e.g., shodan, whois, dns, virustotal)"},
                    },
                    "required": ["reasoning", "target", "target_type", "module"]
                }
            }
        }
    ]

    print(f"\n[Agent Goal] {prompt}")

    while True:
        # Call the LLM
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto"
        }
        
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(LLM_BASE_URL, json=payload, headers=headers)
        if not response.ok:
            print(f"[API Error] {response.text}")
        response.raise_for_status()
        response_message = response.json()["choices"][0]["message"]
        
        # Append assistant message to history
        messages.append(response_message)

        # Check if LLM wants to call a tool
        if response_message.get("tool_calls"):
            for tool_call in response_message["tool_calls"]:
                args = json.loads(tool_call["function"]["arguments"])
                
                # Print the AI's Chain of Thought reasoning!
                print(f"\n[AI Reasoning] {args.get('reasoning', 'No reasoning provided.')}")
                
                # Execute the tool
                result = run_prism_module(args["target"], args["target_type"], args["module"])
                
                # Feed the result back to the LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "content": json.dumps(result)
                })
        else:
            # No tool calls means the LLM provided the final answer!
            print("\n[Agent Final Answer]")
            print(response_message["content"])
            break

if __name__ == "__main__":
    print("=== Prism Autonomous AI Agent PoC ===")
    goal = input("Enter an investigation goal (e.g., 'Find open ports on getprism.su'): ")
    chat_with_agent(goal)
