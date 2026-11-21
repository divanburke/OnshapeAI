"""OpenAI-compatible provider adapter for Ollama and cloud models."""
from __future__ import annotations
from typing import Literal
import httpx
from app.settings import Settings

ProviderName = Literal["ollama", "cloud"]

class AIProviderError(RuntimeError):
    pass

async def generate_chat(settings: Settings, messages: list[dict[str, str]], provider: ProviderName | None = None) -> str:
    selected = provider or settings.ai_provider
    if selected == "ollama":
        base_url = settings.ollama_base_url.rstrip("/")
        model = settings.ollama_model
        api_key = "ollama"
    else:
        base_url = settings.cloud_ai_base_url.rstrip("/")
        model = settings.cloud_ai_model
        api_key = settings.cloud_ai_api_key.get_secret_value()
        if not api_key:
            raise AIProviderError("Cloud AI API key is not configured on the backend.")
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise AIProviderError(f"AI provider request failed: {exc}") from exc
