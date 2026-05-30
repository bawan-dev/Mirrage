"""AI service boundary."""

from ai.config import ai_settings
from ai.models import AssistantResult
from ai.providers.base import AssistantProvider
from ai.providers.ollama import OllamaProvider
from ai.providers.openai import OpenAIProvider
from ai.providers.stub import StubAssistantProvider

PROVIDERS: dict[str, type[AssistantProvider]] = {
    "stub": StubAssistantProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
}


class AssistantAIService:
    def __init__(self, provider_name: str | None = None) -> None:
        self.provider = self._build_provider(provider_name or ai_settings.provider)

    def _build_provider(self, provider_name: str) -> AssistantProvider:
        provider_key = provider_name.strip().lower()

        if provider_key not in PROVIDERS:
            supported = ", ".join(sorted(PROVIDERS))
            raise ValueError(
                f"Unsupported AI provider '{provider_name}'. "
                f"Supported providers: {supported}."
            )

        provider_class = PROVIDERS[provider_key]
        return provider_class()

    def reply(self, message: str) -> AssistantResult:
        return self.provider.reply(message)


assistant_ai_service = AssistantAIService()
