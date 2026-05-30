"""Assistant service boundary."""

from ai.providers.base import AIProviderError
from ai.service import assistant_ai_service
from backend.app.schemas import AssistantMessageRequest, AssistantMessageResponse


def create_assistant_reply(
    message: AssistantMessageRequest,
) -> AssistantMessageResponse:
    try:
        result = assistant_ai_service.reply(message.message)
    except AIProviderError:
        return AssistantMessageResponse(
            reply="The assistant is unavailable right now. Please try again.",
            provider=assistant_ai_service.provider.name,
            model=None,
        )

    return AssistantMessageResponse(
        reply=result.reply,
        provider=result.provider,
        model=result.model,
    )
