"""Tests for the local wake engine boundary."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import routes
from backend.app.services import health as health_service
from backend.app.services.wake_engine import WakeEngineService
from backend.app.services.wake_engine_models import (
    WakeEngineConfig,
    validate_wake_engine_config,
)
from backend.app.settings import settings


def test_wake_engine_status_defaults_to_disabled(client: TestClient) -> None:
    response = client.get("/api/wake-word/status")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["configured"] is False
    assert body["provider"] == "openwakeword"
    assert body["status"] == "disabled"
    assert "model_path" not in body


def test_wake_engine_enabled_without_model_reports_unconfigured(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "wake_engine_enabled", True)
    monkeypatch.setattr(settings, "wake_engine_model_path", None)

    response = client.get("/api/wake-word/status")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["configured"] is False
    assert body["status"] == "unconfigured"
    assert "model path is not configured" in body["message"]


def test_wake_engine_model_path_validation(tmp_path: Path) -> None:
    config = WakeEngineConfig(
        enabled=True,
        provider="openwakeword",
        model_path=str(tmp_path / "missing.onnx"),
        phrase="Hey Mirrage",
        sensitivity=0.5,
        microphone=None,
        sample_rate=16000,
        frame_ms=80,
        cooldown_seconds=3,
    )

    issues = validate_wake_engine_config(config)

    assert "Wake engine model file was not found." in issues


def test_wake_engine_sensitivity_validation() -> None:
    config = WakeEngineConfig(
        enabled=False,
        provider="openwakeword",
        model_path=None,
        phrase="Hey Mirrage",
        sensitivity=1.2,
        microphone=None,
        sample_rate=16000,
        frame_ms=80,
        cooldown_seconds=3,
    )

    issues = validate_wake_engine_config(config)

    assert "Wake engine sensitivity must be between 0.0 and 1.0." in issues


def test_wake_detection_cooldown_suppresses_duplicates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "wake_engine_cooldown_seconds", 30)

    first = client.post("/api/wake-word/detect", json={"phrase": "Hey Mirrage"})
    second = client.post("/api/wake-word/detect", json={"phrase": "Hey Mirrage"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert "cooldown" in second.json()["detail"]


def test_wake_engine_start_stop_endpoints_default_to_safe_disabled(
    client: TestClient,
) -> None:
    start = client.post("/api/wake-word/start")
    stop = client.post("/api/wake-word/stop")

    assert start.status_code == 200
    assert start.json()["status"] == "disabled"
    assert stop.status_code == 200
    assert stop.json()["status"] == "stopped"


def test_wake_engine_start_stop_with_fake_provider(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeProvider:
        name = "openwakeword"

        def listen(
            self,
            _config: WakeEngineConfig,
            stop_event: threading.Event,
            _on_detection,
        ) -> None:
            stop_event.wait(timeout=5)

    model_path = tmp_path / "hey-mirrage.onnx"
    model_path.write_text("fake test model", encoding="utf-8")
    monkeypatch.setattr(settings, "wake_engine_enabled", True)
    monkeypatch.setattr(settings, "wake_engine_model_path", str(model_path))

    service = WakeEngineService(provider_factory=lambda _config: FakeProvider())
    monkeypatch.setattr(routes, "wake_engine_service", service)

    start = client.post("/api/wake-word/start")
    status = client.get("/api/wake-word/status")
    stop = client.post("/api/wake-word/stop")

    assert start.status_code == 200
    assert start.json()["status"] == "starting"
    assert status.status_code == 200
    assert status.json()["running"] is True
    assert stop.status_code == 200
    assert stop.json()["status"] == "stopped"


def test_detect_endpoint_emits_presence_source(client: TestClient) -> None:
    response = client.post(
        "/api/wake-word/detect",
        json={
            "phrase": "Hey Mirrage",
            "engine": "openwakeword",
            "source": "wake_engine:openwakeword",
            "confidence": 0.84,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "wake_detected"
    assert body["source"] == "wake_engine:openwakeword"


def test_full_health_includes_wake_engine(client: TestClient) -> None:
    response = client.get("/api/health/full")

    assert response.status_code == 200
    checks = {check["name"]: check for check in response.json()["checks"]}
    assert "wake_engine" in checks
    assert checks["wake_engine"]["details"]["provider"] == "openwakeword"


def test_health_reports_missing_enabled_model_without_exposing_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret_like_path = tmp_path / "private-model.onnx"
    monkeypatch.setattr(settings, "wake_engine_enabled", True)
    monkeypatch.setattr(settings, "wake_engine_model_path", str(secret_like_path))

    response = client.get("/api/health/full")

    assert response.status_code == 200
    payload = response.json()
    checks = {check["name"]: check for check in payload["checks"]}
    assert checks["wake_engine"]["status"] == "unavailable"
    assert "private-model.onnx" not in json.dumps(payload)


def test_voice_status_includes_local_wake_engine(client: TestClient) -> None:
    response = client.get("/api/voice/status")

    assert response.status_code == 200
    body = response.json()
    assert body["local_wake_engine"] == "disabled"
    assert body["local_wake_engine_provider"] == "openwakeword"


def test_environment_validation_checks_wake_engine_sensitivity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "wake_engine_sensitivity", -0.1)

    issues = health_service.validate_environment()

    assert any(
        issue.field == "MIRRAGE_WAKE_ENGINE_SENSITIVITY" and issue.level == "error"
        for issue in issues
    )
