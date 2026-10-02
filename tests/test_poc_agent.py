import os
import sys
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Add experiments/agent to path to import poc_agent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../experiments/agent')))
import poc_agent

def build_mock_response(tool_calls=None, content=""):
    mock_resp = MagicMock()
    mock_resp.ok = True
    
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
        
    mock_resp.json.return_value = {
        "choices": [{"message": msg}]
    }
    return mock_resp

def test_plan_mode(capsys):
    with patch("requests.post") as mock_post:
        mock_post.return_value = build_mock_response(content="I will run WHOIS.")
        
        with patch("config.LLM_API_KEY", "fake_key"):
            import asyncio
            asyncio.run(poc_agent.chat_with_agent("example.com", "domain", plan_only=True))
            
        output = capsys.readouterr().out
        assert "I will run WHOIS." in output
        
        # In plan mode, tools should not be sent
        call_kwargs = mock_post.call_args[1]
        assert "tools" not in call_kwargs["json"]

@patch("poc_agent.run_scan", new_callable=AsyncMock)
def test_enforce_target_and_module_budget(mock_run_scan, capsys):
    mock_run_scan.return_value = {"whois": {"data": "test"}}
    
    responses = [
        # Step 1: Pivot attempt
        build_mock_response([{
            "id": "call_1",
            "function": {
                "name": "run_prism_module",
                "arguments": json.dumps({
                    "reasoning": "checking pivot",
                    "current_knowledge_summary": "none",
                    "target": "pivot.com",
                    "target_type": "domain",
                    "module": "whois"
                })
            }
        }]),
        # Step 2: Valid call
        build_mock_response([{
            "id": "call_2",
            "function": {
                "name": "run_prism_module",
                "arguments": json.dumps({
                    "reasoning": "valid check",
                    "current_knowledge_summary": "blocked pivot",
                    "target": "example.com",
                    "target_type": "domain",
                    "module": "whois"
                })
            }
        }]),
    ]
    
    with patch("requests.post") as mock_post:
        mock_post.side_effect = responses + [build_mock_response()] * 10
        with patch("config.LLM_API_KEY", "fake_key"):
            import asyncio
            asyncio.run(poc_agent.chat_with_agent("example.com", "domain", plan_only=False))
            
    output = capsys.readouterr().out
    
    # Assert pivot block
    assert "Blocked pivot attempt to pivot.com" in output
    
    # Ensure run_scan was only called for the valid target
    mock_run_scan.assert_called_once_with("example.com", "domain", ["whois"])

@patch("poc_agent.run_scan", new_callable=AsyncMock)
def test_enforce_citations(mock_run_scan, capsys):
    mock_run_scan.return_value = {"whois": {"data": "test"}}
    
    # Step 1: run whois
    step_1 = build_mock_response([{
        "id": "call_1",
        "function": {
            "name": "run_prism_module",
            "arguments": json.dumps({
                "reasoning": "checking whois",
                "current_knowledge_summary": "start",
                "target": "example.com",
                "target_type": "domain",
                "module": "whois"
            })
        }
    }])
    
    # Step 2: submit answer with hallucinated module 'shodan'
    step_2 = build_mock_response([{
        "id": "call_2",
        "function": {
            "name": "submit_final_answer",
            "arguments": json.dumps({
                "claims": [
                    {"claim": "Domain is old", "module": "whois"},
                    {"claim": "Open port 80", "module": "shodan"} # Hallucinated
                ]
            })
        }
    }])
    
    with patch("requests.post") as mock_post:
        mock_post.side_effect = [step_1, step_2]
        with patch("config.LLM_API_KEY", "fake_key"):
            import asyncio
            asyncio.run(poc_agent.chat_with_agent("example.com", "domain", plan_only=False))
            
    output = capsys.readouterr().out
    
    # Claim from whois should be present
    assert "- Domain is old (Source: whois)" in output
    # Hallucinated claim should not be printed
    assert "- Open port 80" not in output
    # Warning about dropped claims should be present
    assert "Dropped 1 unbacked claim(s)." in output
