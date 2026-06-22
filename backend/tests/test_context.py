"""Tests for the personal context aggregation layer."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.schemas import (
    CalendarEventResponse,
    CalendarScheduleResponse,
    MemoryCreateRequest,
    WeatherResponse,
)
from backend.app.services import context as context_service
from backend.app.services import memory as memory_service
from backend.app.services.calendar import CalendarServiceError
from backend.app.settings import settings


@pytest.fixture(autouse=True)
def local_memory_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        settings,
        "memory_database_path",
        str(tmp_path / "mirrage-context-test.sqlite3"),
    )


def _weather() -> WeatherResponse:
    return WeatherResponse(
        status="online",
        location="London",
        temperature_c=18.2,
        condition="Partly cloudy",
        updated="2026-06-22T09:00:00+01:00",
    )


def _calendar_event(title: str) -> CalendarEventResponse:
    return CalendarEventResponse(
        id=title.lower().replace(" ", "-"),
        title=title,
        start="2026-06-22T10:00:00+01:00",
        end="2026-06-22T11:00:00+01:00",
        is_all_day=False,
        location=None,
        calendar="Mirrage",
        html_link=None,
    )


def _calendar(events: list[CalendarEventResponse]) -> CalendarScheduleResponse:
    return CalendarScheduleResponse(
        status="ready",
        authenticated=True,
        date="2026-06-22",
        time_zone="Europe/London",
        events=events,
        updated="2026-06-22T09:05:00+00:00",
        message=f"{len(events)} event{'s' if len(events) != 1 else ''} found.",
    )


def _stub_context_sources(
    monkeypatch: pytest.MonkeyPatch,
    *,
    events: list[CalendarEventResponse] | None = None,
) -> None:
    schedule = _calendar(events or [])

    monkeypatch.setattr(context_service.weather_service, "get_weather", _weather)
    monkeypatch.setattr(
        context_service.calendar_service,
        "get_today_schedule",
        lambda: schedule,
    )
    monkeypatch.setattr(
        context_service.calendar_service,
        "get_upcoming_events",
        lambda: schedule,
    )


def test_daily_context_returns_structured_context(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_context_sources(monkeypatch, events=[_calendar_event("Design review")])

    response = client.get("/api/context/daily")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "partial"}
    assert body["weather"]["summary"] == "18 C and partly cloudy in London."
    assert body["calendar"]["today_event_count"] == 1
    assert body["calendar"]["today_events"][0]["title"] == "Design review"
    assert body["memory"]["status"] == "empty"
    assert body["suggested_focus"][0]["source"] == "calendar"


def test_daily_context_includes_memory_goals(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_context_sources(monkeypatch)
    memory_service.create_memory(
        MemoryCreateRequest(
            kind="goal",
            key="goal: finish mirror prototype",
            value="Finish the wall-mounted prototype.",
        )
    )

    response = client.get("/api/context/daily")

    assert response.status_code == 200
    body = response.json()
    assert body["memory"]["goals"][0]["key"] == "goal: finish mirror prototype"
    assert body["suggested_focus"][0]["source"] == "memory"
    assert "Finish the wall-mounted prototype" in body["suggested_focus"][0]["reason"]


def test_daily_context_handles_all_sources_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def weather_down() -> WeatherResponse:
        raise RuntimeError("weather down")

    def calendar_down() -> CalendarScheduleResponse:
        raise CalendarServiceError("calendar down")

    def memory_down():
        raise RuntimeError("memory down")

    monkeypatch.setattr(context_service.weather_service, "get_weather", weather_down)
    monkeypatch.setattr(
        context_service.calendar_service,
        "get_today_schedule",
        calendar_down,
    )
    monkeypatch.setattr(
        context_service.calendar_service,
        "get_upcoming_events",
        calendar_down,
    )
    monkeypatch.setattr(
        context_service.memory_service, "summarize_memories", memory_down
    )

    response = client.get("/api/context/daily")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["weather"]["status"] == "unavailable"
    assert body["calendar"]["status"] == "unavailable"
    assert body["memory"]["status"] == "unavailable"


def test_assistant_daily_briefing_uses_context_provider(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_context_sources(monkeypatch, events=[_calendar_event("Planning")])

    response = client.post(
        "/api/assistant/message",
        json={"message": "Give me my daily briefing"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "context"
    assert body["context_action"] == "daily"
    assert "Daily briefing" in body["reply"]
    assert "Planning" in body["reply"]
    assert "calendar event" in body["reply"]


def test_assistant_focus_command_uses_context_suggestions(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_context_sources(monkeypatch)
    memory_service.create_memory(
        MemoryCreateRequest(
            kind="goal",
            key="goal: ship context phase",
            value="Finish context routing and tests.",
        )
    )

    response = client.post(
        "/api/assistant/message",
        json={"message": "What should I focus on today?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "context"
    assert body["context_action"] == "focus"
    assert "Suggested focus" in body["reply"]
    assert "Ship context phase" in body["reply"]


def test_calendar_and_weather_unavailable_states_are_safe(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory_service.create_memory(
        MemoryCreateRequest(
            kind="routine",
            key="morning review",
            value="Check calendar, weather, and goals.",
        )
    )

    def weather_unavailable() -> WeatherResponse:
        return WeatherResponse(
            status="unavailable",
            location="London",
            temperature_c=None,
            condition="Unavailable",
            updated=None,
        )

    def calendar_not_configured() -> CalendarScheduleResponse:
        return CalendarScheduleResponse(
            status="not_configured",
            authenticated=False,
            date="2026-06-22",
            time_zone="Europe/London",
            events=[],
            updated=None,
            message="Google Calendar client credentials are not configured.",
        )

    monkeypatch.setattr(
        context_service.weather_service,
        "get_weather",
        weather_unavailable,
    )
    monkeypatch.setattr(
        context_service.calendar_service,
        "get_today_schedule",
        calendar_not_configured,
    )
    monkeypatch.setattr(
        context_service.calendar_service,
        "get_upcoming_events",
        calendar_not_configured,
    )

    response = client.get("/api/context/daily")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["weather"]["status"] == "unavailable"
    assert body["calendar"]["status"] == "not_configured"
    assert body["memory"]["status"] == "ready"
    assert body["suggested_focus"][0]["source"] == "memory"
