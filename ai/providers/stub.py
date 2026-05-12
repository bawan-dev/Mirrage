"""Initial AI provider used before a model is connected."""

from ai.models import AssistantResult
from ai.providers.base import AssistantProvider


class StubAssistantProvider(AssistantProvider):
    name = "stub"

    def reply(self, message: str) -> AssistantResult:
        return AssistantResult(
            reply="Assistant routing is ready, but no model is connected yet.",
            provider=self.name,
            model=None,
        )
