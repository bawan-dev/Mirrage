"""Tests for wake word and assistant presence endpoints."""

from fastapi.testclient import TestClient


def test_presence_status_defaults_to_idle(client: TestClient) -> None:
    response = client.get("/api/presence/status")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "idle"
    assert body["wake_phrase"] == "Hey Mirrage"
    assert body["wake_word_enabled"] is True
    assert body["wake_word_engine"] == "adapter"


def test_presence_settings_can_be_updated(client: TestClient) -> None:
    response = client.patch(
        "/api/presence/settings",
        json={
            "wake_phrase": "Mirror",
            "sensitivity": 0.7,
            "automatic_sleep": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["wake_phrase"] == "Mirror"
    assert body["sensitivity"] == 0.7
    assert body["automatic_sleep"] is False


def test_presence_transition_updates_state(client: TestClient) -> None:
    response = client.post(
        "/api/presence/transition",
        json={
            "state": "listening",
            "event": "test_listen",
            "source": "test",
            "message": "Listening in test.",
            "interim_transcript": "hello",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "listening"
    assert body["previous_state"] == "idle"
    assert body["interim_transcript"] == "hello"


def test_wake_word_detection_moves_to_wake_detected(client: TestClient) -> None:
    response = client.post(
        "/api/wake-word/detect",
        json={
            "phrase": "Hey Mirrage",
            "engine": "test-engine",
            "confidence": 0.9,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "wake_detected"
    assert body["event"] == "wake_word_detected"


def test_wake_word_rejects_wrong_phrase(client: TestClient) -> None:
    response = client.post(
        "/api/wake-word/detect",
        json={"phrase": "Hey mirror"},
    )

    assert response.status_code == 400
    assert "did not match" in response.json()["detail"]


def test_assistant_message_updates_presence_to_speaking(client: TestClient) -> None:
    response = client.post("/api/assistant/message", json={"message": "hello"})

    assert response.status_code == 200

    presence = client.get("/api/presence/status")
    assert presence.status_code == 200
    body = presence.json()
    assert body["state"] == "speaking"
    assert body["transcript"] == "hello"
    assert body["assistant_reply"]
