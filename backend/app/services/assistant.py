"""Assistant service boundary."""

from ai.service import assistant_ai_service
from backend.app.schemas import AssistantMessageRequest, AssistantMessageResponse


def create_assistant_reply(
    message: AssistantMessageRequest,
) -> AssistantMessageResponse:
    result = assistant_ai_service.reply(message.message)

    return AssistantMessageResponse(
        reply=result.reply,
        provider=result.provider,
        model=result.model,
    )
