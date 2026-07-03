"""Tests for the smart home foundation and Home Assistant abstraction."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.schemas import WeatherResponse
from backend.app.services import health as health_service
from backend.app.services.smart_home import SmartHomeService
from backend.app.services.smart_home_models import (
    SmartHomeProviderError,
    SmartHomeSafetyError,
    normalize_entity,
)
from backend.app.settings import settings


class FakeHomeAssistantProvider:
    def __init__(
        self,
        states: list[dict] | None = None,
        *,
        configured: bool = True,
        fail_discovery: bool = False,
    ) -> None:
        self._states = states or []
        self.configured = configured
        self.fail_discovery = fail_discovery
        self.calls: list[tuple[str, str, str]] = []

    def states(self) -> list[dict]:
        if self.fail_discovery:
            raise SmartHomeProviderError("Home Assistant is unavailable right now.")
        return list(self._states)

    def state(self, entity_id: str) -> dict:
        for state in self._states:
            if state["entity_id"] == entity_id:
                return state
        raise SmartHomeProviderError("Smart home entity was not found.")

    def call_service(
        self,
        *,
        domain: str,
        service: str,
        entity_id: str,
    ) -> dict:
        self.calls.append((domain, service, entity_id))
        for state in self._states:
            if state["entity_id"] == entity_id:
                if service == "turn_on":
                    state["state"] = "on"
                elif service == "turn_off":
                    state["state"] = "off"
                return state
        return {}


def _states() -> list[dict]:
    return [
        {
            "entity_id": "light.kitchen",
            "state": "off",
            "attributes": {"friendly_name": "Kitchen Light", "area": "Kitchen"},
            "last_updated": "2026-07-02T09:00:00+00:00",
        },
        {
            "entity_id": "switch.fan",
            "state": "off",
            "attributes": {"friendly_name": "Fan"},
            "last_updated": "2026-07-02T09:00:00+00:00",
        },
        {
            "entity_id": "scene.evening",
            "state": "scening",
            "attributes": {"friendly_name": "Evening"},
            "last_updated": "2026-07-02T09:00:00+00:00",
        },
        {
            "entity_id": "sensor.hall_temperature",
            "state": "21.5",
            "attributes": {"friendly_name": "Hall Temperature"},
            "last_updated": "2026-07-02T09:00:00+00:00",
        },
        {
            "entity_id": "binary_sensor.front_door",
            "state": "off",
            "attributes": {"friendly_name": "Front Door"},
            "last_updated": "2026-07-02T09:00:00+00:00",
        },
        {
            "entity_id": "lock.front_door",
            "state": "locked",
            "attributes": {"friendly_name": "Front Door Lock"},
            "last_updated": "2026-07-02T09:00:00+00:00",
        },
    ]


@pytest.fixture
def enabled_smart_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smart_home_enabled", True)
    monkeypatch.setattr(settings, "home_assistant_enabled", True)
    monkeypatch.setattr(settings, "home_assistant_token", "secret-token")


def test_smart_home_disabled_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smart_home_enabled", False)

    service = SmartHomeService(FakeHomeAssistantProvider())

    status = service.status()
    assert status.enabled is False
    assert status.configured is False
    assert status.connection_status == "disabled"


def test_home_assistant_unconfigured_state(
    enabled_smart_home: None,
) -> None:
    service = SmartHomeService(FakeHomeAssistantProvider(configured=False))

    status = service.status()
    assert status.enabled is True
    assert status.configured is False
    assert status.connection_status == "unconfigured"


def test_entity_normalization() -> None:
    entity = normalize_entity(_states()[0])

    assert entity is not None
    assert entity.entity_id == "light.kitchen"
    assert entity.name == "Kitchen Light"
    assert entity.domain == "light"
    assert entity.device_type == "light"
    assert entity.supported_actions == ["turn_on", "turn_off"]
    assert entity.room == "Kitchen"


def test_supported_domain_filtering(enabled_smart_home: None) -> None:
    service = SmartHomeService(FakeHomeAssistantProvider(_states()))

    entities = service.discover_entities(refresh=True)
    entity_ids = {entity.entity_id for entity in entities}

    assert "light.kitchen" in entity_ids
    assert "switch.fan" in entity_ids
    assert "scene.evening" in entity_ids
    assert "sensor.hall_temperature" in entity_ids
    assert "binary_sensor.front_door" in entity_ids
    assert "lock.front_door" not in entity_ids


def test_device_discovery_failure(enabled_smart_home: None) -> None:
    service = SmartHomeService(
        FakeHomeAssistantProvider(_states(), fail_discovery=True)
    )

    response = service.entities_response()

    assert response.status == "unavailable"
    assert response.count == 0


def test_light_turn_on_and_off(enabled_smart_home: None) -> None:
    provider = FakeHomeAssistantProvider(_states())
    service = SmartHomeService(provider)

    turn_on = service.turn_on("light.kitchen")
    turn_off = service.turn_off("light.kitchen")

    assert turn_on.status == "ok"
    assert turn_on.entity is not None
    assert turn_on.entity.state == "on"
    assert turn_off.entity is not None
    assert turn_off.entity.state == "off"
    assert provider.calls[:2] == [
        ("light", "turn_on", "light.kitchen"),
        ("light", "turn_off", "light.kitchen"),
    ]


def test_switch_turn_on_and_off(enabled_smart_home: None) -> None:
    provider = FakeHomeAssistantProvider(_states())
    service = SmartHomeService(provider)

    service.turn_on("switch.fan")
    service.turn_off("switch.fan")

    assert provider.calls[:2] == [
        ("switch", "turn_on", "switch.fan"),
        ("switch", "turn_off", "switch.fan"),
    ]


def test_scene_activation(enabled_smart_home: None) -> None:
    provider = FakeHomeAssistantProvider(_states())
    service = SmartHomeService(provider)

    response = service.activate_scene("scene.evening")

    assert response.status == "ok"
    assert provider.calls == [("scene", "turn_on", "scene.evening")]


def test_sensor_is_read_only(enabled_smart_home: None) -> None:
    service = SmartHomeService(FakeHomeAssistantProvider(_states()))

    with pytest.raises(SmartHomeSafetyError, match="Sensors are read-only"):
        service.turn_on("sensor.hall_temperature")


def test_unsupported_domain_is_blocked(enabled_smart_home: None) -> None:
    service = SmartHomeService(FakeHomeAssistantProvider(_states()))

    with pytest.raises(SmartHomeSafetyError, match="high-risk"):
        service.turn_on("lock.front_door")


def test_arbitrary_service_call_route_is_blocked(client: TestClient) -> None:
    response = client.post("/api/smart-home/services/light/turn_on")

    assert response.status_code == 403
    assert "blocked" in response.json()["detail"].lower()


def test_home_assistant_token_not_exposed(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "smart_home_enabled", True)
    monkeypatch.setattr(settings, "home_assistant_enabled", True)
    monkeypatch.setattr(settings, "home_assistant_token", "secret-token")

    response = client.get("/api/smart-home/status")

    assert response.status_code == 200
    assert "secret-token" not in json.dumps(response.json())


def test_full_health_includes_smart_home_without_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "smart_home_enabled", False)
    monkeypatch.setattr(settings, "home_assistant_token", "secret-token")
    monkeypatch.setattr(
        health_service,
        "get_weather",
        lambda: WeatherResponse(
            status="online",
            location="Test",
            temperature_c=20.0,
            condition="Clear",
            updated="2026-07-02T09:00:00+00:00",
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
    names = {check["name"] for check in body["checks"]}
    assert "smart_home" in names
    assert "secret-token" not in json.dumps(body)
