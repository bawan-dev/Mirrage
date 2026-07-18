"""Startup validation for production and local deployments."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ai.config import ai_settings
from ai.router import PROVIDER_DEFINITIONS
from backend.app.logging_config import valid_log_level
from backend.app.services.identity_store import identity_store
from backend.app.services.wake_engine_models import (
    FUTURE_WAKE_ENGINE_PROVIDERS,
    SUPPORTED_WAKE_ENGINE_PROVIDERS,
)
from backend.app.settings import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StartupIssue:
    level: str
    field: str
    message: str


def validate_environment() -> list[StartupIssue]:
    """Return startup issues without exposing secret values."""

    issues: list[StartupIssue] = []

    if settings.app_env not in {"development", "test", "production"}:
        issues.append(
            StartupIssue(
                level="warning",
                field="MIRRAGE_APP_ENV",
                message=(
                    "Use development, test, or production for predictable behavior."
                ),
            )
        )

    if not valid_log_level(settings.log_level):
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_LOG_LEVEL",
                message="Log level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL.",
            )
        )

    if not settings.memory_database_path.strip():
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_MEMORY_DATABASE_PATH",
                message="Memory database path is required.",
            )
        )

    if not settings.backup_directory.strip():
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_BACKUP_DIRECTORY",
                message="Backup directory is required.",
            )
        )

    if settings.identity_mode not in {"development", "enforced", "disabled"}:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_IDENTITY_MODE",
                message="Identity mode must be development, enforced, or disabled.",
            )
        )

    if settings.identity_enabled and not settings.identity_database_path.strip():
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_IDENTITY_DATABASE_PATH",
                message="Identity database path is required when identity is enabled.",
            )
        )

    if settings.identity_device_token_bytes < 32:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_IDENTITY_DEVICE_TOKEN_BYTES",
                message="Trusted-device tokens must contain at least 32 random bytes.",
            )
        )

    if settings.identity_session_ttl_seconds <= 0:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_IDENTITY_SESSION_TTL_SECONDS",
                message="Identity session TTL must be greater than zero.",
            )
        )
    if not 60 <= settings.human_session_ttl_seconds <= 86400:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_HUMAN_SESSION_TTL_SECONDS",
                message="Human session lifetime must be between 60 and 86400 seconds.",
            )
        )

    if settings.approval_ttl_seconds <= 0:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_APPROVAL_TTL_SECONDS",
                message="Approval TTL must be greater than zero.",
            )
        )

    if settings.audit_retention_days <= 0:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_AUDIT_RETENTION_DAYS",
                message="Audit retention must be at least one day.",
            )
        )

    identity_status: dict[str, object] | None = None
    if settings.identity_enabled and settings.identity_database_path.strip():
        try:
            identity_status = identity_store.status()
        except Exception:
            issues.append(
                StartupIssue(
                    level="error",
                    field="MIRRAGE_IDENTITY_DATABASE_PATH",
                    message="Identity database could not be initialized or queried.",
                )
            )

    if settings.identity_mode == "enforced" and identity_status is not None:
        if not identity_status["owner_present"]:
            issues.append(
                StartupIssue(
                    level="error",
                    field="MIRRAGE_IDENTITY_DATABASE_PATH",
                    message="Enforced identity mode requires an active owner.",
                )
            )

    if not -90 <= settings.weather_latitude <= 90:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_WEATHER_LATITUDE",
                message="Weather latitude must be between -90 and 90.",
            )
        )

    if not -180 <= settings.weather_longitude <= 180:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_WEATHER_LONGITUDE",
                message="Weather longitude must be between -180 and 180.",
            )
        )

    if not 0 <= settings.wake_word_sensitivity <= 1:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_WAKE_WORD_SENSITIVITY",
                message="Wake-word sensitivity must be between 0.0 and 1.0.",
            )
        )

    if settings.presence_inactivity_timeout_seconds < 5:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_PRESENCE_INACTIVITY_TIMEOUT_SECONDS",
                message="Presence inactivity timeout must be at least 5 seconds.",
            )
        )

    if settings.smart_home_timeout_seconds <= 0:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_SMART_HOME_TIMEOUT_SECONDS",
                message="Smart home timeout must be greater than zero.",
            )
        )

    if settings.wake_engine_provider in FUTURE_WAKE_ENGINE_PROVIDERS:
        issues.append(
            StartupIssue(
                level="warning",
                field="MIRRAGE_WAKE_ENGINE_PROVIDER",
                message=(
                    "Porcupine is documented as a future option, but this build "
                    "currently implements the OpenWakeWord boundary."
                ),
            )
        )
    elif settings.wake_engine_provider not in SUPPORTED_WAKE_ENGINE_PROVIDERS:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_WAKE_ENGINE_PROVIDER",
                message="Wake engine provider must currently be openwakeword.",
            )
        )

    if not 0 <= settings.wake_engine_sensitivity <= 1:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_WAKE_ENGINE_SENSITIVITY",
                message="Wake engine sensitivity must be between 0.0 and 1.0.",
            )
        )

    if settings.wake_engine_sample_rate <= 0:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_WAKE_ENGINE_SAMPLE_RATE",
                message="Wake engine sample rate must be greater than zero.",
            )
        )

    if settings.wake_engine_frame_ms <= 0:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_WAKE_ENGINE_FRAME_MS",
                message="Wake engine frame size must be greater than zero.",
            )
        )

    if settings.wake_engine_cooldown_seconds < 0:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_WAKE_ENGINE_COOLDOWN_SECONDS",
                message="Wake engine cooldown must be zero or greater.",
            )
        )

    if settings.wake_engine_enabled:
        if not settings.wake_engine_model_path:
            issues.append(
                StartupIssue(
                    level="warning",
                    field="MIRRAGE_WAKE_ENGINE_MODEL_PATH",
                    message=(
                        "Wake engine is enabled without a local model path. "
                        "The backend will stay online, but local wake detection "
                        "will not start."
                    ),
                )
            )
        elif not Path(settings.wake_engine_model_path).expanduser().exists():
            issues.append(
                StartupIssue(
                    level="warning",
                    field="MIRRAGE_WAKE_ENGINE_MODEL_PATH",
                    message=(
                        "Wake engine model file was not found. Local wake "
                        "detection will report unconfigured."
                    ),
                )
            )

    if settings.smart_home_enabled and not settings.home_assistant_enabled:
        issues.append(
            StartupIssue(
                level="warning",
                field="MIRRAGE_HOME_ASSISTANT_ENABLED",
                message="Smart home is enabled, but Home Assistant is disabled.",
            )
        )

    if (
        settings.smart_home_enabled
        and settings.home_assistant_enabled
        and not settings.home_assistant_token
    ):
        issues.append(
            StartupIssue(
                level="warning",
                field="MIRRAGE_HOME_ASSISTANT_TOKEN",
                message="Home Assistant is enabled without an access token.",
            )
        )

    if ai_settings.provider not in PROVIDER_DEFINITIONS:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_AI_PROVIDER",
                message="AI provider must be one of: stub, ollama, openai.",
            )
        )

    if ai_settings.fallback_provider not in PROVIDER_DEFINITIONS:
        issues.append(
            StartupIssue(
                level="error",
                field="MIRRAGE_AI_FALLBACK_PROVIDER",
                message="AI fallback provider must be one of: stub, ollama, openai.",
            )
        )

    if bool(settings.spotify_client_id) != bool(settings.spotify_client_secret):
        issues.append(
            StartupIssue(
                level="warning",
                field="MIRRAGE_SPOTIFY_CLIENT_ID",
                message=(
                    "Spotify client ID and client secret should be configured together."
                ),
            )
        )

    if bool(settings.google_calendar_client_id) != bool(
        settings.google_calendar_client_secret
    ):
        issues.append(
            StartupIssue(
                level="warning",
                field="MIRRAGE_GOOGLE_CALENDAR_CLIENT_ID",
                message=(
                    "Google Calendar client ID and secret should be configured "
                    "together."
                ),
            )
        )

    if settings.app_env == "production":
        if not settings.identity_enabled or settings.identity_mode != "enforced":
            issues.append(
                StartupIssue(
                    level="error",
                    field="MIRRAGE_IDENTITY_MODE",
                    message="Production requires enabled, enforced identity mode.",
                )
            )
        if settings.identity_dev_bypass:
            issues.append(
                StartupIssue(
                    level="error",
                    field="MIRRAGE_IDENTITY_DEV_BYPASS",
                    message=(
                        "The identity development bypass is forbidden in production."
                    ),
                )
            )
        if "*" in settings.allowed_origins:
            issues.append(
                StartupIssue(
                    level="error",
                    field="MIRRAGE_ALLOWED_ORIGINS",
                    message="Production should not allow wildcard CORS origins.",
                )
            )
        if "localhost" in settings.frontend_url:
            issues.append(
                StartupIssue(
                    level="warning",
                    field="MIRRAGE_FRONTEND_URL",
                    message="Production frontend URL still points at localhost.",
                )
            )

    return issues


def run_startup_validation() -> None:
    """Log startup checks and fail fast for hard configuration errors."""

    _ensure_runtime_directories()
    issues = validate_environment()

    logger.info(
        "Mirrage backend startup validation completed.",
        extra={"event": "startup_validation", "subsystem": "startup"},
    )

    for issue in issues:
        log = logger.error if issue.level == "error" else logger.warning
        log(
            issue.message,
            extra={
                "event": "startup_validation_issue",
                "subsystem": "startup",
                "field": issue.field,
            },
        )

    errors = [issue for issue in issues if issue.level == "error"]
    if errors:
        raise RuntimeError(
            "Mirrage startup validation failed: "
            + ", ".join(issue.field for issue in errors)
        )


def _ensure_runtime_directories() -> None:
    Path(settings.memory_database_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.identity_database_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.backup_directory).mkdir(parents=True, exist_ok=True)
