from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    default_provider: str = "groq"
    groq_api_key: str | None = None  # optional server-side fallback key
    groq_model: str | None = "llama-3.1-8b-instant"  # valid Groq model override
    request_timeout_s: float = 60.0
    max_tokens: int = 2048


@lru_cache
def get_settings() -> Settings:
    return Settings()