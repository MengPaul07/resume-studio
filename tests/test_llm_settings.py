from __future__ import annotations


def test_build_llm_prefers_deepseek_env_for_deepseek_model(monkeypatch):
    from src.services import build_llm as build_llm_module
    from src.utils.context import set_llm_config

    monkeypatch.setenv("LLM_MODEL", "deepseek-chat")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    monkeypatch.setenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    set_llm_config({})

    llm = build_llm_module.build_llm()

    assert llm.model == "deepseek/deepseek-chat"
    assert llm.api_key == "deepseek-key"
    assert llm.api_base == "https://api.deepseek.com/v1"


def test_build_llm_uses_explicit_request_config_over_env(monkeypatch):
    from src.services import build_llm as build_llm_module
    from src.utils.context import set_llm_config

    monkeypatch.setenv("LLM_MODEL", "deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    set_llm_config(
        {
            "model": "openai/gpt-4.1",
            "api_key": "request-key",
            "api_base": "https://example.test/v1",
            "max_tokens": 12000,
            "temperature": 0.4,
        }
    )

    llm = build_llm_module.build_llm()

    assert llm.model == "openai/gpt-4.1"
    assert llm.api_key == "request-key"
    assert llm.api_base == "https://example.test/v1"
    assert llm.max_tokens == 8192
    assert llm.temperature == 0.4


def test_build_llm_supports_generic_api_env_names(monkeypatch):
    from src.services import build_llm as build_llm_module
    from src.utils.context import set_llm_config

    monkeypatch.setenv("LLM_MODEL", "openai/custom-model")
    monkeypatch.setenv("API_KEY", "generic-key")
    monkeypatch.setenv("API_BASE", "https://llm.example.test/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    set_llm_config({})

    llm = build_llm_module.build_llm()

    assert llm.model == "openai/custom-model"
    assert llm.api_key == "generic-key"
    assert llm.api_base == "https://llm.example.test/v1"
