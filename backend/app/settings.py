"""Central configuration for Onshape AI Studio.

Secrets are loaded from environment variables or a local .env file.
Never put real credentials in source code or commit a populated .env file.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Onshape AI Studio"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    # Browser access is restricted to the local frontend during development.
    allowed_origins: list[str] = ["http://localhost:5173"]

    # Use the matching Onshape stack for the API key being used.
    # Enterprise users can override this with their company domain.
    onshape_base_url: str = "https://cad.onshape.com/api"
    onshape_access_key: str = ""
    onshape_secret_key: SecretStr = SecretStr("")

    # AI provider selection is configured independently of Onshape.
    ai_provider: Literal["ollama", "cloud"] = "ollama"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5-coder:7b"
    cloud_ai_base_url: str = "https://api.openai.com/v1"
    cloud_ai_api_key: SecretStr = SecretStr("")
    cloud_ai_model: str = "gpt-4.1-mini"

    # Keep server-side limits conservative; tune after observing real usage.
    onshape_request_timeout_seconds: float = 30.0
    onshape_get_cache_ttl_seconds: int = 30
    onshape_max_concurrent_requests: int = 2


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance for the application process."""
    return Settings()
