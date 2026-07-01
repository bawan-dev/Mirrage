"""Tests for the dashboard-facing API endpoints."""

import pytest
from fastapi.testclient import TestClient

from ai.models import RuntimeResult
from backend.app.services import assistant as assistant_service


def test_system_status_reports_all_layers(client: TestClient) -> None:
    response = client.get("/api/system/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "online"
    for layer in ("frontend", "backend", "ai", "voice", "hardware"):
        assert layer in body


def test_voice_status_reports_presence_engine(client: TestClient) -> None:
    response = client.get("/api/voice/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["listening"] is False
    assert body["wake_word"] == "enabled"
    assert body["wake_phrase"] == "Hey Mirrage"
    assert body["presence_state"] == "idle"


def test_assistant_message_returns_stub_reply(client: TestClient) -> None:
    response = client.post("/api/assistant/message", json={"message": "hello"})

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "stub"
    assert body["model"] is None
    assert isinstance(body["reply"], str)
    assert body["reply"]


def test_assistant_message_rejects_empty_message(client: TestClient) -> None:
    response = client.post("/api/assistant/message", json={"message": ""})

    assert response.status_code == 422


def test_assistant_message_requires_message_field(client: TestClient) -> None:
    response = client.post("/api/assistant/message", json={})

    assert response.status_code == 422


def test_assistant_message_handles_runtime_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(_message: str) -> RuntimeResult:
        return RuntimeResult(
            reply="The AI runtime is unavailable right now.",
            provider="runtime",
            model=None,
            task_type="conversation",
            runtime_mode="test",
            used_fallback=True,
            context_sources=[],
        )

    monkeypatch.setattr(
        assistant_service.assistant_runtime,
        "run_assistant_request",
        unavailable,
    )

    response = client.post("/api/assistant/message", json={"message": "hi"})

    assert response.status_code == 200
    assert "unavailable" in response.json()["reply"].lower()
