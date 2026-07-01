"""Ollama provider: talks to a local Ollama server (no API key, private)."""

import httpx

from ai.config import ai_settings
from ai.models import AssistantResult
from ai.providers.base import AIProviderError, AssistantProvider

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"


class OllamaProvider(AssistantProvider):
    name = "ollama"

    def __init__(
        self,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.base_url = (ai_settings.base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or ai_settings.model or DEFAULT_MODEL
        self.timeout = ai_settings.timeout
        self.system_prompt = system_prompt or ai_settings.system_prompt

    def reply(self, message: str) -> AssistantResult:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message},
            ],
        }

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as error:
            raise AIProviderError(f"Ollama request failed: {error}") from error

        return AssistantResult(
            reply=content.strip(),
            provider=self.name,
            model=self.model,
        )
