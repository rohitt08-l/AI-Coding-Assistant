import pytest

from app.llm import LLMConfig, LLMError


def test_groq_requires_key(monkeypatch):
    monkeypatch.setattr("app.llm.provider.get_settings", lambda: type("S", (), {"groq_api_key": None})())
    with pytest.raises(LLMError, match="API key"):
        LLMConfig(provider="groq").resolved()


def test_ollama_needs_no_key():
    base_url, model, key = LLMConfig(provider="ollama").resolved()
    assert base_url.endswith("/v1") and model and key == "not-needed"


def test_custom_requires_base_url():
    with pytest.raises(LLMError, match="base_url"):
        LLMConfig(provider="custom", model="x").resolved()


def test_ollama_tunnel_override():
    cfg = LLMConfig(provider="ollama", base_url="https://abc.ngrok.app/v1", model="qwen2.5-coder")
    assert cfg.resolved()[0] == "https://abc.ngrok.app/v1"


def test_key_not_leaked_in_repr():
    assert "secret123" not in repr(LLMConfig(provider="groq", api_key="secret123"))


def test_groq_uses_settings_model_override(monkeypatch):
    monkeypatch.setattr(
        "app.llm.provider.get_settings",
        lambda: type("S", (), {"groq_api_key": "secret", "groq_model": "llama-3.1-8b-instant"})(),
    )
    base_url, model, key = LLMConfig(provider="groq").resolved()
    assert base_url == "https://api.groq.com/openai/v1"
    assert model == "llama-3.1-8b-instant"
    assert key == "secret"


def test_unknown_provider():
    with pytest.raises(LLMError, match="Unknown provider"):
        LLMConfig(provider="nope").resolved()