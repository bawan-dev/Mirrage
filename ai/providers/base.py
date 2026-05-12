"""Base AI provider interface."""

from abc import ABC, abstractmethod

from ai.models import AssistantResult


class AssistantProvider(ABC):
    name: str

    @abstractmethod
    def reply(self, message: str) -> AssistantResult:
        raise NotImplementedError
