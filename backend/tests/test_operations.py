"""Tests for production operations helpers."""

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.logging_config import JsonLogFormatter
from backend.app.schemas import MemoryCreateRequest, WeatherResponse
from backend.app.services import health as health_service
from backend.app.services.backups import create_memory_backup, restore_memory_backup
from backend.app.services.memory import create_memory, list_memories
from backend.app.services.startup import validate_environment
from backend.app.settings import settings


def test_api_health_is_online(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"service": "mirrage-api", "status": "online"}


def test_full_health_reports_operational_components(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        settings,
        "memory_database_path",
        str(tmp_path / "health-memory.sqlite3"),
    )
    monkeypatch.setattr(
        health_service,
        "get_weather",
        lambda: WeatherResponse(
            status="online",
            location="Test",
            temperature_c=20.0,
            condition="Clear",
            updated="2026-07-01T12:00:00+00:00",
        ),
    )
    monkeypatch.setattr(
        health_service,
        "get_calendar_status",
        lambda: SimpleNamespace(
            configured=False,
            authenticated=False,
            calendar_id="primary",
            message="Calendar not configured.",
        ),
    )
    monkeypatch.setattr(
        health_service,
        "get_spotify_status",
        lambda: SimpleNamespace(
            configured=False,
            authenticated=False,
            message="Spotify not configured.",
        ),
    )

    response = client.get("/api/health/full")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "mirrage-api"
    assert body["status"] in {"ok", "degraded"}
    component_names = {check["name"] for check in body["checks"]}
    assert {
        "backend",
        "environment",
        "memory",
        "ai_runtime",
        "providers",
        "presence",
        "weather",
        "calendar",
        "spotify",
    }.issubset(component_names)


def test_environment_validation_reports_invalid_log_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "log_level", "LOUD")

    issues = validate_environment()

    assert any(issue.field == "MIRRAGE_LOG_LEVEL" for issue in issues)
    assert any(issue.level == "error" for issue in issues)


def test_json_logging_uses_safe_operational_fields_only() -> None:
    record = logging.LogRecord(
        name="mirrage.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Provider selected.",
        args=(),
        exc_info=None,
    )
    record.provider = "ollama"
    record.task_type = "conversation"
    record.api_key = "should-not-appear"

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["provider"] == "ollama"
    assert payload["task_type"] == "conversation"
    assert "api_key" not in payload
    assert "should-not-appear" not in json.dumps(payload)


def test_memory_backup_and_restore(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "memory.sqlite3"
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(settings, "memory_database_path", str(database_path))
    monkeypatch.setattr(settings, "backup_directory", str(backup_dir))

    create_memory(
        MemoryCreateRequest(
            kind="preference",
            key="favorite drink",
            value="coffee",
        )
    )
    backup = create_memory_backup()
    create_memory(
        MemoryCreateRequest(
            kind="preference",
            key="favorite drink",
            value="tea",
        )
    )

    restore = restore_memory_backup(backup.destination)
    memories = list_memories(kind="preference").items

    assert backup.status == "created"
    assert restore.status == "restored"
    assert Path(backup.destination).exists()
    assert memories[0].value == "coffee"
