"""Assistant service boundary."""

from ai.runtime import assistant_runtime
from backend.app.schemas import AssistantMessageRequest, AssistantMessageResponse
from backend.app.services.context import handle_context_message
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.memory import handle_memory_message
from backend.app.services.proactive import handle_proactive_message
from backend.app.services.smart_home import handle_smart_home_message


def create_assistant_reply(
    message: AssistantMessageRequest,
    principal: AuthenticatedPrincipal | None = None,
) -> AssistantMessageResponse:
    proactive_response = handle_proactive_message(message.message, principal)
    if proactive_response is not None:
        return proactive_response

    context_response = handle_context_message(message.message, principal)
    if context_response is not None:
        return context_response

    memory_response = handle_memory_message(message.message)
    if memory_response is not None:
        return memory_response

    smart_home_response = handle_smart_home_message(message.message)
    if smart_home_response is not None:
        return smart_home_response

    result = assistant_runtime.run_assistant_request(
        message.message, principal=principal
    )

    return AssistantMessageResponse(
        reply=result.reply,
        provider=result.provider,
        model=result.model,
    )
