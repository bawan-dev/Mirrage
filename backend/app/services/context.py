"""Provider-independent personal context aggregation."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.app.schemas import (
    AssistantMessageResponse,
    CalendarEventResponse,
    ContextCalendarSummary,
    ContextFocusSuggestion,
    ContextMemorySummary,
    ContextWeatherSummary,
    DailyContext,
    MemoryRecordResponse,
)
from backend.app.services import calendar as calendar_service
from backend.app.services import memory as memory_service
from backend.app.services import weather as weather_service
from backend.app.services.calendar import CalendarServiceError
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.permissions import Permission
from backend.app.settings import settings

_CONTEXT_COMMANDS = (
    "what is my day like",
    "what does my day look like",
    "what should i focus on",
    "what should i focus on today",
    "what goals am i working on",
    "give me my daily briefing",
    "daily briefing",
    "what do i have today",
    "show my context",
)


def get_daily_context(principal: AuthenticatedPrincipal | None = None) -> DailyContext:
    """Return a local daily context object from weather, calendar, and memory."""

    generated_at = datetime.now(UTC).isoformat()
    today = _today()
    weather = _weather_context()
    calendar_allowed = _private_source_allowed(
        principal, Permission.CALENDAR_READ_PRIVATE.value
    )
    memory_allowed = _private_source_allowed(
        principal, Permission.MEMORY_READ_PRIVATE.value
    )
    calendar = _calendar_context(calendar_allowed)
    memory = _memory_context(memory_allowed)
    suggestions = _focus_suggestions(calendar, memory)
    status = _overall_status(weather, calendar, memory)

    return DailyContext(
        status=status,
        date=today,
        generated_at=generated_at,
        weather=weather,
        calendar=calendar,
        memory=memory,
        suggested_focus=suggestions,
        message=_context_message(status),
    )


def handle_context_message(
    message: str, principal: AuthenticatedPrincipal | None = None
) -> AssistantMessageResponse | None:
    """Answer daily-context prompts locally before model provider routing."""

    intent = _context_intent(message)
    if intent is None:
        return None

    context = get_daily_context(principal)
    if intent == "goals":
        reply = _goals_reply(context)
    else:
        reply = _daily_briefing_reply(context)

    return AssistantMessageResponse(
        reply=reply,
        provider="context",
        model=None,
        context_action=intent,
    )


def _weather_context() -> ContextWeatherSummary:
    try:
        weather = weather_service.get_weather()
    except Exception:
        return ContextWeatherSummary(
            status="unavailable",
            location=settings.weather_location,
            temperature_c=None,
            condition="Unavailable",
            summary="Weather is unavailable.",
            updated=None,
            message="Weather could not be loaded from the backend service.",
        )

    if weather.status != "online" or weather.temperature_c is None:
        return ContextWeatherSummary(
            status=weather.status,
            location=weather.location,
            temperature_c=weather.temperature_c,
            condition=weather.condition,
            summary="Weather is unavailable.",
            updated=weather.updated,
            message="Weather data is not available right now.",
        )

    temperature = round(weather.temperature_c)
    summary = f"{temperature} C and {weather.condition.lower()} in {weather.location}."

    return ContextWeatherSummary(
        status=weather.status,
        location=weather.location,
        temperature_c=weather.temperature_c,
        condition=weather.condition,
        summary=summary,
        updated=weather.updated,
        message="Weather loaded.",
    )


def _calendar_context(allowed: bool = True) -> ContextCalendarSummary:
    if not allowed:
        return ContextCalendarSummary(
            status="not_authorized",
            authenticated=False,
            today_event_count=0,
            upcoming_event_count=0,
            today_events=[],
            upcoming_events=[],
            message="Calendar context is private and was not included.",
        )
    today_events: list[CalendarEventResponse] = []
    upcoming_events: list[CalendarEventResponse] = []
    authenticated = False
    statuses: list[str] = []
    messages: list[str] = []

    try:
        today = calendar_service.get_today_schedule()
        today_events = today.events
        authenticated = today.authenticated
        statuses.append(today.status)
        messages.append(today.message)
    except CalendarServiceError as exc:
        statuses.append("unavailable")
        messages.append(str(exc))
    except Exception:
        statuses.append("unavailable")
        messages.append("Calendar could not be loaded from the backend service.")

    try:
        upcoming = calendar_service.get_upcoming_events()
        upcoming_events = upcoming.events
        authenticated = authenticated or upcoming.authenticated
        statuses.append(upcoming.status)
    except CalendarServiceError:
        statuses.append("unavailable")
    except Exception:
        statuses.append("unavailable")

    status = _calendar_status(statuses)
    return ContextCalendarSummary(
        status=status,
        authenticated=authenticated,
        today_event_count=len(today_events),
        upcoming_event_count=len(upcoming_events),
        today_events=today_events[:6],
        upcoming_events=upcoming_events[:6],
        message=_calendar_message(status, today_events, messages),
    )


def _memory_context(allowed: bool = True) -> ContextMemorySummary:
    if not allowed:
        return ContextMemorySummary(
            status="not_authorized",
            preferences=[],
            goals=[],
            routines=[],
            facts_count=0,
            message="Local memory is private and was not included.",
        )
    try:
        summary = memory_service.summarize_memories()
    except Exception:
        return ContextMemorySummary(
            status="unavailable",
            preferences=[],
            goals=[],
            routines=[],
            facts_count=0,
            message="Local memory could not be loaded.",
        )

    status = "empty" if summary.count == 0 else "ready"
    return ContextMemorySummary(
        status=status,
        preferences=summary.preferences[:8],
        goals=summary.goals[:8],
        routines=summary.routines[:8],
        facts_count=len(summary.facts),
        message=summary.message,
    )


def _focus_suggestions(
    calendar: ContextCalendarSummary,
    memory: ContextMemorySummary,
) -> list[ContextFocusSuggestion]:
    suggestions: list[ContextFocusSuggestion] = []

    if calendar.today_events:
        event = calendar.today_events[0]
        suggestions.append(
            ContextFocusSuggestion(
                title=f"Prepare for {event.title}",
                reason="First calendar item today.",
                source="calendar",
                priority="high",
            )
        )

    for goal in memory.goals[:2]:
        suggestions.append(
            ContextFocusSuggestion(
                title=goal.key.removeprefix("goal: ").capitalize(),
                reason=goal.value,
                source="memory",
                priority="medium",
            )
        )

    if not suggestions and memory.routines:
        routine = memory.routines[0]
        suggestions.append(
            ContextFocusSuggestion(
                title=routine.key.capitalize(),
                reason=routine.value,
                source="memory",
                priority="medium",
            )
        )

    if not suggestions:
        suggestions.append(
            ContextFocusSuggestion(
                title="Keep the day light",
                reason="No calendar items or local goals are available yet.",
                source="context",
                priority="low",
            )
        )

    return suggestions[:4]


def _daily_briefing_reply(context: DailyContext) -> str:
    parts = [
        f"Daily briefing for {context.date}.",
        context.weather.summary,
        context.calendar.message,
        _memory_reply_line(context.memory),
        _focus_reply_line(context.suggested_focus),
    ]
    return " ".join(part for part in parts if part)


def _goals_reply(context: DailyContext) -> str:
    goals = context.memory.goals
    if not goals:
        return "I do not have any local goals saved yet."

    goal_text = "; ".join(_memory_item_text(goal) for goal in goals[:5])
    return f"Your active local goals are: {goal_text}."


def _memory_reply_line(memory: ContextMemorySummary) -> str:
    if memory.status == "unavailable":
        return memory.message

    if not memory.goals and not memory.routines and not memory.preferences:
        return "No local goals, routines, or preferences are stored yet."

    details: list[str] = []
    if memory.goals:
        details.append(
            f"{len(memory.goals)} goal{'s' if len(memory.goals) != 1 else ''}"
        )
    if memory.routines:
        details.append(
            f"{len(memory.routines)} routine{'s' if len(memory.routines) != 1 else ''}"
        )
    if memory.preferences:
        preference_count = len(memory.preferences)
        details.append(
            f"{preference_count} preference{'s' if preference_count != 1 else ''}"
        )

    return f"Local memory has {', '.join(details)} available."


def _focus_reply_line(suggestions: list[ContextFocusSuggestion]) -> str:
    if not suggestions:
        return ""

    first = suggestions[0]
    return f"Suggested focus: {first.title}. {first.reason}"


def _memory_item_text(memory: MemoryRecordResponse) -> str:
    return f"{memory.key.removeprefix('goal: ')}: {memory.value}"


def _context_intent(message: str) -> str | None:
    command = _normalize(message)
    if not command:
        return None

    if "goal" in command and ("working on" in command or "my goals" in command):
        return "goals"

    if any(phrase in command for phrase in _CONTEXT_COMMANDS):
        if "focus" in command:
            return "focus"
        return "daily"

    return None


def _calendar_status(statuses: list[str]) -> str:
    if "ready" in statuses:
        return "ready"
    if "not_authenticated" in statuses:
        return "not_authenticated"
    if "not_configured" in statuses:
        return "not_configured"
    if "unavailable" in statuses:
        return "unavailable"
    return "unknown"


def _calendar_message(
    status: str,
    today_events: list[CalendarEventResponse],
    messages: list[str],
) -> str:
    if status == "ready":
        if not today_events:
            return "No calendar events are scheduled today."
        return (
            f"{len(today_events)} calendar event"
            f"{'s' if len(today_events) != 1 else ''} today."
        )

    if status == "not_configured":
        return "Calendar is not configured yet."
    if status == "not_authenticated":
        return "Calendar is configured but not connected."
    if messages:
        return messages[0]
    return "Calendar is unavailable."


def _overall_status(
    weather: ContextWeatherSummary,
    calendar: ContextCalendarSummary,
    memory: ContextMemorySummary,
) -> str:
    if (
        weather.status == "online"
        and calendar.status == "ready"
        and memory.status in {"ready", "empty"}
    ):
        return "ready"

    if (
        weather.status == "unavailable"
        and calendar.status == "unavailable"
        and memory.status == "unavailable"
    ):
        return "unavailable"

    return "partial"


def _context_message(status: str) -> str:
    if status == "ready":
        return "Daily context loaded."
    if status == "partial":
        return "Daily context loaded with one or more fallback states."
    return "Daily context is unavailable."


def _today() -> str:
    try:
        timezone = ZoneInfo(settings.google_calendar_time_zone)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo("UTC")

    return datetime.now(timezone).date().isoformat()


def _private_source_allowed(
    principal: AuthenticatedPrincipal | None, permission: str
) -> bool:
    if principal is None:
        return True
    if permission not in principal.effective_permissions:
        return False
    return not (
        principal.device_type == "mirror" and not principal.human_session_active
    )


def _normalize(value: str) -> str:
    return (
        value.casefold()
        .replace("?", " ")
        .replace(".", " ")
        .replace(",", " ")
        .replace("'", "")
        .replace("’", "")
        .strip()
    )
