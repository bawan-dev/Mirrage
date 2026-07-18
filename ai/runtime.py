"""AI Runtime orchestration for Mirrage."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

from ai.config import ai_settings
from ai.context_builder import build_runtime_context
from ai.models import RuntimeResult, RuntimeTaskType
from ai.providers.base import AIProviderError
from ai.router import PROVIDER_DEFINITIONS, provider_router
from backend.app.services.identity_models import AuthenticatedPrincipal

logger = logging.getLogger(__name__)


class AIRuntime:
    """Orchestrates context, provider routing, fallback, and streaming shape."""

    def run_assistant_request(
        self,
        message: str,
        task_type: RuntimeTaskType | None = None,
        principal: AuthenticatedPrincipal | None = None,
    ) -> RuntimeResult:
        context = (
            build_runtime_context(message, task_type)
            if principal is None
            else build_runtime_context(message, task_type, principal)
        )
        selection = provider_router.select_provider(context)
        prompt = context.local_prompt if selection.is_local else context.cloud_prompt
        provider = provider_router.build_provider(selection.provider, selection.model)
        logger.info(
            "AI runtime selected provider.",
            extra={
                "event": "ai_provider_selected",
                "subsystem": "ai_runtime",
                "provider": selection.provider,
                "task_type": context.task_type,
                "local": selection.is_local,
            },
        )

        try:
            result = provider.reply(prompt)
            return RuntimeResult(
                reply=result.reply,
                provider=result.provider,
                model=result.model,
                task_type=context.task_type,
                runtime_mode=ai_settings.runtime_mode,
                used_fallback=False,
                context_sources=context.sources,
            )
        except AIProviderError:
            fallback = selection.fallback_provider
            logger.warning(
                "AI provider failed; attempting fallback.",
                extra={
                    "event": "ai_provider_fallback",
                    "subsystem": "ai_runtime",
                    "provider": selection.provider,
                    "fallback_provider": fallback,
                    "task_type": context.task_type,
                },
            )
            if not fallback or fallback == selection.provider:
                return self._unavailable_result(context.task_type, context.sources)

            fallback_provider = provider_router.build_provider(
                fallback, selection.model
            )
            fallback_definition = PROVIDER_DEFINITIONS[fallback]
            fallback_prompt = (
                context.local_prompt
                if fallback_definition.is_local
                else context.cloud_prompt
            )

            try:
                result = fallback_provider.reply(fallback_prompt)
            except AIProviderError:
                return self._unavailable_result(context.task_type, context.sources)

            return RuntimeResult(
                reply=result.reply,
                provider=result.provider,
                model=result.model,
                task_type=context.task_type,
                runtime_mode=ai_settings.runtime_mode,
                used_fallback=True,
                context_sources=context.sources,
            )

    def stream_assistant_request(
        self,
        message: str,
        *,
        principal: AuthenticatedPrincipal | None = None,
    ) -> Iterator[str]:
        """Yield Server-Sent Events.

        Providers do not expose token streaming yet, so this path keeps the API
        shape ready and falls back to one response chunk.
        """

        if not ai_settings.streaming_enabled:
            yield _sse("error", {"message": "AI runtime streaming is disabled."})
            return

        yield _sse("status", {"stage": "runtime_started"})
        result = self.run_assistant_request(message, principal=principal)
        yield _sse(
            "chunk",
            {
                "text": result.reply,
                "provider": result.provider,
                "model": result.model,
                "fallback": result.used_fallback,
            },
        )
        yield _sse("done", {"provider": result.provider, "model": result.model})

    def runtime_status(self) -> dict[str, str | bool | list[str] | None]:
        return {
            "runtime_mode": ai_settings.runtime_mode,
            "configured_provider": ai_settings.provider,
            "fallback_provider": ai_settings.fallback_provider,
            "local_first": ai_settings.local_first,
            "local_only": ai_settings.local_only,
            "streaming_enabled": ai_settings.streaming_enabled,
            "privacy_mode": ai_settings.privacy_mode,
            "available_providers": provider_router.available_provider_names(),
            "default_task_model": ai_settings.default_task_model,
            "summary_model": ai_settings.summary_model,
            "planning_model": ai_settings.planning_model,
        }

    @staticmethod
    def _unavailable_result(
        task_type: RuntimeTaskType,
        sources: list[str],
    ) -> RuntimeResult:
        return RuntimeResult(
            reply=(
                "The AI runtime is unavailable right now. "
                "Local deterministic Mirrage services are still available."
            ),
            provider="runtime",
            model=None,
            task_type=task_type,
            runtime_mode=ai_settings.runtime_mode,
            used_fallback=True,
            context_sources=sources,
        )


def _sse(event: str, payload: dict[str, object]) -> str:
    data = json.dumps(payload, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


assistant_runtime = AIRuntime()
