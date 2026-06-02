"""Tests for the Spotify integration API boundary."""

import time
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.services import spotify as spotify_service


@pytest.fixture(autouse=True)
def reset_spotify(monkeypatch: pytest.MonkeyPatch) -> None:
    spotify_service._reset_for_tests()
    monkeypatch.setattr(spotify_service.settings, "spotify_client_id", None)
    monkeypatch.setattr(spotify_service.settings, "spotify_client_secret", None)
    monkeypatch.setattr(
        spotify_service.settings,
        "spotify_redirect_uri",
        "http://127.0.0.1:8000/api/integrations/spotify/callback",
    )


def configure_spotify(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spotify_service.settings, "spotify_client_id", "client-id")
    monkeypatch.setattr(
        spotify_service.settings,
        "spotify_client_secret",
        "client-secret",
    )


def authenticate_spotify() -> None:
    spotify_service._token_state = spotify_service.SpotifyTokenState(
        access_token="access-token",
        refresh_token="refresh-token",
        expires_at=time.time() + 3600,
        scopes=spotify_service.SPOTIFY_SCOPES,
    )


def test_spotify_status_reports_missing_configuration(client: TestClient) -> None:
    response = client.get("/api/integrations/spotify/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["authenticated"] is False
    assert body["login_url"] is None


def test_spotify_login_requires_configuration(client: TestClient) -> None:
    response = client.get("/api/integrations/spotify/login")

    assert response.status_code == 400


def test_spotify_login_redirects_to_authorization_url(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_spotify(monkeypatch)

    response = client.get("/api/integrations/spotify/login", follow_redirects=False)

    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith("https://accounts.spotify.com/authorize?")
    assert "client_id=client-id" in location
    assert "user-read-currently-playing" in location
    assert "user-modify-playback-state" in location


def test_spotify_currently_playing_maps_track_payload(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_spotify(monkeypatch)
    authenticate_spotify()

    def fake_request(
        method: str,
        url: str,
        **_kwargs: Any,
    ) -> httpx.Response:
        assert method == "GET"
        assert url.endswith("/me/player/currently-playing")
        return httpx.Response(
            200,
            json={
                "is_playing": True,
                "progress_ms": 42000,
                "device": {"name": "Office speaker", "type": "Computer"},
                "item": {
                    "name": "Night Drive",
                    "duration_ms": 180000,
                    "external_urls": {"spotify": "https://open.spotify.com/track/1"},
                    "artists": [{"name": "Mirrage Test"}],
                    "album": {
                        "name": "Mirror Sessions",
                        "images": [
                            {
                                "url": "https://example.com/small.jpg",
                                "width": 64,
                                "height": 64,
                            },
                            {
                                "url": "https://example.com/large.jpg",
                                "width": 640,
                                "height": 640,
                            },
                        ],
                    },
                },
            },
        )

    monkeypatch.setattr(spotify_service.httpx, "request", fake_request)

    response = client.get("/api/integrations/spotify/player/currently-playing")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "playing"
    assert body["is_playing"] is True
    assert body["title"] == "Night Drive"
    assert body["artist"] == "Mirrage Test"
    assert body["album"] == "Mirror Sessions"
    assert body["artwork_url"] == "https://example.com/large.jpg"
    assert body["device_name"] == "Office speaker"


def test_spotify_currently_playing_handles_no_active_playback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_spotify(monkeypatch)
    authenticate_spotify()

    def fake_request(
        _method: str,
        _url: str,
        **_kwargs: Any,
    ) -> httpx.Response:
        return httpx.Response(204)

    monkeypatch.setattr(spotify_service.httpx, "request", fake_request)

    response = client.get("/api/integrations/spotify/player/currently-playing")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_active_playback"
    assert body["title"] is None


def test_spotify_player_action_calls_expected_endpoint(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_spotify(monkeypatch)
    authenticate_spotify()
    calls: list[tuple[str, str]] = []

    def fake_request(
        method: str,
        url: str,
        **_kwargs: Any,
    ) -> httpx.Response:
        calls.append((method, url))
        return httpx.Response(204)

    monkeypatch.setattr(spotify_service.httpx, "request", fake_request)

    response = client.post("/api/integrations/spotify/player/next")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert calls == [("POST", "https://api.spotify.com/v1/me/player/next")]
