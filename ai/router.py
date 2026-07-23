"""Provider routing for the Mirrage AI runtime."""

from __future__ import annotations

from dataclasses import dataclass

from ai.config import ai_settings
from ai.models import ProviderSelection, RuntimeContext, RuntimeTaskType
from ai.providers.base import AssistantProvider
from ai.providers.ollama import OllamaProvider
from ai.providers.openai import OpenAIProvider
from ai.providers.stub import StubAssistantProvider


@dataclass(frozen=True)
class ProviderDefinition:
    name: str
    provider_class: type[AssistantProvider]
    kind: str
    supports_streaming: bool = False
    requires_secret: bool = False

    @property
    def is_local(self) -> bool:
        return self.kind == "local"


PROVIDER_DEFINITIONS: dict[str, ProviderDefinition] = {
    "stub": ProviderDefinition("stub", StubAssistantProvider, "local"),
    "ollama": ProviderDefinition("ollama", OllamaProvider, "local"),
    "openai": ProviderDefinition(
        "openai",
        OpenAIProvider,
        "cloud",
        requires_secret=True,
    ),
}

_TASK_MODEL_FIELDS: dict[RuntimeTaskType, str] = {
    "conversation": "default_task_model",
    "summarisation": "summary_model",
    "memory": "default_task_model",
    "planning": "planning_model",
    "context_enhancement": "summary_model",
    "future_agent": "planning_model",
    "agent_planning": "planning_model",
    "agent_execution_summary": "summary_model",
    "agent_result_summary": "summary_model",
}


class ProviderRouter:
    """Selects a provider and model without provider-specific request logic."""

    def select_provider(self, context: RuntimeContext) -> ProviderSelection:
        preferred = self._safe_provider_name(ai_settings.provider)
        fallback = self._safe_provider_name(ai_settings.fallback_provider)
        model = self.select_model(context.task_type)

        if ai_settings.local_only:
            provider = self._local_provider(preferred)
            fallback_provider = self._local_provider(fallback)
            if fallback_provider == provider and provider != "stub":
                fallback_provider = "stub"
            return self._selection(
                provider,
                model,
                reason="local_only",
                fallback_provider=fallback_provider,
            )

        if context.privacy_level == "private" or ai_settings.local_first:
            provider = self._local_provider(preferred)
            return self._selection(
                provider,
                model,
                reason="privacy_or_local_first",
                fallback_provider=self._safe_fallback(fallback),
            )

        return self._selection(
            preferred,
            model,
            reason="preferred_provider",
            fallback_provider=self._safe_fallback(fallback),
        )

    def select_model(self, task_type: RuntimeTaskType) -> str | None:
        field_name = _TASK_MODEL_FIELDS.get(task_type, "default_task_model")
        task_model = getattr(ai_settings, field_name, None)
        return task_model or ai_settings.model

    def build_provider(
        self,
        provider_name: str,
        model: str | None,
    ) -> AssistantProvider:
        provider = PROVIDER_DEFINITIONS[self._safe_provider_name(provider_name)]
        return provider.provider_class(
            model=model, system_prompt=ai_settings.system_prompt
        )

    def provider_status(self) -> list[dict[str, str | bool | None]]:
        return [
            {
                "name": provider.name,
                "kind": provider.kind,
                "configured": self._is_configured(provider),
                "supports_streaming": provider.supports_streaming,
                "default_model": self._provider_model(provider.name),
            }
            for provider in PROVIDER_DEFINITIONS.values()
        ]

    def available_provider_names(self) -> list[str]:
        return sorted(PROVIDER_DEFINITIONS)

    def _selection(
        self,
        provider_name: str,
        model: str | None,
        *,
        reason: str,
        fallback_provider: str | None,
    ) -> ProviderSelection:
        provider = PROVIDER_DEFINITIONS[provider_name]
        return ProviderSelection(
            provider=provider.name,
            model=model,
            is_local=provider.is_local,
            supports_streaming=provider.supports_streaming,
            reason=reason,
            fallback_provider=fallback_provider,
        )

    def _local_provider(self, provider_name: str) -> str:
        provider = PROVIDER_DEFINITIONS[provider_name]
        if provider.is_local:
            return provider.name
        return "ollama" if "ollama" in PROVIDER_DEFINITIONS else "stub"

    def _safe_fallback(self, provider_name: str) -> str | None:
        if ai_settings.local_only:
            fallback = self._local_provider(provider_name)
            return fallback if fallback != provider_name else None
        return provider_name

    @staticmethod
    def _safe_provider_name(provider_name: str) -> str:
        provider_key = provider_name.strip().lower()
        if provider_key in PROVIDER_DEFINITIONS:
            return provider_key
        return "stub"

    @staticmethod
    def _is_configured(provider: ProviderDefinition) -> bool:
        if provider.name == "openai":
            return bool(ai_settings.api_key or ai_settings.base_url)
        return True

    @staticmethod
    def _provider_model(provider_name: str) -> str | None:
        if provider_name == "ollama":
            return ai_settings.model or "llama3.2"
        if provider_name == "openai":
            return ai_settings.model or "gpt-4o-mini"
        return ai_settings.model


provider_router = ProviderRouter()
