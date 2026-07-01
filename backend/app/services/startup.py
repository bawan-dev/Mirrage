"""Startup validation for production and local deployments."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ai.config import ai_settings
from ai.router import PROVIDER_DEFINITIONS
from backend.app.logging_config import valid_log_level
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
    Path(settings.backup_directory).mkdir(parents=True, exist_ok=True)
