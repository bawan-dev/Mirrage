"""API route definitions."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from backend.app.schemas import (
    AssistantMessageRequest,
    AssistantMessageResponse,
    CalendarScheduleResponse,
    CalendarStatusResponse,
    MemoryCreateRequest,
    MemoryKind,
    MemoryRecordResponse,
    MemorySearchResponse,
    MemoryStatus,
    MemorySummaryResponse,
    MemoryUpdateRequest,
    SpotifyActionResponse,
    SpotifyPlaybackResponse,
    SpotifyStatusResponse,
    WeatherResponse,
)
from backend.app.services.assistant import create_assistant_reply
from backend.app.services.calendar import (
    CalendarAuthError,
    CalendarServiceError,
    build_calendar_authorization_url,
    complete_calendar_authorization,
    get_calendar_status,
    get_today_schedule,
    get_upcoming_events,
)
from backend.app.services.memory import (
    MemoryNotFoundError,
    create_memory,
    list_memories,
    summarize_memories,
    update_memory,
)
from backend.app.services.spotify import (
    SpotifyAuthError,
    SpotifyServiceError,
    build_authorization_url,
    complete_authorization,
    get_current_playback,
    get_spotify_status,
    run_player_action,
)
from backend.app.services.system import get_system_status
from backend.app.services.voice import get_voice_status
from backend.app.services.weather import get_weather
from backend.app.settings import settings

router = APIRouter()


@router.get("/")
def read_root() -> dict[str, str]:
    return {
        "service": "mirrage-api",
        "status": "online",
    }


@router.get("/health")
def read_health() -> dict[str, str]:
    return {
        "service": "mirrage-api",
        "status": "online",
    }


@router.get("/api/system/status")
def read_system_status() -> dict[str, str]:
    return get_system_status()


@router.get("/api/voice/status")
def read_voice_status() -> dict[str, str | bool]:
    return get_voice_status()


@router.get("/api/info/weather")
def read_weather() -> WeatherResponse:
    return get_weather()


@router.post("/api/assistant/message")
def create_assistant_message(
    message: AssistantMessageRequest,
) -> AssistantMessageResponse:
    return create_assistant_reply(message)


@router.get("/api/memory")
def read_memories(
    kind: MemoryKind | None = None,
    q: str | None = None,
    status: MemoryStatus | None = "active",
) -> MemorySearchResponse:
    return list_memories(kind=kind, query=q, status=status)


@router.get("/api/memory/summary")
def read_memory_summary() -> MemorySummaryResponse:
    return summarize_memories()


@router.post("/api/memory")
def create_memory_record(memory: MemoryCreateRequest) -> MemoryRecordResponse:
    return create_memory(memory)


@router.patch("/api/memory/{memory_id}")
def update_memory_record(
    memory_id: int,
    update: MemoryUpdateRequest,
) -> MemoryRecordResponse:
    try:
        return update_memory(memory_id, update)
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/integrations/calendar/status")
def read_calendar_status() -> CalendarStatusResponse:
    return get_calendar_status()


@router.get("/api/integrations/calendar/login")
def start_calendar_login() -> RedirectResponse:
    try:
        return RedirectResponse(build_calendar_authorization_url())
    except CalendarAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/integrations/calendar/callback")
def complete_calendar_login(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        return RedirectResponse(f"{settings.frontend_url}?calendar=error")

    if not code or not state:
        return RedirectResponse(f"{settings.frontend_url}?calendar=missing_callback")

    try:
        complete_calendar_authorization(code, state)
    except CalendarServiceError:
        return RedirectResponse(f"{settings.frontend_url}?calendar=error")

    return RedirectResponse(f"{settings.frontend_url}?calendar=connected")


@router.get("/api/integrations/calendar/events/today")
def read_calendar_today() -> CalendarScheduleResponse:
    try:
        return get_today_schedule()
    except CalendarServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/integrations/calendar/events/upcoming")
def read_calendar_upcoming(days: int = 7) -> CalendarScheduleResponse:
    try:
        return get_upcoming_events(days)
    except CalendarServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/integrations/spotify/status")
def read_spotify_status() -> SpotifyStatusResponse:
    return get_spotify_status()


@router.get("/api/integrations/spotify/login")
def start_spotify_login() -> RedirectResponse:
    try:
        return RedirectResponse(build_authorization_url())
    except SpotifyAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/integrations/spotify/callback")
def complete_spotify_login(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        return RedirectResponse(f"{settings.frontend_url}?spotify=error")

    if not code or not state:
        return RedirectResponse(f"{settings.frontend_url}?spotify=missing_callback")

    try:
        complete_authorization(code, state)
    except SpotifyServiceError:
        return RedirectResponse(f"{settings.frontend_url}?spotify=error")

    return RedirectResponse(f"{settings.frontend_url}?spotify=connected")


@router.get("/api/integrations/spotify/player/currently-playing")
def read_spotify_currently_playing() -> SpotifyPlaybackResponse:
    try:
        return get_current_playback()
    except SpotifyAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except SpotifyServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/api/integrations/spotify/player/{action}")
def control_spotify_player(action: str) -> SpotifyActionResponse:
    try:
        return run_player_action(action)
    except SpotifyAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except SpotifyServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
