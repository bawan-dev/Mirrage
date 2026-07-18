"""Privacy-first proactive assistant logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.app.schemas import (
    AssistantMessageResponse,
    CalendarEventResponse,
    DailyContext,
    ProactiveSummaryResponse,
)
from backend.app.services.context import get_daily_context
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.personalization import build_safe_personalization_context

_PROACTIVE_COMMANDS = (
    "good morning",
    "brief me",
    "give me my daily briefing",
    "daily briefing",
    "what should i know today",
    "what should i focus on",
    "what should i focus on today",
    "any reminders",
    "what needs my attention",
)

_WEATHER_ATTENTION_TERMS = (
    "rain",
    "snow",
    "storm",
    "thunder",
    "fog",
    "wind",
    "drizzle",
    "showers",
)


def get_proactive_summary(
    principal: AuthenticatedPrincipal | None = None,
) -> ProactiveSummaryResponse:
    """Return a deterministic proactive summary from local context sources."""

    generated_at = datetime.now(UTC).isoformat()

    personalization = build_safe_personalization_context(principal)
    if (
        principal is not None
        and "profile" in personalization.sources
        and (personalization.proactivity == "silent" or personalization.quiet_hours)
    ):
        reason = (
            "Quiet hours are active."
            if personalization.quiet_hours
            else "Proactivity is set to silent."
        )
        return ProactiveSummaryResponse(
            status="ready",
            generated_at=generated_at,
            priority="none",
            headline="Standing by",
            message=reason,
            suggestions=[],
            sources=["profile"],
            should_interrupt=False,
        )

    try:
        context = (
            get_daily_context() if principal is None else get_daily_context(principal)
        )
    except Exception:
        return ProactiveSummaryResponse(
            status="unavailable",
            generated_at=generated_at,
            priority="none",
            headline="Briefing unavailable",
            message="Mirrage could not load local context right now.",
            suggestions=["Try again later"],
            sources=[],
            should_interrupt=False,
        )

    event_soon = _event_starting_soon(context.calendar.today_events)
    weather_needs_attention = _weather_needs_attention(context.weather.condition)
    first_focus = context.suggested_focus[0] if context.suggested_focus else None
    sources = _sources_used(context)

    if event_soon is not None:
        return ProactiveSummaryResponse(
            status="ready",
            generated_at=generated_at,
            priority="high",
            headline=f"{event_soon.title} starts soon",
            message=(
                "Your next calendar event is close. Open Calendar when you are ready."
            ),
            suggestions=["Open Calendar", "Ask for your daily briefing"],
            sources=sources,
            should_interrupt=True,
        )

    if context.calendar.today_event_count >= 4:
        return ProactiveSummaryResponse(
            status="ready",
            generated_at=generated_at,
            priority="medium",
            headline="Busy day ahead",
            message=(
                f"You have {context.calendar.today_event_count} events today. "
                "Keep transitions light."
            ),
            suggestions=["Review today's schedule", "Ask what needs attention"],
            sources=sources,
            should_interrupt=False,
        )

    if weather_needs_attention:
        return ProactiveSummaryResponse(
            status="ready",
            generated_at=generated_at,
            priority="medium",
            headline="Weather may affect plans",
            message=context.weather.summary,
            suggestions=["Open Weather", "Plan around the forecast"],
            sources=sources,
            should_interrupt=False,
        )

    if context.memory.goals:
        goal = context.memory.goals[0]
        return ProactiveSummaryResponse(
            status="ready",
            generated_at=generated_at,
            priority="medium",
            headline=goal.key.removeprefix("goal: ").capitalize(),
            message=goal.value,
            suggestions=["Ask what should I focus on", "Open Context"],
            sources=sources,
            should_interrupt=False,
        )

    if context.calendar.today_event_count == 0 and context.calendar.status == "ready":
        return ProactiveSummaryResponse(
            status="ready",
            generated_at=generated_at,
            priority="low",
            headline="No events today",
            message="Good time for focused work.",
            suggestions=["Ask for your daily briefing", "Add a goal to memory"],
            sources=sources,
            should_interrupt=False,
        )

    if first_focus is not None:
        return ProactiveSummaryResponse(
            status=context.status,
            generated_at=generated_at,
            priority=first_focus.priority,
            headline=first_focus.title,
            message=first_focus.reason,
            suggestions=["Open Context", "Ask what should I know today"],
            sources=sources,
            should_interrupt=False,
        )

    return ProactiveSummaryResponse(
        status="ready",
        generated_at=generated_at,
        priority="none",
        headline="Nothing needs attention",
        message="Mirrage is standing by.",
        suggestions=[],
        sources=sources,
        should_interrupt=False,
    )


def handle_proactive_message(
    message: str, principal: AuthenticatedPrincipal | None = None
) -> AssistantMessageResponse | None:
    """Answer proactive prompts locally before model provider routing."""

    command = _normalize(message)
    if not command or not any(phrase in command for phrase in _PROACTIVE_COMMANDS):
        return None

    summary = get_proactive_summary(principal)

    return AssistantMessageResponse(
        reply=_summary_reply(summary),
        provider="proactive",
        model=None,
        context_action="proactive",
    )


def _event_starting_soon(
    events: list[CalendarEventResponse],
) -> CalendarEventResponse | None:
    now = datetime.now(UTC)

    for event in events:
        if event.is_all_day:
            continue

        try:
            start = datetime.fromisoformat(event.start)
        except ValueError:
            continue

        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)

        starts_in = start.astimezone(UTC) - now
        if timedelta(minutes=0) <= starts_in <= timedelta(minutes=30):
            return event

    return None


def _weather_needs_attention(condition: str) -> bool:
    condition_text = condition.casefold()
    return any(term in condition_text for term in _WEATHER_ATTENTION_TERMS)


def _sources_used(context: DailyContext) -> list[str]:
    sources = ["context"]

    if context.weather.status != "unavailable":
        sources.append("weather")
    if context.calendar.status != "unavailable":
        sources.append("calendar")
    if context.memory.status != "unavailable":
        sources.append("memory")

    return sources


def _summary_reply(summary: ProactiveSummaryResponse) -> str:
    parts = [
        summary.headline,
        summary.message,
    ]

    if summary.suggestions:
        parts.append(f"Suggested next step: {summary.suggestions[0]}.")

    return " ".join(part for part in parts if part)


def _normalize(value: str) -> str:
    normalized = "".join(
        character if character.isalnum() or character.isspace() else " "
        for character in value.casefold()
    )
    return " ".join(normalized.split())
