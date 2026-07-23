"""Central allow-list of tools available to bounded agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from backend.app.services.agents.models import (
    AgentToolExecutionOutput,
    AgentToolResponse,
    AgentType,
    CalendarUpcomingInput,
    EmptyToolInput,
    MemoryCreateInput,
    MemorySearchInput,
    OrganizeInput,
    SharedContextCreateInput,
    SmartHomeEntityInput,
    SmartHomeSceneInput,
)
from backend.app.services.permissions import Permission


class UnknownAgentToolError(ValueError):
    """Raised when a plan references a tool outside the registry."""


@dataclass(frozen=True)
class RegisteredAgentTool:
    name: str
    description: str
    input_model: type[BaseModel]
    required_permission: str
    risk_level: str
    side_effect: bool
    approval_required: bool
    timeout_seconds: float
    max_retries: int
    idempotent: bool
    allowed_agent_types: frozenset[AgentType]

    def descriptor(self) -> AgentToolResponse:
        return AgentToolResponse(
            name=self.name,
            description=self.description,
            required_permission=self.required_permission,
            risk_level=self.risk_level,
            side_effect=self.side_effect,
            approval_required=self.approval_required,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            idempotent=self.idempotent,
            allowed_agent_types=sorted(self.allowed_agent_types),
            input_schema=self.input_model.model_json_schema(),
            output_schema=AgentToolExecutionOutput.model_json_schema(),
        )


READ_ONLY_TYPES = frozenset(
    {"planning", "memory", "calendar", "smart_home", "research"}
)


def _tool(
    name: str,
    description: str,
    input_model: type[BaseModel],
    permission: Permission,
    *,
    types: frozenset[AgentType] = READ_ONLY_TYPES,
    side_effect: bool = False,
    approval: bool = False,
    idempotent: bool = True,
    retries: int = 1,
    timeout: float = 10.0,
) -> RegisteredAgentTool:
    return RegisteredAgentTool(
        name=name,
        description=description,
        input_model=input_model,
        required_permission=permission.value,
        risk_level="low" if side_effect else "read_only",
        side_effect=side_effect,
        approval_required=approval,
        timeout_seconds=timeout,
        max_retries=retries,
        idempotent=idempotent,
        allowed_agent_types=types,
    )


_TOOLS = (
    _tool(
        "weather.read",
        "Read the configured current weather summary.",
        EmptyToolInput,
        Permission.WEATHER_READ,
        types=frozenset({"planning", "calendar"}),
    ),
    _tool(
        "calendar.read_today",
        "Read the authenticated user's schedule for today.",
        EmptyToolInput,
        Permission.CALENDAR_READ_PRIVATE,
        types=frozenset({"planning", "calendar"}),
    ),
    _tool(
        "calendar.read_upcoming",
        "Read the authenticated user's upcoming schedule.",
        CalendarUpcomingInput,
        Permission.CALENDAR_READ_PRIVATE,
        types=frozenset({"planning", "calendar"}),
    ),
    _tool(
        "memory.search_own",
        "Search the current installation owner's private memory store.",
        MemorySearchInput,
        Permission.MEMORY_READ_PRIVATE,
        types=frozenset({"planning", "memory"}),
    ),
    _tool(
        "memory.summary_own",
        "Summarize the current installation owner's private memory store.",
        EmptyToolInput,
        Permission.MEMORY_READ_PRIVATE,
        types=frozenset({"planning", "memory"}),
    ),
    _tool(
        "shared_context.read_allowed",
        "Read shared context already visible to the authenticated user.",
        EmptyToolInput,
        Permission.SHARED_CONTEXT_READ,
        types=frozenset({"planning", "memory", "research"}),
    ),
    _tool(
        "profile.read_self",
        "Read the authenticated user's own personalization profile.",
        EmptyToolInput,
        Permission.PROFILE_READ_SELF,
    ),
    _tool(
        "proactive.read_summary",
        "Read the authenticated user's deterministic proactive summary.",
        EmptyToolInput,
        Permission.CONTEXT_READ_PRIVATE,
        types=frozenset({"planning", "calendar"}),
    ),
    _tool(
        "smart_home.read_entities",
        "Read supported Home Assistant entities through the safe service boundary.",
        EmptyToolInput,
        Permission.SMART_HOME_READ,
        types=frozenset({"smart_home"}),
    ),
    _tool(
        "smart_home.read_sensors",
        "Read supported Home Assistant sensors through the safe service boundary.",
        EmptyToolInput,
        Permission.SMART_HOME_READ,
        types=frozenset({"smart_home"}),
    ),
    _tool(
        "system.read_safe_status",
        "Read non-private Mirrage system status.",
        EmptyToolInput,
        Permission.SYSTEM_STATUS_READ,
        types=frozenset({"planning", "research"}),
    ),
    _tool(
        "research.organize_input",
        "Organize user-provided text without fetching external sources.",
        OrganizeInput,
        Permission.ASSISTANT_USE,
        types=frozenset({"research", "planning"}),
    ),
    _tool(
        "memory.create_own",
        "Create one entry in the owner-private memory store.",
        MemoryCreateInput,
        Permission.MEMORY_WRITE_PRIVATE,
        types=frozenset({"memory"}),
        side_effect=True,
        approval=True,
        idempotent=False,
        retries=0,
    ),
    _tool(
        "shared_context.create_private",
        "Create a private shared-context item owned by the authenticated user.",
        SharedContextCreateInput,
        Permission.SHARED_CONTEXT_MANAGE,
        types=frozenset({"memory"}),
        side_effect=True,
        approval=True,
        idempotent=False,
        retries=0,
    ),
    _tool(
        "smart_home.turn_on_approved_light",
        "Turn on an approved light or switch through the smart-home safety layer.",
        SmartHomeEntityInput,
        Permission.SMART_HOME_CONTROL_LOW_RISK,
        types=frozenset({"smart_home"}),
        side_effect=True,
        approval=True,
        idempotent=True,
        retries=0,
    ),
    _tool(
        "smart_home.turn_off_approved_light",
        "Turn off an approved light or switch through the smart-home safety layer.",
        SmartHomeEntityInput,
        Permission.SMART_HOME_CONTROL_LOW_RISK,
        types=frozenset({"smart_home"}),
        side_effect=True,
        approval=True,
        idempotent=True,
        retries=0,
    ),
    _tool(
        "smart_home.activate_approved_scene",
        "Activate an approved scene through the smart-home safety layer.",
        SmartHomeSceneInput,
        Permission.SMART_HOME_CONTROL_LOW_RISK,
        types=frozenset({"smart_home"}),
        side_effect=True,
        approval=True,
        idempotent=True,
        retries=0,
    ),
)


class AgentToolRegistry:
    def __init__(self) -> None:
        self._tools = {tool.name: tool for tool in _TOOLS}

    def get(self, name: str) -> RegisteredAgentTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownAgentToolError("The proposed tool is not registered.") from exc

    def descriptors(self) -> list[AgentToolResponse]:
        return [self._tools[name].descriptor() for name in sorted(self._tools)]

    def names_for(self, agent_type: AgentType) -> list[str]:
        return sorted(
            name
            for name, tool in self._tools.items()
            if agent_type in tool.allowed_agent_types
        )

    def validate_arguments(self, name: str, arguments: dict[str, Any]) -> BaseModel:
        return self.get(name).input_model.model_validate(arguments)


agent_tool_registry = AgentToolRegistry()
