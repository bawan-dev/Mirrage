"""OpenAI-compatible provider.

Works with the OpenAI API and any OpenAI-compatible endpoint (including a local
Ollama server's ``/v1`` endpoint) by pointing ``MIRRAGE_AI_BASE_URL`` at it.
"""

import logging

import httpx

from ai.config import ai_settings
from ai.models import AssistantResult
from ai.providers.base import AIProviderError, AssistantProvider

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
logger = logging.getLogger(__name__)


class OpenAIProvider(AssistantProvider):
    name = "openai"

    def __init__(
        self,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.base_url = (ai_settings.base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or ai_settings.model or DEFAULT_MODEL
        self.api_key = ai_settings.api_key
        self.timeout = ai_settings.timeout
        self.system_prompt = system_prompt or ai_settings.system_prompt

    def reply(self, message: str) -> AssistantResult:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message},
            ],
        }

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
            logger.warning(
                "OpenAI-compatible provider request failed.",
                extra={
                    "event": "provider_request_failed",
                    "subsystem": "ai_provider",
                    "provider": self.name,
                    "model": self.model,
                },
            )
            raise AIProviderError(f"OpenAI request failed: {error}") from error

        return AssistantResult(
            reply=content.strip(),
            provider=self.name,
            model=self.model,
        )
