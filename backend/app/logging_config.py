"""Structured logging setup for the backend."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from logging import LogRecord
from pathlib import Path

from backend.app.settings import settings

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_SAFE_EXTRA_FIELDS = (
    "engine",
    "fallback_provider",
    "field",
    "local",
    "model",
    "provider",
    "source",
    "state",
    "previous_state",
    "task_type",
)


class JsonLogFormatter(logging.Formatter):
    """Small JSON formatter that keeps logs machine-readable."""

    def format(self, record: LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        event = getattr(record, "event", None)
        if event:
            payload["event"] = str(event)

        subsystem = getattr(record, "subsystem", None)
        if subsystem:
            payload["subsystem"] = str(subsystem)

        for field in _SAFE_EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, separators=(",", ":"))


def configure_logging() -> None:
    """Configure root logging once at process startup."""

    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if settings.log_file:
        Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(settings.log_file, encoding="utf-8"))

    formatter: logging.Formatter
    if settings.log_json:
        formatter = JsonLogFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    for handler in handlers:
        handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    for handler in handlers:
        root_logger.addHandler(handler)


def valid_log_level(level: str) -> bool:
    return level.upper() in _VALID_LEVELS
