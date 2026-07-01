"""Initial AI provider used before a model is connected."""

from ai.models import AssistantResult
from ai.providers.base import AssistantProvider


class StubAssistantProvider(AssistantProvider):
    name = "stub"

    def __init__(
        self,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.model = model
        self.system_prompt = system_prompt

    def reply(self, message: str) -> AssistantResult:
        return AssistantResult(
            reply="Assistant routing is ready, but no model is connected yet.",
            provider=self.name,
            model=self.model,
        )
