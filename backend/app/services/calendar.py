"""Google Calendar API integration boundary."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from backend.app.schemas import (
    CalendarEventResponse,
    CalendarScheduleResponse,
    CalendarStatusResponse,
)
from backend.app.settings import settings

GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events.readonly",
]

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_API_BASE_URL = "https://www.googleapis.com/calendar/v3"
_REQUEST_TIMEOUT = 10.0


class CalendarServiceError(RuntimeError):
    """Raised when Google Calendar cannot complete a requested operation."""


class CalendarAuthError(CalendarServiceError):
    """Raised when Google Calendar credentials or auth state are missing."""


@dataclass
class CalendarTokenState:
    access_token: str
    refresh_token: str | None
    expires_at: float
    scopes: list[str]


_token_state: CalendarTokenState | None = None
_pending_states: set[str] = set()


def _calendar_id() -> str:
    return settings.google_calendar_id or "primary"


def _time_zone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.google_calendar_time_zone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _is_configured() -> bool:
    return bool(
        settings.google_calendar_client_id and settings.google_calendar_client_secret
    )


def _require_configured() -> None:
    if not _is_configured():
        raise CalendarAuthError("Google Calendar is not configured.")


def _store_token(payload: dict[str, Any]) -> None:
    global _token_state

    refresh_token = payload.get("refresh_token")
    if not refresh_token and _token_state is not None:
        refresh_token = _token_state.refresh_token

    _token_state = CalendarTokenState(
        access_token=payload["access_token"],
        refresh_token=refresh_token,
        expires_at=time.time() + int(payload.get("expires_in", 3600)) - 30,
        scopes=str(payload.get("scope", "")).split(),
    )


def _google_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"Google Calendar request failed with status {response.status_code}."

    error = body.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if message:
            return str(message)
    if isinstance(error, str):
        description = body.get("error_description")
        if description:
            return str(description)
        return error
    return f"Google Calendar request failed with status {response.status_code}."


def build_calendar_authorization_url() -> str:
    """Create a Google OAuth authorization URL for Calendar access."""
    _require_configured()

    state = secrets.token_urlsafe(24)
    _pending_states.add(state)

    return f"{_AUTH_URL}?" + urlencode(
        {
            "access_type": "offline",
            "client_id": settings.google_calendar_client_id,
            "include_granted_scopes": "true",
            "prompt": "consent",
            "redirect_uri": settings.google_calendar_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_CALENDAR_SCOPES),
            "state": state,
        }
    )


def complete_calendar_authorization(code: str, state: str) -> None:
    """Exchange Google's callback code for Calendar API tokens."""
    _require_configured()

    if state not in _pending_states:
        raise CalendarAuthError("Google Calendar authorization state did not match.")

    _pending_states.remove(state)

    response = httpx.post(
        _TOKEN_URL,
        data={
            "client_id": settings.google_calendar_client_id,
            "client_secret": settings.google_calendar_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.google_calendar_redirect_uri,
        },
        timeout=_REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        raise CalendarServiceError(_google_error(response))

    _store_token(response.json())


def _refresh_token() -> None:
    _require_configured()

    if _token_state is None or not _token_state.refresh_token:
        raise CalendarAuthError("Google Calendar is not connected.")

    response = httpx.post(
        _TOKEN_URL,
        data={
            "client_id": settings.google_calendar_client_id,
            "client_secret": settings.google_calendar_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": _token_state.refresh_token,
        },
        timeout=_REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        raise CalendarServiceError(_google_error(response))

    _store_token(response.json())


def _access_token() -> str:
    if _token_state is None:
        raise CalendarAuthError("Google Calendar is not connected.")

    if time.time() >= _token_state.expires_at:
        _refresh_token()

    if _token_state is None:
        raise CalendarAuthError("Google Calendar is not connected.")

    return _token_state.access_token


def _calendar_request(
    path: str,
    *,
    params: dict[str, str | int | bool],
) -> httpx.Response:
    token = _access_token()

    response = httpx.get(
        f"{_API_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=_REQUEST_TIMEOUT,
    )

    if (
        response.status_code == 401
        and _token_state is not None
        and _token_state.refresh_token
    ):
        _refresh_token()
        token = _access_token()
        response = httpx.get(
            f"{_API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=_REQUEST_TIMEOUT,
        )

    if response.status_code != 200:
        raise CalendarServiceError(_google_error(response))

    return response


def get_calendar_status() -> CalendarStatusResponse:
    if not _is_configured():
        return CalendarStatusResponse(
            configured=False,
            authenticated=False,
            login_url=None,
            calendar_id=_calendar_id(),
            scopes=GOOGLE_CALENDAR_SCOPES,
            message="Google Calendar client credentials are not configured.",
        )

    if _token_state is None:
        return CalendarStatusResponse(
            configured=True,
            authenticated=False,
            login_url="/api/integrations/calendar/login",
            calendar_id=_calendar_id(),
            scopes=GOOGLE_CALENDAR_SCOPES,
            message="Google Calendar is configured but not connected.",
        )

    return CalendarStatusResponse(
        configured=True,
        authenticated=True,
        login_url=None,
        calendar_id=_calendar_id(),
        scopes=_token_state.scopes or GOOGLE_CALENDAR_SCOPES,
        message="Google Calendar is connected.",
    )


def _empty_schedule(
    *,
    date: datetime,
    status: str,
    message: str,
) -> CalendarScheduleResponse:
    return CalendarScheduleResponse(
        status=status,
        authenticated=_token_state is not None,
        date=date.date().isoformat(),
        time_zone=settings.google_calendar_time_zone,
        events=[],
        updated=datetime.now(UTC).isoformat(),
        message=message,
    )


def _event_time(
    event_time: dict[str, Any] | None,
) -> tuple[str | None, bool]:
    if not isinstance(event_time, dict):
        return None, False

    if "date" in event_time:
        return str(event_time["date"]), True

    if "dateTime" in event_time:
        return str(event_time["dateTime"]), False

    return None, False


def _calendar_event_from_payload(event: dict[str, Any]) -> CalendarEventResponse:
    start, start_is_all_day = _event_time(event.get("start"))
    end, end_is_all_day = _event_time(event.get("end"))

    return CalendarEventResponse(
        id=str(event.get("id") or ""),
        title=str(event.get("summary") or "Untitled event"),
        start=start or "",
        end=end,
        is_all_day=start_is_all_day or end_is_all_day,
        location=event.get("location"),
        calendar=event.get("organizer", {}).get("displayName")
        if isinstance(event.get("organizer"), dict)
        else None,
        html_link=event.get("htmlLink"),
    )


def _events_path() -> str:
    return f"/calendars/{quote(_calendar_id(), safe='')}/events"


def _schedule_between(
    *,
    end: datetime,
    max_results: int,
    start: datetime,
    status: str,
) -> CalendarScheduleResponse:
    if not _is_configured():
        return _empty_schedule(
            date=start,
            status="not_configured",
            message="Google Calendar client credentials are not configured.",
        )

    if _token_state is None:
        return _empty_schedule(
            date=start,
            status="not_authenticated",
            message="Google Calendar is not connected.",
        )

    response = _calendar_request(
        _events_path(),
        params={
            "maxResults": max_results,
            "orderBy": "startTime",
            "singleEvents": "true",
            "timeMax": end.isoformat(),
            "timeMin": start.isoformat(),
            "timeZone": settings.google_calendar_time_zone,
        },
    )
    payload = response.json()
    events = [
        _calendar_event_from_payload(event)
        for event in payload.get("items", [])
        if isinstance(event, dict)
    ]

    return CalendarScheduleResponse(
        status=status,
        authenticated=True,
        date=start.date().isoformat(),
        time_zone=str(payload.get("timeZone") or settings.google_calendar_time_zone),
        events=events,
        updated=datetime.now(UTC).isoformat(),
        message=(
            f"{len(events)} event{'s' if len(events) != 1 else ''} found."
            if events
            else "No calendar events found."
        ),
    )


def get_today_schedule() -> CalendarScheduleResponse:
    tz = _time_zone()
    start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    return _schedule_between(
        end=end,
        max_results=20,
        start=start,
        status="ready",
    )


def get_upcoming_events(days: int = 7) -> CalendarScheduleResponse:
    tz = _time_zone()
    start = datetime.now(tz)
    bounded_days = min(max(days, 1), 31)
    end = start + timedelta(days=bounded_days)

    return _schedule_between(
        end=end,
        max_results=30,
        start=start,
        status="ready",
    )


def _reset_for_tests() -> None:
    global _token_state

    _token_state = None
    _pending_states.clear()
