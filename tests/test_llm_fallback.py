import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import web.app as app_mod

PAYLOAD = {"messages": [{"role": "user", "content": "hi"}]}


def _reset(monkeypatch, custom="", openrouter="", groq=""):
    monkeypatch.setattr(app_mod, "OPENROUTER_API_KEY", openrouter)
    monkeypatch.setattr(app_mod, "GROQ_API_KEY", groq)
    for name in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "GROQ_MODEL"):
        monkeypatch.delenv(name, raising=False)
    if custom:
        monkeypatch.setenv("LLM_API_KEY", custom)


def _answers(mapping):
    def fake(provider, payload):
        return mapping[provider["name"]]
    return fake


def test_no_providers_configured(monkeypatch):
    _reset(monkeypatch)
    assert app_mod.llm_providers() == []
    out = app_mod._llm_complete(PAYLOAD)
    assert "No LLM provider configured" in out["error"]


def test_a_keyless_local_endpoint_is_enough(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("LLM_BASE_URL", "http://ollama:11434/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5:3b")
    providers = app_mod.llm_providers()
    assert [p["name"] for p in providers] == ["custom"]
    assert providers[0]["url"] == "http://ollama:11434/v1/chat/completions"
    assert providers[0]["model"] == "qwen2.5:3b"


def test_provider_order_puts_custom_first(monkeypatch):
    _reset(monkeypatch, custom="c", openrouter="o", groq="g")
    assert [p["name"] for p in app_mod.llm_providers()] == ["custom", "openrouter", "groq"]


def test_the_same_key_is_not_listed_twice(monkeypatch):
    _reset(monkeypatch, custom="same", openrouter="same", groq="g")
    assert [p["name"] for p in app_mod.llm_providers()] == ["custom", "groq"]


def test_falls_back_to_the_next_provider(monkeypatch):
    _reset(monkeypatch, openrouter="o", groq="g")
    monkeypatch.setattr(app_mod, "_call_llm", _answers({
        "openrouter": {"error": {"message": "Access denied by security policy."}},
        "groq": {"choices": [{"message": {"content": "answer"}}], "model": "llama"},
    }))
    out = app_mod._llm_complete(PAYLOAD)
    assert out["text"] == "answer"
    assert out["provider"] == "groq"


def test_first_provider_wins_when_it_works(monkeypatch):
    _reset(monkeypatch, openrouter="o", groq="g")
    called = []

    def fake(provider, payload):
        called.append(provider["name"])
        return {"choices": [{"message": {"content": "ok"}}]}
    monkeypatch.setattr(app_mod, "_call_llm", fake)
    app_mod._llm_complete(PAYLOAD)
    assert called == ["openrouter"]


def test_every_provider_failing_reports_each_one(monkeypatch):
    _reset(monkeypatch, openrouter="o", groq="g")
    monkeypatch.setattr(app_mod, "_call_llm", _answers({
        "openrouter": {"error": {"message": "Access denied by security policy."}},
        "groq": {"error": {"message": "rate limit reached"}},
    }))
    out = app_mod._llm_complete(PAYLOAD)
    assert "tried" in out
    assert len(out["tried"]) == 2
    assert "openrouter" in out["error"] and "groq" in out["error"]
    assert "datacentre" in out["error"]


def test_single_provider_failure_stays_readable(monkeypatch):
    _reset(monkeypatch, groq="g")
    monkeypatch.setattr(app_mod, "_call_llm", _answers({
        "groq": {"error": {"message": "invalid api key"}},
    }))
    out = app_mod._llm_complete(PAYLOAD)
    assert out["error"] == "invalid api key"


def test_missing_choices_counts_as_a_failure(monkeypatch):
    _reset(monkeypatch, openrouter="o", groq="g")
    monkeypatch.setattr(app_mod, "_call_llm", _answers({
        "openrouter": {"id": "x"},
        "groq": {"choices": [{"message": {"content": "second"}}]},
    }))
    assert app_mod._llm_complete(PAYLOAD)["text"] == "second"


@pytest.mark.parametrize("message,blocked", [
    ("Access denied by security policy.", True),
    ("Model unavailable in your region", True),
    ("cloudflare challenge", True),
    ("invalid api key", False),
    ("context length exceeded", False),
])
def test_geo_block_detection(message, blocked):
    assert app_mod._looks_geo_blocked(message) is blocked


def test_each_provider_is_asked_with_its_own_model(monkeypatch):
    _reset(monkeypatch, openrouter="o", groq="g")
    seen = {}

    def fake(provider, payload):
        seen[provider["name"]] = provider["model"]
        return {"error": "nope"}
    monkeypatch.setattr(app_mod, "_call_llm", fake)
    app_mod._llm_complete(PAYLOAD)
    assert seen["groq"] == "llama-3.1-8b-instant"
    assert seen["openrouter"] != seen["groq"]
