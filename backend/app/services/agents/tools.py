"""Implementations for the small allow-listed agent tool set."""

from __future__ import annotations

from typing import Any

from backend.app.schemas import MemoryCreateRequest
from backend.app.services import calendar as calendar_service
from backend.app.services import weather as weather_service
from backend.app.services.agents.models import AgentToolExecutionOutput
from backend.app.services.agents.registry import agent_tool_registry
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.memory import (
    create_memory,
    list_memories,
    summarize_memories,
)
from backend.app.services.personalization import visible_profile
from backend.app.services.proactive import get_proactive_summary
from backend.app.services.relationship_models import SharedContextCreateRequest
from backend.app.services.relationship_store import relationship_store
from backend.app.services.smart_home import smart_home_service
from backend.app.services.system import get_system_status


def execute_registered_tool(
    tool_name: str,
    arguments: dict[str, Any],
    principal: AuthenticatedPrincipal,
    run_goal: str,
) -> AgentToolExecutionOutput:
    """Dispatch only after registry validation and policy authorization."""

    if not principal.user_id:
        raise PermissionError("An authenticated user is required.")
    parsed = agent_tool_registry.validate_arguments(tool_name, arguments)
    data = parsed.model_dump(mode="json")

    if tool_name == "weather.read":
        result = weather_service.get_weather()
        return _output(
            f"Weather loaded for {result.location}.",
            f"{result.location}: {result.temperature_c} C, {result.condition}.",
        )
    if tool_name == "calendar.read_today":
        result = calendar_service.get_today_schedule()
        titles = [event.title for event in result.events]
        return _output(
            f"Read {len(titles)} calendar events for today.",
            _list_result("Today's schedule", titles, result.message),
        )
    if tool_name == "calendar.read_upcoming":
        result = calendar_service.get_upcoming_events(data["days"])
        titles = [event.title for event in result.events]
        return _output(
            f"Read {len(titles)} upcoming calendar events.",
            _list_result("Upcoming schedule", titles, result.message),
        )
    if tool_name == "memory.search_own":
        result = list_memories(kind=data.get("kind"), query=data.get("query"))
        items = [f"{item.kind}: {item.key}" for item in result.items]
        return _output(
            f"Found {result.count} matching private memory entries.",
            _list_result("Matching memories", items, "No matching memories."),
        )
    if tool_name == "memory.summary_own":
        result = summarize_memories()
        sections = [
            f"{len(result.goals)} goals",
            f"{len(result.routines)} routines",
            f"{len(result.preferences)} preferences",
            f"{len(result.facts)} facts",
        ]
        return _output(
            f"Summarized {result.count} private memory entries.",
            "Memory summary: " + ", ".join(sections) + ".",
        )
    if tool_name == "shared_context.read_allowed":
        items = relationship_store.list_shared_context(principal.user_id)
        titles = [f"{item.context_type}: {item.title}" for item in items]
        return _output(
            f"Read {len(items)} visible shared-context items.",
            _list_result("Visible context", titles, "No shared context is visible."),
        )
    if tool_name == "profile.read_self":
        result = visible_profile(principal.user_id, principal.user_id)
        fields = [field.replace("_", " ") for field in result.visible_fields]
        return _output(
            f"Read {len(fields)} visible profile fields.",
            _list_result("Profile fields", fields, "No profile fields are set."),
        )
    if tool_name == "proactive.read_summary":
        result = get_proactive_summary(principal)
        return _output(
            f"Loaded proactive summary with priority {result.priority}.",
            f"{result.headline}. {result.message}",
        )
    if tool_name == "smart_home.read_entities":
        result = smart_home_service.entities_response()
        names = [item.name for item in result.items]
        return _output(
            f"Read {result.count} safe smart-home entities.",
            _list_result("Smart-home entities", names, result.message),
        )
    if tool_name == "smart_home.read_sensors":
        result = smart_home_service.sensors_response()
        names = [f"{item.name}: {item.state}" for item in result.items]
        return _output(
            f"Read {result.count} safe smart-home sensors.",
            _list_result("Smart-home sensors", names, result.message),
        )
    if tool_name == "system.read_safe_status":
        result = get_system_status()
        return _output(
            "Read safe Mirrage system status.",
            "System: " + ", ".join(f"{key}={value}" for key, value in result.items()),
        )
    if tool_name == "research.organize_input":
        text = run_goal.strip()
        lines = [line.strip(" -") for line in text.splitlines() if line.strip(" -")]
        organized = lines or [text]
        return _output(
            f"Organized {len(organized)} user-provided items without web access.",
            _list_result("Organized notes", organized, "No input was provided."),
        )
    if tool_name == "memory.create_own":
        result = create_memory(
            MemoryCreateRequest(
                kind=data["kind"],
                key=data["key"],
                value=data["value"],
                source="agent-approved",
            )
        )
        return _output(
            f"Stored approved {result.kind} memory.",
            f"Saved {result.kind}: {result.key}.",
        )
    if tool_name == "shared_context.create_private":
        result = relationship_store.create_shared_context(
            principal.user_id,
            SharedContextCreateRequest(
                context_type=data["context_type"],
                title=data["title"],
                value=data["value"],
                visibility="private",
            ),
        )
        return _output(
            "Created one approved private context item.",
            f"Saved private context: {result.title}.",
        )
    if tool_name == "smart_home.turn_on_approved_light":
        result = smart_home_service.turn_on(data["entity_id"])
        return _output("Sent one approved turn-on action.", result.message)
    if tool_name == "smart_home.turn_off_approved_light":
        result = smart_home_service.turn_off(data["entity_id"])
        return _output("Sent one approved turn-off action.", result.message)
    if tool_name == "smart_home.activate_approved_scene":
        result = smart_home_service.activate_scene(data["entity_id"])
        return _output("Sent one approved scene action.", result.message)
    raise ValueError("Registered tool does not have an implementation.")


def _output(summary: str, result: str) -> AgentToolExecutionOutput:
    return AgentToolExecutionOutput(safe_summary=summary, result_text=result)


def _list_result(title: str, items: list[str], fallback: str) -> str:
    if not items:
        return fallback
    return f"{title}: " + "; ".join(items[:10]) + "."
