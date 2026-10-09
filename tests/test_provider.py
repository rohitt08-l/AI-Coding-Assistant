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


def test_unknown_provider():
    with pytest.raises(LLMError, match="Unknown provider"):
        LLMConfig(provider="nope").resolved()


def test_groq_connection_status_reports_missing_key(monkeypatch):
    monkeypatch.setattr("app.llm.provider.get_settings", lambda: type("S", (), {"groq_api_key": None, "request_timeout_s": 30.0, "max_tokens": 512})())
    status_ok, message = __import__("app.llm.provider", fromlist=["validate_groq_connection"]).validate_groq_connection()
    assert status_ok is False
    assert "GROQ_API_KEY" in message
