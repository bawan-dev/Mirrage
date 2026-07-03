"""API route definitions."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse

from ai.router import provider_router
from ai.runtime import assistant_runtime
from backend.app.schemas import (
    AIProvidersResponse,
    AIRuntimeStatusResponse,
    AssistantMessageRequest,
    AssistantMessageResponse,
    CalendarScheduleResponse,
    CalendarStatusResponse,
    DailyContext,
    HealthResponse,
    MemoryCreateRequest,
    MemoryKind,
    MemoryRecordResponse,
    MemorySearchResponse,
    MemoryStatus,
    MemorySummaryResponse,
    MemoryUpdateRequest,
    PresenceSettings,
    PresenceSettingsUpdate,
    PresenceSnapshot,
    PresenceTransitionRequest,
    ProactiveSummaryResponse,
    SmartHomeActionResponse,
    SmartHomeEntitiesResponse,
    SmartHomeEntityResponse,
    SmartHomeStatusResponse,
    SpotifyActionResponse,
    SpotifyPlaybackResponse,
    SpotifyStatusResponse,
    WakeWordDetectionRequest,
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
from backend.app.services.context import get_daily_context
from backend.app.services.health import basic_health, full_health
from backend.app.services.memory import (
    MemoryNotFoundError,
    create_memory,
    list_memories,
    summarize_memories,
    update_memory,
)
from backend.app.services.presence import assistant_state_manager
from backend.app.services.proactive import get_proactive_summary
from backend.app.services.smart_home import smart_home_service
from backend.app.services.smart_home_models import (
    SmartHomeConfigurationError,
    SmartHomeProviderError,
    SmartHomeSafetyError,
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
from backend.app.services.voice_pipeline import voice_pipeline
from backend.app.services.wake_word import wake_word_service
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
    return basic_health()


@router.get("/api/health")
def read_api_health() -> dict[str, str]:
    return basic_health()


@router.get("/api/health/full")
def read_full_health() -> HealthResponse:
    return full_health()


@router.get("/api/system/status")
def read_system_status() -> dict[str, str]:
    return get_system_status()


@router.get("/api/voice/status")
def read_voice_status() -> dict[str, str | bool | float | None]:
    return get_voice_status()


@router.get("/api/ai/runtime/status")
def read_ai_runtime_status() -> AIRuntimeStatusResponse:
    return AIRuntimeStatusResponse(**assistant_runtime.runtime_status())


@router.get("/api/ai/providers")
def read_ai_providers() -> AIProvidersResponse:
    return AIProvidersResponse(providers=provider_router.provider_status())


@router.get("/api/presence/status")
def read_presence_status() -> PresenceSnapshot:
    return assistant_state_manager.snapshot()


@router.get("/api/presence/events")
async def read_presence_events() -> StreamingResponse:
    return StreamingResponse(
        assistant_state_manager.events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/presence/settings")
def read_presence_settings() -> PresenceSettings:
    return assistant_state_manager.settings()


@router.patch("/api/presence/settings")
def update_presence_settings(update: PresenceSettingsUpdate) -> PresenceSettings:
    return assistant_state_manager.update_settings(update)


@router.post("/api/presence/transition")
def create_presence_transition(
    transition: PresenceTransitionRequest,
) -> PresenceSnapshot:
    return assistant_state_manager.transition(
        transition.state,
        event=transition.event or "manual_transition",
        source=transition.source,
        message=transition.message or f"Assistant state changed to {transition.state}.",
        transcript=transition.transcript,
        interim_transcript=transition.interim_transcript,
        assistant_reply=transition.assistant_reply,
    )


@router.post("/api/wake-word/detect")
def detect_wake_word(request: WakeWordDetectionRequest) -> PresenceSnapshot:
    matched, message = wake_word_service.handle_detection(request)
    if not matched:
        raise HTTPException(status_code=400, detail=message)
    return assistant_state_manager.snapshot()


@router.get("/api/info/weather")
def read_weather() -> WeatherResponse:
    return get_weather()


@router.get("/api/smart-home/status")
def read_smart_home_status() -> SmartHomeStatusResponse:
    return smart_home_service.status()


@router.get("/api/smart-home/entities")
def read_smart_home_entities() -> SmartHomeEntitiesResponse:
    return smart_home_service.entities_response()


@router.get("/api/smart-home/entities/{entity_id}")
def read_smart_home_entity(entity_id: str) -> SmartHomeEntityResponse:
    try:
        return smart_home_service.get_entity(entity_id)
    except SmartHomeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SmartHomeSafetyError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SmartHomeProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/smart-home/sensors")
def read_smart_home_sensors() -> SmartHomeEntitiesResponse:
    return smart_home_service.sensors_response()


@router.post("/api/smart-home/entities/{entity_id}/turn-on")
def turn_on_smart_home_entity(entity_id: str) -> SmartHomeActionResponse:
    return _run_smart_home_action(lambda: smart_home_service.turn_on(entity_id))


@router.post("/api/smart-home/entities/{entity_id}/turn-off")
def turn_off_smart_home_entity(entity_id: str) -> SmartHomeActionResponse:
    return _run_smart_home_action(lambda: smart_home_service.turn_off(entity_id))


@router.post("/api/smart-home/scenes/{entity_id}/activate")
def activate_smart_home_scene(entity_id: str) -> SmartHomeActionResponse:
    return _run_smart_home_action(lambda: smart_home_service.activate_scene(entity_id))


@router.post("/api/smart-home/services/{domain}/{service}")
def block_arbitrary_smart_home_service(
    domain: str,
    service: str,
) -> SmartHomeActionResponse:
    raise HTTPException(
        status_code=403,
        detail="Arbitrary Home Assistant service calls are blocked.",
    )


def _run_smart_home_action(action) -> SmartHomeActionResponse:
    try:
        return action()
    except SmartHomeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SmartHomeSafetyError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SmartHomeProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/api/assistant/message")
def create_assistant_message(
    message: AssistantMessageRequest,
) -> AssistantMessageResponse:
    voice_pipeline.processing(message.message)
    response = create_assistant_reply(message)
    voice_pipeline.speaking(response.reply, transcript=message.message)
    return response


@router.post("/api/assistant/stream")
def stream_assistant_message(message: AssistantMessageRequest) -> StreamingResponse:
    voice_pipeline.processing(message.message)
    return StreamingResponse(
        assistant_runtime.stream_assistant_request(message.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/context/daily")
def read_daily_context() -> DailyContext:
    return get_daily_context()


@router.get("/api/proactive/summary")
def read_proactive_summary() -> ProactiveSummaryResponse:
    return get_proactive_summary()


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
