"""Tests for the proactive assistant layer."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.schemas import (
    CalendarEventResponse,
    ContextCalendarSummary,
    ContextFocusSuggestion,
    ContextMemorySummary,
    ContextWeatherSummary,
    DailyContext,
    MemoryKind,
    MemoryRecordResponse,
)
from backend.app.services import proactive as proactive_service


def _memory_record(kind: MemoryKind, key: str, value: str) -> MemoryRecordResponse:
    return MemoryRecordResponse(
        id=1,
        kind=kind,
        key=key,
        value=value,
        status="active",
        source="test",
        created_at="2026-06-23T08:00:00+00:00",
        updated_at="2026-06-23T08:00:00+00:00",
    )


def _event(title: str, starts_in_minutes: int) -> CalendarEventResponse:
    start = datetime.now(UTC) + timedelta(minutes=starts_in_minutes)
    end = start + timedelta(minutes=30)

    return CalendarEventResponse(
        id=title.lower().replace(" ", "-"),
        title=title,
        start=start.isoformat(),
        end=end.isoformat(),
        is_all_day=False,
        location=None,
        calendar="Mirrage",
        html_link=None,
    )


def _context(
    _principal=None,
    *,
    condition: str = "Mainly clear",
    goals: list[MemoryRecordResponse] | None = None,
    today_events: list[CalendarEventResponse] | None = None,
) -> DailyContext:
    events = today_events or []

    return DailyContext(
        status="partial",
        date="2026-06-23",
        generated_at="2026-06-23T08:00:00+00:00",
        weather=ContextWeatherSummary(
            status="online",
            location="London",
            temperature_c=16.2,
            condition=condition,
            summary=f"16 C and {condition.lower()} in London.",
            updated="2026-06-23T08:00:00+00:00",
            message="Weather loaded.",
        ),
        calendar=ContextCalendarSummary(
            status="ready",
            authenticated=True,
            today_event_count=len(events),
            upcoming_event_count=len(events),
            today_events=events,
            upcoming_events=events,
            message=(
                "No calendar events are scheduled today."
                if not events
                else f"{len(events)} calendar events today."
            ),
        ),
        memory=ContextMemorySummary(
            status="ready" if goals else "empty",
            preferences=[],
            goals=goals or [],
            routines=[],
            facts_count=0,
            message="Memory loaded.",
        ),
        suggested_focus=[
            ContextFocusSuggestion(
                title="Keep the day light",
                reason="No calendar items or local goals are available yet.",
                source="context",
                priority="low",
            )
        ],
        message="Daily context loaded.",
    )


def test_proactive_summary_returns_low_priority_daily_nudge(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(proactive_service, "get_daily_context", _context)

    response = client.get("/api/proactive/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["priority"] == "low"
    assert body["headline"] == "No events today"
    assert body["should_interrupt"] is False
    assert "context" in body["sources"]


def test_proactive_summary_prioritizes_event_starting_soon(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        proactive_service,
        "get_daily_context",
        lambda _principal=None: _context(
            _principal, today_events=[_event("Design review", 10)]
        ),
    )

    response = client.get("/api/proactive/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["priority"] == "high"
    assert body["headline"] == "Design review starts soon"
    assert body["should_interrupt"] is True


def test_proactive_summary_includes_goal_reminder(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        proactive_service,
        "get_daily_context",
        lambda _principal=None: _context(
            _principal,
            goals=[
                _memory_record(
                    "goal",
                    "goal: finish mirror prototype",
                    "Finish the wall-mounted prototype.",
                )
            ],
        ),
    )

    response = client.get("/api/proactive/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["priority"] == "medium"
    assert body["headline"] == "Finish mirror prototype"
    assert "wall-mounted prototype" in body["message"]


def test_proactive_summary_falls_back_when_context_fails(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_context(_principal=None) -> DailyContext:
        raise RuntimeError("context unavailable")

    monkeypatch.setattr(proactive_service, "get_daily_context", broken_context)

    response = client.get("/api/proactive/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["priority"] == "none"
    assert body["headline"] == "Briefing unavailable"
    assert body["should_interrupt"] is False


def test_assistant_good_morning_uses_proactive_provider(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(proactive_service, "get_daily_context", _context)

    response = client.post(
        "/api/assistant/message",
        json={"message": "Good morning"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "proactive"
    assert body["context_action"] == "proactive"
    assert "No events today" in body["reply"]


def test_assistant_focus_prompt_uses_proactive_provider(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        proactive_service,
        "get_daily_context",
        lambda _principal=None: _context(
            _principal,
            goals=[
                _memory_record(
                    "goal",
                    "goal: finish mirror prototype",
                    "Finish the wall-mounted prototype.",
                )
            ],
        ),
    )

    response = client.post(
        "/api/assistant/message",
        json={"message": "What should I focus on today?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "proactive"
    assert body["context_action"] == "proactive"
    assert "Finish mirror prototype" in body["reply"]
