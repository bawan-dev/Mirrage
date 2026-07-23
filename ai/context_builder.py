"""Build privacy-aware AI runtime context."""

from __future__ import annotations

from ai.models import RuntimeContext, RuntimePrivacyLevel, RuntimeTaskType
from backend.app.services.context import get_daily_context
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.memory import summarize_memories
from backend.app.services.permissions import Permission
from backend.app.services.personalization import build_safe_personalization_context
from backend.app.services.proactive import get_proactive_summary

_PLANNING_TERMS = ("plan", "roadmap", "schedule", "strategy", "next steps")
_SUMMARY_TERMS = ("summarize", "summary", "recap", "brief")
_MEMORY_TERMS = ("remember", "memory", "preference", "goal", "routine")


def classify_task_type(message: str) -> RuntimeTaskType:
    normalized = message.casefold()

    if any(term in normalized for term in _MEMORY_TERMS):
        return "memory"
    if any(term in normalized for term in _PLANNING_TERMS):
        return "planning"
    if any(term in normalized for term in _SUMMARY_TERMS):
        return "summarisation"
    if "context" in normalized or "my day" in normalized:
        return "context_enhancement"
    if "agent" in normalized:
        return "future_agent"

    return "conversation"


def build_runtime_context(
    message: str,
    task_type: RuntimeTaskType | None = None,
    principal: AuthenticatedPrincipal | None = None,
) -> RuntimeContext:
    """Return a small context bundle for a model request."""

    selected_task = task_type or classify_task_type(message)
    agent_task = selected_task in {
        "agent_planning",
        "agent_execution_summary",
        "agent_result_summary",
    }
    if agent_task:
        daily_context = None
        memory_summary = None
        proactive_summary = None
    elif principal is None:
        daily_context = _safe_daily_context()
        memory_summary = _safe_memory_summary()
        proactive_summary = _safe_proactive_summary()
    else:
        daily_context = _safe_daily_context(principal)
        memory_summary = _safe_memory_summary(principal)
        proactive_summary = _safe_proactive_summary(principal)
    personalization = build_safe_personalization_context(principal)
    privacy_level = _privacy_level(selected_task, memory_summary)
    sources: list[str] = []
    local_lines = [
        "You are Mirrage, a calm smart mirror assistant.",
        "Answer concisely and use the context only when it helps.",
    ]
    cloud_lines = [
        "You are Mirrage, a calm smart mirror assistant.",
        "Answer concisely. Private local memory has been summarized or withheld.",
    ]

    if personalization.local_lines:
        sources.extend(personalization.sources)
        local_lines.extend(personalization.local_lines)
    if personalization.cloud_lines:
        cloud_lines.extend(personalization.cloud_lines)

    if daily_context is not None:
        sources.append("daily_context")
        local_lines.extend(
            [
                f"Weather: {daily_context.weather.summary}",
                f"Calendar: {daily_context.calendar.message}",
                f"Suggested focus: {daily_context.suggested_focus[0].title}",
            ]
        )
        cloud_lines.append(f"Weather: {daily_context.weather.summary}")
        if principal is None:
            cloud_lines.append(f"Calendar: {daily_context.calendar.message}")

    memory_count = 0
    if memory_summary is not None:
        sources.append("memory")
        preferences = memory_summary.preferences[:3]
        goals = memory_summary.goals[:3]
        routines = memory_summary.routines[:2]
        memory_count = len(preferences) + len(goals) + len(routines)

        if preferences:
            local_lines.append(
                "Preferences: "
                + "; ".join(f"{memory.key}: {memory.value}" for memory in preferences)
            )
        if goals:
            local_lines.append(
                "Active goals: "
                + "; ".join(f"{memory.key}: {memory.value}" for memory in goals)
            )
            cloud_lines.append(
                f"Local memory has {len(goals)} active goal"
                f"{'s' if len(goals) != 1 else ''}; details withheld."
            )
        if routines:
            local_lines.append(
                "Routines: "
                + "; ".join(f"{memory.key}: {memory.value}" for memory in routines)
            )

        if memory_count == 0:
            local_lines.append(memory_summary.message)
            cloud_lines.append(memory_summary.message)

    if proactive_summary is not None:
        sources.append("proactive")
        local_lines.append(
            f"Proactive note: {proactive_summary.headline}. {proactive_summary.message}"
        )

    local_lines.append(f"User request: {message}")
    cloud_lines.append(f"User request: {message}")

    return RuntimeContext(
        user_message=message,
        task_type=selected_task,
        privacy_level=privacy_level,
        local_prompt="\n".join(local_lines),
        cloud_prompt="\n".join(cloud_lines),
        sources=sources,
        memory_items_included=memory_count,
        context_items_included=len(sources),
    )


def _privacy_level(
    task_type: RuntimeTaskType, memory_summary: object | None
) -> RuntimePrivacyLevel:
    if task_type in {
        "memory",
        "planning",
        "future_agent",
        "agent_planning",
        "agent_execution_summary",
        "agent_result_summary",
    }:
        return "private"
    if memory_summary is not None:
        return "personal"
    return "standard"


def _safe_daily_context(principal: AuthenticatedPrincipal | None = None):
    try:
        return get_daily_context(principal)
    except Exception:
        return None


def _safe_memory_summary(principal: AuthenticatedPrincipal | None = None):
    if principal is not None and not _principal_allows(
        principal, Permission.MEMORY_READ_PRIVATE.value
    ):
        return None
    try:
        return summarize_memories()
    except Exception:
        return None


def _safe_proactive_summary(principal: AuthenticatedPrincipal | None = None):
    if principal is not None and not _principal_allows(
        principal, Permission.CONTEXT_READ_PRIVATE.value
    ):
        return None
    try:
        return get_proactive_summary(principal)
    except Exception:
        return None


def _principal_allows(principal: AuthenticatedPrincipal, permission: str) -> bool:
    if permission not in principal.effective_permissions:
        return False
    return not (
        principal.device_type == "mirror" and not principal.human_session_active
    )
