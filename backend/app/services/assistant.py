"""Assistant service boundary."""

from backend.app.schemas import AssistantMessageRequest, AssistantMessageResponse


def create_assistant_reply(
    message: AssistantMessageRequest,
) -> AssistantMessageResponse:
    return AssistantMessageResponse(
        reply="Assistant routing is ready, but no model is connected yet.",
        provider="stub",
        model=None,
    )
