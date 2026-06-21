"""Tests for the local memory layer."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.settings import settings


@pytest.fixture(autouse=True)
def memory_database_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        settings,
        "memory_database_path",
        str(tmp_path / "mirrage-test-memory.sqlite3"),
    )


def test_memory_record_can_be_created_and_listed(client: TestClient) -> None:
    response = client.post(
        "/api/memory",
        json={
            "kind": "preference",
            "key": "temperature unit",
            "value": "celsius",
        },
    )

    assert response.status_code == 200
    created = response.json()
    assert created["kind"] == "preference"
    assert created["key"] == "temperature unit"
    assert created["value"] == "celsius"
    assert created["status"] == "active"

    list_response = client.get("/api/memory?kind=preference")

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["count"] == 1
    assert body["items"][0]["key"] == "temperature unit"


def test_memory_create_upserts_existing_kind_and_key(client: TestClient) -> None:
    first = client.post(
        "/api/memory",
        json={"kind": "fact", "key": "home city", "value": "London"},
    )
    second = client.post(
        "/api/memory",
        json={"kind": "fact", "key": "home city", "value": "Manchester"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["value"] == "Manchester"

    list_response = client.get("/api/memory?kind=fact")
    assert list_response.json()["count"] == 1


def test_memory_record_can_be_updated(client: TestClient) -> None:
    created = client.post(
        "/api/memory",
        json={"kind": "goal", "key": "prototype", "value": "build frame"},
    ).json()

    response = client.patch(
        f"/api/memory/{created['id']}",
        json={"value": "test display", "status": "done"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["value"] == "test display"
    assert updated["status"] == "done"


def test_memory_summary_groups_records(client: TestClient) -> None:
    client.post(
        "/api/memory",
        json={"kind": "preference", "key": "weather units", "value": "celsius"},
    )
    client.post(
        "/api/memory",
        json={"kind": "routine", "key": "morning", "value": "check calendar"},
    )

    response = client.get("/api/memory/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["preferences"][0]["key"] == "weather units"
    assert body["routines"][0]["key"] == "morning"


def test_assistant_can_store_and_retrieve_memory(client: TestClient) -> None:
    store_response = client.post(
        "/api/assistant/message",
        json={"message": "remember my favorite drink is coffee"},
    )

    assert store_response.status_code == 200
    stored = store_response.json()
    assert stored["provider"] == "memory"
    assert stored["memory_action"] == "stored"
    assert "favorite drink" in stored["reply"]

    recall_response = client.post(
        "/api/assistant/message",
        json={"message": "what do you remember about me?"},
    )

    assert recall_response.status_code == 200
    recalled = recall_response.json()
    assert recalled["provider"] == "memory"
    assert recalled["memory_action"] == "retrieved"
    assert "favorite drink: coffee" in recalled["reply"]


def test_assistant_can_update_memory(client: TestClient) -> None:
    client.post(
        "/api/assistant/message",
        json={"message": "remember my favorite drink is coffee"},
    )

    response = client.post(
        "/api/assistant/message",
        json={"message": "update my favorite drink to tea"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "memory"
    assert body["memory_action"] == "updated"

    summary = client.get("/api/memory/summary").json()
    assert summary["preferences"][0]["value"] == "tea"
