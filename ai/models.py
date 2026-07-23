"""AI data models."""

from dataclasses import dataclass, field
from typing import Literal

RuntimeTaskType = Literal[
    "conversation",
    "summarisation",
    "memory",
    "planning",
    "context_enhancement",
    "future_agent",
    "agent_planning",
    "agent_execution_summary",
    "agent_result_summary",
]

RuntimePrivacyLevel = Literal["standard", "personal", "private"]


@dataclass(frozen=True)
class AssistantResult:
    reply: str
    provider: str
    model: str | None


@dataclass(frozen=True)
class RuntimeContext:
    user_message: str
    task_type: RuntimeTaskType
    privacy_level: RuntimePrivacyLevel
    local_prompt: str
    cloud_prompt: str
    sources: list[str] = field(default_factory=list)
    memory_items_included: int = 0
    context_items_included: int = 0


@dataclass(frozen=True)
class ProviderSelection:
    provider: str
    model: str | None
    is_local: bool
    supports_streaming: bool
    reason: str
    fallback_provider: str | None = None


@dataclass(frozen=True)
class RuntimeResult:
    reply: str
    provider: str
    model: str | None
    task_type: RuntimeTaskType
    runtime_mode: str
    used_fallback: bool
    context_sources: list[str]
