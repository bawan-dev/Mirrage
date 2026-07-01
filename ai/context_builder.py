"""Build privacy-aware AI runtime context."""

from __future__ import annotations

from ai.models import RuntimeContext, RuntimePrivacyLevel, RuntimeTaskType
from backend.app.services.context import get_daily_context
from backend.app.services.memory import summarize_memories
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
) -> RuntimeContext:
    """Return a small context bundle for a model request."""

    selected_task = task_type or classify_task_type(message)
    daily_context = _safe_daily_context()
    memory_summary = _safe_memory_summary()
    proactive_summary = _safe_proactive_summary()
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

    if daily_context is not None:
        sources.append("daily_context")
        local_lines.extend(
            [
                f"Weather: {daily_context.weather.summary}",
                f"Calendar: {daily_context.calendar.message}",
                f"Suggested focus: {daily_context.suggested_focus[0].title}",
            ]
        )
        cloud_lines.extend(
            [
                f"Weather: {daily_context.weather.summary}",
                f"Calendar: {daily_context.calendar.message}",
            ]
        )

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
    if task_type in {"memory", "planning", "future_agent"}:
        return "private"
    if memory_summary is not None:
        return "personal"
    return "standard"


def _safe_daily_context():
    try:
        return get_daily_context()
    except Exception:
        return None


def _safe_memory_summary():
    try:
        return summarize_memories()
    except Exception:
        return None


def _safe_proactive_summary():
    try:
        return get_proactive_summary()
    except Exception:
        return None
