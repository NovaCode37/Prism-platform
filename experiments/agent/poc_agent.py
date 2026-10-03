import os
import sys
import json
import argparse
import requests
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config  

from cli import run_scan, MODULES_BY_TARGET_TYPE

MAX_STEPS = 5
MAX_MODULES = 10

def summarize_result(data, max_list_size=5):
    if isinstance(data, dict):
        return {k: summarize_result(v, max_list_size) for k, v in data.items()}
    elif isinstance(data, list):
        if len(data) > max_list_size:
            return [summarize_result(v, max_list_size) for v in data[:max_list_size]] + [f"... ({len(data) - max_list_size} more items truncated)"]
        return [summarize_result(v, max_list_size) for v in data]
    return data

async def chat_with_agent(target: str, target_type: str, plan_only: bool = False):
    if not config.LLM_API_KEY and not plan_only:
        print("Please configure your LLM provider keys in the environment.")
        return

    system_prompt = f"""You are an autonomous OSINT investigation agent for the PRISM platform.
Your ONLY target is: {target} (Type: {target_type}).

CRITICAL CONSTRAINTS:
1. ONLY analyze the exact target provided. You MUST NOT pivot to other domains, IPs, emails, or usernames you find along the way. If a lead looks worth following, suggest it to the user in the final answer, but do NOT run modules on it.
2. Every claim in your final answer MUST cite the specific module result it came from. Anything you cannot back with a result MUST be dropped.
3. You have a maximum of {MAX_STEPS} steps and a maximum budget of {MAX_MODULES} modules.
4. Output your final answer using the submit_final_answer tool.
"""

    if plan_only:
        system_prompt += "\nMODE: --plan is enabled. Do not call any tools. Just print a step-by-step plan of which modules you WOULD run and why."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Investigate {target}. Discover as much info as possible using available modules."}
    ]

    tools = [{
        "type": "function",
        "function": {
            "name": "run_prism_module",
            "description": "Run a specific PRISM OSINT module against the target.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string"},
                    "current_knowledge_summary": {"type": "string"},
                    "target": {"type": "string"},
                    "target_type": {"type": "string"},
                    "module": {"type": "string"}
                },
                "required": ["reasoning", "current_knowledge_summary", "target", "target_type", "module"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_final_answer",
            "description": "Submit your final OSINT investigation report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "claim": {"type": "string", "description": "The factual claim being made."},
                                "module": {"type": "string", "description": "The exact name of the module this claim comes from."}
                            },
                            "required": ["claim", "module"]
                        }
                    }
                },
                "required": ["claims"]
            }
        }
    }]

    print(f"\n[Agent Target] {target}")
    step_count = 0
    modules_run = 0
    executed_modules = set()

    while step_count < MAX_STEPS:
        step_count += 1
        payload = {
            "model": config.LLM_MODEL,
            "messages": messages,
        }
        if not plan_only:
            payload["tools"] = tools
        
        headers = {"Authorization": f"Bearer {config.LLM_API_KEY}", "Content-Type": "application/json"}
        try:
            response = await asyncio.to_thread(
                requests.post,
                config.LLM_BASE_URL, 
                json=payload, 
                headers=headers, 
                proxies=config.LLM_PROXIES, 
                timeout=config.LLM_TIMEOUT
            )
        except requests.exceptions.RequestException as e:
            print(f"[Network Error] Could not connect to LLM provider: {e}")
            break

        if not response.ok:
            print(f"[API Error] {response.text}")
            break
            
        response_message = response.json()["choices"][0]["message"]
        messages.append(response_message)

        if response_message.get("tool_calls") and not plan_only:
            for tool_call in response_message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                
                if tool_name == "submit_final_answer":
                    claims = args.get("claims", [])
                    print("\n[Agent Final Answer]")
                    dropped_count = 0
                    for c in claims:
                        if c["module"] in executed_modules:
                            print(f"- {c['claim']} (Source: {c['module']})")
                        else:
                            dropped_count += 1
                    
                    if dropped_count > 0:
                        print(f"\n[Validation] Dropped {dropped_count} unbacked claim(s).")
                    return

                print(f"\n[Step {step_count}/{MAX_STEPS} Knowledge State] {args.get('current_knowledge_summary', 'None')}")
                print(f"[Step {step_count}/{MAX_STEPS} Reasoning] {args.get('reasoning', '')}")
                
                if args.get("target") != target:
                    result = {"error": f"Constraint Violation: You are only allowed to scan {target}."}
                    print(f"[Agent Action] Blocked pivot attempt to {args.get('target')}")
                else:
                    module_name = args.get("module")
                    valid_modules = MODULES_BY_TARGET_TYPE.get(target_type, ())
                    if module_name not in valid_modules:
                        result = {"error": f"Invalid module '{module_name}' for target_type '{target_type}'. Valid: {list(valid_modules)}"}
                    elif modules_run >= MAX_MODULES:
                        result = {"error": f"Module budget exceeded ({MAX_MODULES}). Submit final answer."}
                    else:
                        modules_run += 1
                        executed_modules.add(module_name)
                        try:
                            scan_result = await run_scan(target, target_type, [module_name])
                            result = scan_result.get(module_name, {"error": "Module returned no data"})
                        except Exception as e:
                            result = {"error": f"Module execution failed: {e}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": json.dumps(summarize_result(result))[:15000]
                })
        else:
            if plan_only:
                print(f"\n[Agent Plan]\n{response_message.get('content', '')}")
            else:
                print(f"\n[Agent Output]\n{response_message.get('content', '')}")
            break

    if step_count >= MAX_STEPS:
        print(f"\n[Agent Final Answer]\nReached maximum step limit ({MAX_STEPS}). Terminating early.")

def main():
    parser = argparse.ArgumentParser(description="PRISM Autonomous Agent PoC")
    parser.add_argument("target", help="The target to investigate")
    parser.add_argument("--type", default="domain", help="Target type")
    parser.add_argument("--plan", action="store_true", help="Print plan without running modules")
    args = parser.parse_args()
    asyncio.run(chat_with_agent(args.target, args.type, plan_only=args.plan))

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    main()
