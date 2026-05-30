"""Base AI provider interface."""

from abc import ABC, abstractmethod

from ai.models import AssistantResult


class AIProviderError(RuntimeError):
    """Raised when a provider cannot produce a reply."""


class AssistantProvider(ABC):
    name: str

    @abstractmethod
    def reply(self, message: str) -> AssistantResult:
        raise NotImplementedError
