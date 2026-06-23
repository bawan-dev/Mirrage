"""Assistant service boundary."""

from ai.providers.base import AIProviderError
from ai.service import assistant_ai_service
from backend.app.schemas import AssistantMessageRequest, AssistantMessageResponse
from backend.app.services.context import handle_context_message
from backend.app.services.memory import handle_memory_message
from backend.app.services.proactive import handle_proactive_message


def create_assistant_reply(
    message: AssistantMessageRequest,
) -> AssistantMessageResponse:
    proactive_response = handle_proactive_message(message.message)
    if proactive_response is not None:
        return proactive_response

    context_response = handle_context_message(message.message)
    if context_response is not None:
        return context_response

    memory_response = handle_memory_message(message.message)
    if memory_response is not None:
        return memory_response

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
