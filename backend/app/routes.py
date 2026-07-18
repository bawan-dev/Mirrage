"""API route definitions."""

# FastAPI dependencies are intentionally declared in parameter defaults.
# ruff: noqa: B008

from fastapi import APIRouter, Depends, HTTPException
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
    WakeEngineActionResponse,
    WakeEngineStatusResponse,
    WakeWordDetectionRequest,
    WeatherResponse,
)
from backend.app.services.assistant import create_assistant_reply
from backend.app.services.audit import record_sensitive_access
from backend.app.services.authentication import require_permission
from backend.app.services.authorization import (
    authorization_service,
    required_assistant_permission,
)
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
from backend.app.services.identity_models import (
    AuthenticatedPrincipal,
    AuthorizationRequest,
)
from backend.app.services.identity_store import identity_store
from backend.app.services.memory import (
    MemoryNotFoundError,
    create_memory,
    list_memories,
    summarize_memories,
    update_memory,
)
from backend.app.services.permissions import Permission
from backend.app.services.presence import assistant_state_manager
from backend.app.services.proactive import get_proactive_summary
from backend.app.services.smart_home import smart_home_service
from backend.app.services.smart_home_models import (
    SmartHomeConfigurationError,
    SmartHomeProviderError,
    SmartHomeSafetyError,
    entity_domain,
    risk_classification,
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
from backend.app.services.wake_engine import wake_engine_service
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
def read_full_health(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.HEALTH_FULL_READ.value)
    ),
) -> HealthResponse:
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
def update_presence_settings(
    update: PresenceSettingsUpdate,
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.SYSTEM_ADMIN.value, risk_level="low")
    ),
) -> PresenceSettings:
    return assistant_state_manager.update_settings(update)


@router.post("/api/presence/transition")
def create_presence_transition(
    transition: PresenceTransitionRequest,
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.ASSISTANT_USE.value, risk_level="low")
    ),
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
    result = wake_word_service.handle_detection(request)
    if not result.accepted:
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return assistant_state_manager.snapshot()


@router.get("/api/wake-word/status")
def read_wake_word_status() -> WakeEngineStatusResponse:
    return wake_engine_service.status()


@router.post("/api/wake-word/start")
def start_wake_word_engine(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.SYSTEM_ADMIN.value, risk_level="low")
    ),
) -> WakeEngineActionResponse:
    return wake_engine_service.start()


@router.post("/api/wake-word/stop")
def stop_wake_word_engine(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.SYSTEM_ADMIN.value, risk_level="low")
    ),
) -> WakeEngineActionResponse:
    return wake_engine_service.stop()


@router.get("/api/info/weather")
def read_weather() -> WeatherResponse:
    return get_weather()


@router.get("/api/smart-home/status")
def read_smart_home_status(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.SMART_HOME_READ.value, resource_type="smart_home")
    ),
) -> SmartHomeStatusResponse:
    return smart_home_service.status()


@router.get("/api/smart-home/entities")
def read_smart_home_entities(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.SMART_HOME_READ.value, resource_type="smart_home")
    ),
) -> SmartHomeEntitiesResponse:
    return smart_home_service.entities_response()


@router.get("/api/smart-home/entities/{entity_id}")
def read_smart_home_entity(
    entity_id: str,
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.SMART_HOME_READ.value, resource_type="smart_home")
    ),
) -> SmartHomeEntityResponse:
    try:
        return smart_home_service.get_entity(entity_id)
    except SmartHomeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SmartHomeSafetyError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SmartHomeProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/smart-home/sensors")
def read_smart_home_sensors(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.SMART_HOME_READ.value, resource_type="smart_home")
    ),
) -> SmartHomeEntitiesResponse:
    return smart_home_service.sensors_response()


@router.post("/api/smart-home/entities/{entity_id}/turn-on")
def turn_on_smart_home_entity(
    entity_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            resource_type="smart_home",
            risk_level="low",
        )
    ),
) -> SmartHomeActionResponse:
    _authorize_smart_home_action(principal, entity_id, "turn_on")
    return _run_smart_home_action(
        lambda: smart_home_service.turn_on(entity_id),
        principal=principal,
        entity_id=entity_id,
        action="turn_on",
    )


@router.post("/api/smart-home/entities/{entity_id}/turn-off")
def turn_off_smart_home_entity(
    entity_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            resource_type="smart_home",
            risk_level="low",
        )
    ),
) -> SmartHomeActionResponse:
    _authorize_smart_home_action(principal, entity_id, "turn_off")
    return _run_smart_home_action(
        lambda: smart_home_service.turn_off(entity_id),
        principal=principal,
        entity_id=entity_id,
        action="turn_off",
    )


@router.post("/api/smart-home/scenes/{entity_id}/activate")
def activate_smart_home_scene(
    entity_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            resource_type="smart_home",
            risk_level="low",
        )
    ),
) -> SmartHomeActionResponse:
    _authorize_smart_home_action(principal, entity_id, "activate")
    return _run_smart_home_action(
        lambda: smart_home_service.activate_scene(entity_id),
        principal=principal,
        entity_id=entity_id,
        action="activate",
    )


@router.post("/api/smart-home/services/{domain}/{service}")
def block_arbitrary_smart_home_service(
    domain: str,
    service: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            resource_type="smart_home",
            risk_level="low",
        )
    ),
) -> SmartHomeActionResponse:
    decision = authorization_service.decide(
        principal,
        AuthorizationRequest(
            permission=Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            resource_type="smart_home",
            resource_id=f"{domain}.{service}",
            risk_level="high",
            context={"smart_home_domain": domain, "arbitrary_service": True},
        ),
    )
    identity_store.append_audit_event(
        event_type="smart_home_control_attempt",
        principal=principal,
        action=service,
        resource_type="smart_home",
        resource_id=domain,
        authorization_decision="denied",
        risk_level="high",
        reason=decision.policy_id,
        result="blocked",
    )
    raise HTTPException(
        status_code=403,
        detail="Arbitrary Home Assistant service calls are blocked.",
    )


def _run_smart_home_action(
    operation,
    *,
    principal: AuthenticatedPrincipal,
    entity_id: str,
    action: str,
) -> SmartHomeActionResponse:
    identity_store.append_audit_event(
        event_type="smart_home_control_attempt",
        principal=principal,
        action=action,
        resource_type="smart_home",
        resource_id=entity_id,
        authorization_decision="allowed",
        risk_level="low",
        result="attempted",
    )
    try:
        response = operation()
    except SmartHomeConfigurationError as exc:
        _audit_smart_home_result(principal, entity_id, action, "configuration_error")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SmartHomeSafetyError as exc:
        _audit_smart_home_result(principal, entity_id, action, "blocked")
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SmartHomeProviderError as exc:
        _audit_smart_home_result(principal, entity_id, action, "provider_error")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    _audit_smart_home_result(principal, entity_id, action, "success")
    return response


@router.post("/api/assistant/message")
def create_assistant_message(
    message: AssistantMessageRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.ASSISTANT_USE.value, risk_level="low")
    ),
) -> AssistantMessageResponse:
    _authorize_assistant_private_intent(message.message, principal)
    voice_pipeline.processing(message.message)
    response = create_assistant_reply(message)
    voice_pipeline.speaking(response.reply, transcript=message.message)
    return response


@router.post("/api/assistant/stream")
def stream_assistant_message(
    message: AssistantMessageRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.ASSISTANT_USE.value, risk_level="low")
    ),
) -> StreamingResponse:
    _authorize_assistant_private_intent(message.message, principal)
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
def read_daily_context(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.CONTEXT_READ_PRIVATE.value)
    ),
) -> DailyContext:
    response = get_daily_context()
    record_sensitive_access(
        principal, action="context.daily.read", resource_type="personal_context"
    )
    return response


@router.get("/api/proactive/summary")
def read_proactive_summary(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.CONTEXT_READ_PRIVATE.value)
    ),
) -> ProactiveSummaryResponse:
    response = get_proactive_summary()
    record_sensitive_access(
        principal, action="context.proactive.read", resource_type="personal_context"
    )
    return response


@router.get("/api/memory")
def read_memories(
    kind: MemoryKind | None = None,
    q: str | None = None,
    status: MemoryStatus | None = "active",
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.MEMORY_READ_PRIVATE.value)
    ),
) -> MemorySearchResponse:
    response = list_memories(kind=kind, query=q, status=status)
    record_sensitive_access(
        principal, action="memory.list", resource_type="private_memory"
    )
    return response


@router.get("/api/memory/summary")
def read_memory_summary(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.MEMORY_READ_PRIVATE.value)
    ),
) -> MemorySummaryResponse:
    response = summarize_memories()
    record_sensitive_access(
        principal, action="memory.summary", resource_type="private_memory"
    )
    return response


@router.post("/api/memory")
def create_memory_record(
    memory: MemoryCreateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.MEMORY_WRITE_PRIVATE.value, risk_level="low")
    ),
) -> MemoryRecordResponse:
    response = create_memory(memory)
    identity_store.append_audit_event(
        event_type="sensitive_memory_write",
        principal=principal,
        action="memory.create",
        resource_type="private_memory",
        resource_id=str(response.id),
        authorization_decision="allowed",
        risk_level="low",
        result="success",
    )
    return response


@router.patch("/api/memory/{memory_id}")
def update_memory_record(
    memory_id: int,
    update: MemoryUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.MEMORY_WRITE_PRIVATE.value, risk_level="low")
    ),
) -> MemoryRecordResponse:
    try:
        response = update_memory(memory_id, update)
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    identity_store.append_audit_event(
        event_type="sensitive_memory_write",
        principal=principal,
        action="memory.update",
        resource_type="private_memory",
        resource_id=str(memory_id),
        authorization_decision="allowed",
        risk_level="low",
        result="success",
    )
    return response


@router.get("/api/integrations/calendar/status")
def read_calendar_status(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.CALENDAR_READ_PRIVATE.value)
    ),
) -> CalendarStatusResponse:
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
def read_calendar_today(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.CALENDAR_READ_PRIVATE.value)
    ),
) -> CalendarScheduleResponse:
    try:
        response = get_today_schedule()
    except CalendarServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    record_sensitive_access(
        principal, action="calendar.today.read", resource_type="private_calendar"
    )
    return response


@router.get("/api/integrations/calendar/events/upcoming")
def read_calendar_upcoming(
    days: int = 7,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.CALENDAR_READ_PRIVATE.value)
    ),
) -> CalendarScheduleResponse:
    try:
        response = get_upcoming_events(days)
    except CalendarServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    record_sensitive_access(
        principal, action="calendar.upcoming.read", resource_type="private_calendar"
    )
    return response


@router.get("/api/integrations/spotify/status")
def read_spotify_status(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.MEDIA_READ.value)
    ),
) -> SpotifyStatusResponse:
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
def read_spotify_currently_playing(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.MEDIA_READ.value)
    ),
) -> SpotifyPlaybackResponse:
    try:
        return get_current_playback()
    except SpotifyAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except SpotifyServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/api/integrations/spotify/player/{action}")
def control_spotify_player(
    action: str,
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.MEDIA_CONTROL.value, risk_level="low")
    ),
) -> SpotifyActionResponse:
    try:
        return run_player_action(action)
    except SpotifyAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except SpotifyServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _authorize_assistant_private_intent(
    message: str, principal: AuthenticatedPrincipal
) -> None:
    permission = required_assistant_permission(message)
    if permission is None:
        return
    decision = authorization_service.decide(
        principal,
        AuthorizationRequest(
            permission=permission,
            resource_type="assistant_private_intent",
            risk_level="low" if permission.endswith("write_private") else "read_only",
        ),
    )
    if decision.decision != "allowed":
        raise HTTPException(
            status_code=403,
            detail={
                "decision": decision.decision,
                "reason": decision.reason,
                "permission": permission,
                "policy_id": decision.policy_id,
            },
        )


def _authorize_smart_home_action(
    principal: AuthenticatedPrincipal, entity_id: str, action: str
) -> None:
    try:
        domain = entity_domain(entity_id)
    except SmartHomeSafetyError as exc:
        identity_store.append_audit_event(
            event_type="smart_home_control_attempt",
            principal=principal,
            action=action,
            resource_type="smart_home",
            resource_id=entity_id,
            authorization_decision="denied",
            risk_level="high",
            reason="smart_home.entity.invalid",
            result="blocked",
        )
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    risk = risk_classification(domain)
    normalized_risk = risk if risk in {"read_only", "low", "high"} else "high"
    decision = authorization_service.decide(
        principal,
        AuthorizationRequest(
            permission=Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            resource_type="smart_home",
            resource_id=entity_id,
            risk_level=normalized_risk,
            context={"smart_home_domain": domain, "action": action},
        ),
    )
    if decision.decision != "allowed":
        identity_store.append_audit_event(
            event_type="smart_home_control_attempt",
            principal=principal,
            action=action,
            resource_type="smart_home",
            resource_id=entity_id,
            authorization_decision=decision.decision,
            risk_level=normalized_risk,
            reason=decision.policy_id,
            result="blocked",
        )
        raise HTTPException(status_code=403, detail=decision.reason)


def _audit_smart_home_result(
    principal: AuthenticatedPrincipal, entity_id: str, action: str, result: str
) -> None:
    identity_store.append_audit_event(
        event_type="smart_home_control_result",
        principal=principal,
        action=action,
        resource_type="smart_home",
        resource_id=entity_id,
        authorization_decision="allowed",
        risk_level="low",
        result=result,
    )
