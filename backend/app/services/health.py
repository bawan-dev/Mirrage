"""Health monitoring for Mirrage backend services."""

from __future__ import annotations

from datetime import UTC, datetime

from ai.router import provider_router
from ai.runtime import assistant_runtime
from backend.app.schemas import HealthComponentResponse, HealthResponse
from backend.app.services.calendar import get_calendar_status
from backend.app.services.memory import memory_health
from backend.app.services.presence import assistant_state_manager
from backend.app.services.smart_home import smart_home_service
from backend.app.services.spotify import get_spotify_status
from backend.app.services.startup import validate_environment
from backend.app.services.wake_engine import wake_engine_service
from backend.app.services.weather import get_weather


def basic_health() -> dict[str, str]:
    return {
        "service": "mirrage-api",
        "status": "online",
    }


def full_health() -> HealthResponse:
    checks = [
        _backend_check(),
        _environment_check(),
        _memory_check(),
        _ai_runtime_check(),
        _provider_check(),
        _presence_check(),
        _wake_engine_check(),
        _smart_home_check(),
        _weather_check(),
        _calendar_check(),
        _spotify_check(),
    ]

    return HealthResponse(
        service="mirrage-api",
        status=_overall_status(checks),
        generated_at=datetime.now(UTC).isoformat(),
        checks=checks,
    )


def _backend_check() -> HealthComponentResponse:
    return HealthComponentResponse(
        name="backend",
        status="ok",
        message="Backend process is running.",
    )


def _environment_check() -> HealthComponentResponse:
    issues = validate_environment()
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]

    if errors:
        return HealthComponentResponse(
            name="environment",
            status="error",
            message=f"{len(errors)} startup configuration error(s) found.",
            details={"fields": [issue.field for issue in errors]},
        )

    if warnings:
        return HealthComponentResponse(
            name="environment",
            status="warning",
            message=f"{len(warnings)} startup configuration warning(s) found.",
            details={"fields": [issue.field for issue in warnings]},
        )

    return HealthComponentResponse(
        name="environment",
        status="ok",
        message="Startup configuration is valid.",
    )


def _memory_check() -> HealthComponentResponse:
    try:
        result = memory_health()
    except Exception as exc:
        return HealthComponentResponse(
            name="memory",
            status="error",
            message="Memory database health check failed.",
            details={"error": exc.__class__.__name__},
        )

    return HealthComponentResponse(
        name="memory",
        status=result["status"],
        message=result["message"],
        details={
            "database_path": result["database_path"],
            "record_count": result["record_count"],
        },
    )


def _ai_runtime_check() -> HealthComponentResponse:
    status = assistant_runtime.runtime_status()
    return HealthComponentResponse(
        name="ai_runtime",
        status="ok",
        message="AI runtime is configured.",
        details={
            "configured_provider": status["configured_provider"],
            "fallback_provider": status["fallback_provider"],
            "local_first": status["local_first"],
            "local_only": status["local_only"],
            "streaming_enabled": status["streaming_enabled"],
            "privacy_mode": status["privacy_mode"],
        },
    )


def _provider_check() -> HealthComponentResponse:
    providers = provider_router.provider_status()
    configured = [provider for provider in providers if provider["configured"]]

    return HealthComponentResponse(
        name="providers",
        status="ok" if configured else "warning",
        message=f"{len(configured)} provider(s) are configured.",
        details={"providers": providers},
    )


def _presence_check() -> HealthComponentResponse:
    snapshot = assistant_state_manager.snapshot()
    return HealthComponentResponse(
        name="presence",
        status="ok",
        message="Presence engine is running.",
        details={
            "state": snapshot.state,
            "wake_word_enabled": snapshot.wake_word_enabled,
            "wake_word_engine": snapshot.wake_word_engine,
        },
    )


def _wake_engine_check() -> HealthComponentResponse:
    status = wake_engine_service.status()

    if not status.enabled:
        check_status = "ok"
    elif status.running:
        check_status = "ok"
    elif status.configured:
        check_status = "warning"
    else:
        check_status = "unavailable"

    return HealthComponentResponse(
        name="wake_engine",
        status=check_status,
        message=status.message,
        details={
            "enabled": status.enabled,
            "configured": status.configured,
            "provider": status.provider,
            "status": status.status,
            "running": status.running,
            "phrase": status.phrase,
            "sensitivity": status.sensitivity,
            "microphone_configured": status.microphone_configured,
            "model_configured": status.model_configured,
            "sample_rate": status.sample_rate,
            "frame_ms": status.frame_ms,
            "cooldown_seconds": status.cooldown_seconds,
            "last_detection_time": status.last_detection_time,
            "last_detection_latency_ms": status.last_detection_latency_ms,
            "error_message": status.error_message,
        },
    )


def _smart_home_check() -> HealthComponentResponse:
    status = smart_home_service.status()
    if not status.enabled:
        check_status = "warning"
    elif status.connection_status == "connected":
        check_status = "ok"
    elif status.connection_status in {"unconfigured", "provider_disabled"}:
        check_status = "warning"
    else:
        check_status = "unavailable"

    return HealthComponentResponse(
        name="smart_home",
        status=check_status,
        message=status.message,
        details={
            "enabled": status.enabled,
            "configured": status.configured,
            "provider": status.provider,
            "connection_status": status.connection_status,
            "entity_count": status.entity_count,
            "supported_domains": status.supported_domains,
            "last_successful_sync": status.last_successful_sync,
        },
    )


def _weather_check() -> HealthComponentResponse:
    try:
        weather = get_weather()
    except Exception as exc:
        return HealthComponentResponse(
            name="weather",
            status="warning",
            message="Weather health check failed.",
            details={"error": exc.__class__.__name__},
        )

    return HealthComponentResponse(
        name="weather",
        status="ok" if weather.status == "online" else "warning",
        message=f"Weather status is {weather.status}.",
        details={
            "provider": "open-meteo",
            "status": weather.status,
            "location": weather.location,
            "updated": weather.updated,
        },
    )


def _calendar_check() -> HealthComponentResponse:
    status = get_calendar_status()
    return HealthComponentResponse(
        name="calendar",
        status="ok" if status.configured and status.authenticated else "warning",
        message=status.message,
        details={
            "configured": status.configured,
            "authenticated": status.authenticated,
            "calendar_id": status.calendar_id,
        },
    )


def _spotify_check() -> HealthComponentResponse:
    status = get_spotify_status()
    return HealthComponentResponse(
        name="spotify",
        status="ok" if status.configured and status.authenticated else "warning",
        message=status.message,
        details={
            "configured": status.configured,
            "authenticated": status.authenticated,
        },
    )


def _overall_status(checks: list[HealthComponentResponse]) -> str:
    statuses = {check.status for check in checks}
    if "error" in statuses:
        return "error"
    if statuses.intersection({"warning", "unavailable"}):
        return "degraded"
    return "ok"
