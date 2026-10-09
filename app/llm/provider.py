"""Provider-agnostic LLM client.

Groq, OpenAI, OpenRouter and Ollama all expose OpenAI-compatible endpoints,
so one client with a configurable base_url covers all of them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import APIError, OpenAI, OpenAIError
from pydantic import BaseModel, SecretStr

from app.config import get_settings


class LLMError(Exception):
    """Raised for any provider failure (bad key, network, rate limit...)."""


@dataclass(frozen=True)
class ProviderPreset:
    base_url: str | None
    default_model: str
    needs_key: bool = True


PROVIDERS: dict[str, ProviderPreset] = {
    "groq": ProviderPreset("https://api.groq.com/openai/v1", "llama-3.1-8b-instant"),
    "openai": ProviderPreset("https://api.openai.com/v1", "gpt-4o-mini"),
    "openrouter": ProviderPreset("https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct"),
    "ollama": ProviderPreset("http://localhost:11434/v1", "llama3.1", needs_key=False),
    "custom": ProviderPreset(None, "", needs_key=False),  # any OpenAI-compatible URL
}


class LLMConfig(BaseModel):
    """Per-request config. The key is a SecretStr so it never shows up in logs/reprs."""

    provider: str = "groq"
    model: str | None = None
    api_key: SecretStr | None = None
    base_url: str | None = None  # overrides the preset (needed for ollama tunnels / custom)

    def resolved(self) -> tuple[str, str, str]:
        """Return (base_url, model, api_key) or raise LLMError with a clear message."""
        preset = PROVIDERS.get(self.provider)
        if preset is None:
            raise LLMError(f"Unknown provider '{self.provider}'. Options: {', '.join(PROVIDERS)}")

        base_url = self.base_url or preset.base_url
        if not base_url:
            raise LLMError("This provider requires a base_url.")

        settings = get_settings()
        groq_model = getattr(settings, "groq_model", None)
        model = self.model or (
            groq_model if self.provider == "groq" and groq_model else preset.default_model
        )
        if not model:
            raise LLMError("A model name is required.")

        key = self.api_key.get_secret_value() if self.api_key else None
        if not key and self.provider == "groq":
            key = settings.groq_api_key  # optional server-side fallback
        if preset.needs_key and not key:
            raise LLMError(f"An API key is required for provider '{self.provider}'.")

        return base_url, model, key or "not-needed"  # SDK demands a non-empty string


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


def validate_groq_connection() -> tuple[bool, str]:
    """Check whether the Groq API key and endpoint are valid without sending a completion request."""
    try:
        settings = get_settings()
        if not settings.groq_api_key:
            return False, "GROQ_API_KEY is missing. Add it to your .env file before trying Groq."

        config = LLMConfig(provider="groq")
        base_url, model, key = config.resolved()
        client = OpenAI(base_url=base_url, api_key=key, timeout=settings.request_timeout_s)
        client.models.list()
        return True, f"Groq connection is healthy. Using model '{model}'."
    except LLMError as exc:
        return False, str(exc)
    except OpenAIError as exc:
        return False, f"Groq connection failed: {exc}"


class LLMClient:
    def __init__(self, config: LLMConfig):
        base_url, self.model, key = config.resolved()
        self._client = OpenAI(
            base_url=base_url,
            api_key=key,
            timeout=get_settings().request_timeout_s,
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": get_settings().max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = self._client.chat.completions.create(**kwargs)
        except APIError as e:
            msg = str(e.message or e)
            if "model_not_found" in msg.lower() or "does not exist" in msg.lower():
                raise LLMError(
                    f"Provider error: {msg}. Set GROQ_MODEL to a valid Groq model such as 'llama-3.1-8b-instant' and restart the app."
                ) from e
            raise LLMError(f"Provider error: {msg}") from e
        except Exception as e:  # network, DNS, timeout...
            raise LLMError(f"Could not reach the model: {e}") from e

        msg = resp.choices[0].message
        calls = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}  # let the tool layer reject it
            calls.append(ToolCall(tc.id, tc.function.name, args))

        usage = {}
        if resp.usage:
            usage = {"prompt": resp.usage.prompt_tokens, "completion": resp.usage.completion_tokens}
        return LLMResponse(content=msg.content or "", tool_calls=calls, usage=usage)