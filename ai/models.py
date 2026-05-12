"""AI data models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantResult:
    reply: str
    provider: str
    model: str | None
