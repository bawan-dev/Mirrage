"""Tests for the weather endpoint, with the network mocked out."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.services import weather


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self._payload


@pytest.fixture(autouse=True)
def _clear_weather_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(weather, "_cache_value", None)
    monkeypatch.setattr(weather, "_cache_expires", 0.0)


def test_weather_returns_live_data(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(*_args: Any, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(
            {
                "current": {
                    "temperature_2m": 12.3,
                    "weather_code": 3,
                    "time": "2026-05-30T10:00",
                }
            }
        )

    monkeypatch.setattr(weather.httpx, "get", fake_get)

    response = client.get("/api/info/weather")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "online"
    assert body["temperature_c"] == 12.3
    assert body["condition"] == "Overcast"


def test_weather_handles_failure_gracefully(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise weather.httpx.HTTPError("network down")

    monkeypatch.setattr(weather.httpx, "get", boom)

    response = client.get("/api/info/weather")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["temperature_c"] is None
