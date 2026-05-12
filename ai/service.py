"""AI service boundary."""

from ai.models import AssistantResult
from ai.providers.stub import StubAssistantProvider


class AssistantAIService:
    def __init__(self) -> None:
        self.provider = StubAssistantProvider()

    def reply(self, message: str) -> AssistantResult:
        return self.provider.reply(message)


assistant_ai_service = AssistantAIService()
