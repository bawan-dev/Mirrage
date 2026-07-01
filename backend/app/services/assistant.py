"""Assistant service boundary."""

from ai.runtime import assistant_runtime
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

    result = assistant_runtime.run_assistant_request(message.message)

    return AssistantMessageResponse(
        reply=result.reply,
        provider=result.provider,
        model=result.model,
    )
