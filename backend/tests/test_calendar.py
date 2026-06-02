"""Tests for the Google Calendar integration API boundary."""

import time
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.services import calendar as calendar_service


@pytest.fixture(autouse=True)
def reset_calendar(monkeypatch: pytest.MonkeyPatch) -> None:
    calendar_service._reset_for_tests()
    monkeypatch.setattr(calendar_service.settings, "google_calendar_client_id", None)
    monkeypatch.setattr(
        calendar_service.settings,
        "google_calendar_client_secret",
        None,
    )
    monkeypatch.setattr(
        calendar_service.settings,
        "google_calendar_redirect_uri",
        "http://127.0.0.1:8000/api/integrations/calendar/callback",
    )
    monkeypatch.setattr(calendar_service.settings, "google_calendar_id", "primary")
    monkeypatch.setattr(
        calendar_service.settings,
        "google_calendar_time_zone",
        "Europe/London",
    )


def configure_calendar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        calendar_service.settings,
        "google_calendar_client_id",
        "client-id",
    )
    monkeypatch.setattr(
        calendar_service.settings,
        "google_calendar_client_secret",
        "client-secret",
    )


def authenticate_calendar() -> None:
    calendar_service._token_state = calendar_service.CalendarTokenState(
        access_token="access-token",
        refresh_token="refresh-token",
        expires_at=time.time() + 3600,
        scopes=calendar_service.GOOGLE_CALENDAR_SCOPES,
    )


def test_calendar_status_reports_missing_configuration(client: TestClient) -> None:
    response = client.get("/api/integrations/calendar/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["authenticated"] is False
    assert body["login_url"] is None


def test_calendar_login_requires_configuration(client: TestClient) -> None:
    response = client.get("/api/integrations/calendar/login")

    assert response.status_code == 400


def test_calendar_login_redirects_to_google_authorization(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_calendar(monkeypatch)

    response = client.get("/api/integrations/calendar/login", follow_redirects=False)

    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=client-id" in location
    assert "access_type=offline" in location
    assert "calendar.events.readonly" in location


def test_calendar_today_reports_not_configured(client: TestClient) -> None:
    response = client.get("/api/integrations/calendar/events/today")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_configured"
    assert body["authenticated"] is False
    assert body["events"] == []


def test_calendar_today_maps_google_events(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_calendar(monkeypatch)
    authenticate_calendar()

    def fake_get(
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        assert url.endswith("/calendars/primary/events")
        assert kwargs["headers"]["Authorization"] == "Bearer access-token"
        params = kwargs["params"]
        assert params["singleEvents"] == "true"
        assert params["orderBy"] == "startTime"
        return httpx.Response(
            200,
            json={
                "timeZone": "Europe/London",
                "items": [
                    {
                        "id": "event-1",
                        "summary": "Design review",
                        "start": {"dateTime": "2026-06-02T09:30:00+01:00"},
                        "end": {"dateTime": "2026-06-02T10:00:00+01:00"},
                        "location": "Studio",
                        "organizer": {"displayName": "Mirrage"},
                        "htmlLink": "https://calendar.google.com/event?eid=1",
                    },
                    {
                        "id": "event-2",
                        "summary": "Project day",
                        "start": {"date": "2026-06-02"},
                        "end": {"date": "2026-06-03"},
                    },
                ],
            },
        )

    monkeypatch.setattr(calendar_service.httpx, "get", fake_get)

    response = client.get("/api/integrations/calendar/events/today")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["authenticated"] is True
    assert len(body["events"]) == 2
    assert body["events"][0]["title"] == "Design review"
    assert body["events"][0]["location"] == "Studio"
    assert body["events"][0]["is_all_day"] is False
    assert body["events"][1]["is_all_day"] is True


def test_calendar_upcoming_handles_empty_google_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_calendar(monkeypatch)
    authenticate_calendar()

    def fake_get(
        _url: str,
        **_kwargs: Any,
    ) -> httpx.Response:
        return httpx.Response(200, json={"items": [], "timeZone": "Europe/London"})

    monkeypatch.setattr(calendar_service.httpx, "get", fake_get)

    response = client.get("/api/integrations/calendar/events/upcoming?days=3")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["events"] == []
    assert body["message"] == "No calendar events found."
