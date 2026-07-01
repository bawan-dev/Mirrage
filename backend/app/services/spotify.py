"""Spotify Web API integration boundary."""

from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from backend.app.schemas import (
    SpotifyActionResponse,
    SpotifyPlaybackResponse,
    SpotifyStatusResponse,
)
from backend.app.settings import settings

SPOTIFY_SCOPES = [
    "user-read-currently-playing",
    "user-read-playback-state",
    "user-modify-playback-state",
]

_AUTH_URL = "https://accounts.spotify.com/authorize"
_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_BASE_URL = "https://api.spotify.com/v1"
_REQUEST_TIMEOUT = 10.0
logger = logging.getLogger(__name__)


class SpotifyServiceError(RuntimeError):
    """Raised when Spotify cannot complete a requested operation."""


class SpotifyAuthError(SpotifyServiceError):
    """Raised when Spotify credentials or authorization state are missing."""


@dataclass
class SpotifyTokenState:
    access_token: str
    refresh_token: str | None
    expires_at: float
    scopes: list[str]


_token_state: SpotifyTokenState | None = None
_pending_states: set[str] = set()


def _is_configured() -> bool:
    return bool(settings.spotify_client_id and settings.spotify_client_secret)


def _require_configured() -> None:
    if not _is_configured():
        raise SpotifyAuthError("Spotify is not configured.")


def _auth_headers() -> tuple[str, str]:
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        raise SpotifyAuthError("Spotify client credentials are missing.")
    return (settings.spotify_client_id, settings.spotify_client_secret)


def _store_token(payload: dict[str, Any]) -> None:
    global _token_state

    refresh_token = payload.get("refresh_token")
    if not refresh_token and _token_state is not None:
        refresh_token = _token_state.refresh_token

    _token_state = SpotifyTokenState(
        access_token=payload["access_token"],
        refresh_token=refresh_token,
        expires_at=time.time() + int(payload.get("expires_in", 3600)) - 30,
        scopes=str(payload.get("scope", "")).split(),
    )


def _spotify_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"Spotify request failed with status {response.status_code}."

    error = body.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if message:
            return str(message)
    if isinstance(error, str):
        description = body.get("error_description")
        if description:
            return str(description)
        return error
    return f"Spotify request failed with status {response.status_code}."


def build_authorization_url() -> str:
    """Create a Spotify authorization URL for the current browser session."""
    _require_configured()

    state = secrets.token_urlsafe(24)
    _pending_states.add(state)

    return f"{_AUTH_URL}?" + urlencode(
        {
            "response_type": "code",
            "client_id": settings.spotify_client_id,
            "scope": " ".join(SPOTIFY_SCOPES),
            "redirect_uri": settings.spotify_redirect_uri,
            "state": state,
        }
    )


def complete_authorization(code: str, state: str) -> None:
    """Exchange Spotify's callback code for an access and refresh token."""
    _require_configured()

    if state not in _pending_states:
        raise SpotifyAuthError("Spotify authorization state did not match.")

    _pending_states.remove(state)

    response = httpx.post(
        _TOKEN_URL,
        auth=_auth_headers(),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.spotify_redirect_uri,
        },
        timeout=_REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        logger.warning(
            "Spotify token exchange failed.",
            extra={"event": "integration_auth_failed", "subsystem": "spotify"},
        )
        raise SpotifyServiceError(_spotify_error(response))

    _store_token(response.json())


def _refresh_token() -> None:
    _require_configured()

    if _token_state is None or not _token_state.refresh_token:
        raise SpotifyAuthError("Spotify is not connected.")

    response = httpx.post(
        _TOKEN_URL,
        auth=_auth_headers(),
        data={
            "grant_type": "refresh_token",
            "refresh_token": _token_state.refresh_token,
        },
        timeout=_REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        logger.warning(
            "Spotify token refresh failed.",
            extra={"event": "integration_auth_failed", "subsystem": "spotify"},
        )
        raise SpotifyServiceError(_spotify_error(response))

    _store_token(response.json())


def _access_token() -> str:
    if _token_state is None:
        raise SpotifyAuthError("Spotify is not connected.")

    if time.time() >= _token_state.expires_at:
        _refresh_token()

    if _token_state is None:
        raise SpotifyAuthError("Spotify is not connected.")

    return _token_state.access_token


def _spotify_request(
    method: str,
    path: str,
    *,
    expected_statuses: tuple[int, ...],
) -> httpx.Response:
    token = _access_token()

    response = httpx.request(
        method,
        f"{_API_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=_REQUEST_TIMEOUT,
    )

    if (
        response.status_code == 401
        and _token_state is not None
        and _token_state.refresh_token
    ):
        _refresh_token()
        token = _access_token()
        response = httpx.request(
            method,
            f"{_API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_REQUEST_TIMEOUT,
        )

    if response.status_code not in expected_statuses:
        logger.warning(
            "Spotify API request failed.",
            extra={"event": "integration_request_failed", "subsystem": "spotify"},
        )
        raise SpotifyServiceError(_spotify_error(response))

    return response


def get_spotify_status() -> SpotifyStatusResponse:
    if not _is_configured():
        return SpotifyStatusResponse(
            configured=False,
            authenticated=False,
            login_url=None,
            scopes=SPOTIFY_SCOPES,
            message="Spotify client credentials are not configured.",
        )

    if _token_state is None:
        return SpotifyStatusResponse(
            configured=True,
            authenticated=False,
            login_url="/api/integrations/spotify/login",
            scopes=SPOTIFY_SCOPES,
            message="Spotify is configured but not connected.",
        )

    return SpotifyStatusResponse(
        configured=True,
        authenticated=True,
        login_url=None,
        scopes=_token_state.scopes or SPOTIFY_SCOPES,
        message="Spotify is connected.",
    )


def _empty_playback(status: str, message: str) -> SpotifyPlaybackResponse:
    return SpotifyPlaybackResponse(
        status=status,
        authenticated=_token_state is not None,
        is_playing=False,
        title=None,
        artist=None,
        album=None,
        artwork_url=None,
        progress_ms=None,
        duration_ms=None,
        device_name=None,
        device_type=None,
        spotify_url=None,
        updated=datetime.now(UTC).isoformat(),
        message=message,
    )


def _best_artwork(images: list[dict[str, Any]]) -> str | None:
    if not images:
        return None

    sorted_images = sorted(
        images,
        key=lambda image: int(image.get("width") or image.get("height") or 0),
        reverse=True,
    )
    return sorted_images[0].get("url")


def _artist_text(item: dict[str, Any]) -> str | None:
    artists = item.get("artists")
    if not isinstance(artists, list):
        return None
    names = [artist.get("name") for artist in artists if isinstance(artist, dict)]
    return ", ".join(name for name in names if name) or None


def _playback_from_payload(payload: dict[str, Any]) -> SpotifyPlaybackResponse:
    item = payload.get("item") if isinstance(payload.get("item"), dict) else None
    device = payload.get("device") if isinstance(payload.get("device"), dict) else {}
    album = item.get("album") if item and isinstance(item.get("album"), dict) else {}
    images = album.get("images") if isinstance(album.get("images"), list) else []
    is_playing = bool(payload.get("is_playing"))

    return SpotifyPlaybackResponse(
        status="playing" if is_playing else "paused",
        authenticated=True,
        is_playing=is_playing,
        title=item.get("name") if item else None,
        artist=_artist_text(item) if item else None,
        album=album.get("name") if album else None,
        artwork_url=_best_artwork(images),
        progress_ms=payload.get("progress_ms"),
        duration_ms=item.get("duration_ms") if item else None,
        device_name=device.get("name"),
        device_type=device.get("type"),
        spotify_url=(
            item.get("external_urls", {}).get("spotify")
            if item and isinstance(item.get("external_urls"), dict)
            else None
        ),
        updated=datetime.now(UTC).isoformat(),
        message="Spotify playback loaded.",
    )


def get_current_playback() -> SpotifyPlaybackResponse:
    if not _is_configured():
        return _empty_playback(
            "not_configured",
            "Spotify client credentials are not configured.",
        )

    if _token_state is None:
        return _empty_playback("not_authenticated", "Spotify is not connected.")

    response = _spotify_request(
        "GET",
        "/me/player/currently-playing",
        expected_statuses=(200, 204),
    )

    if response.status_code == 204 or not response.content:
        return _empty_playback("no_active_playback", "No active Spotify playback.")

    return _playback_from_payload(response.json())


def run_player_action(action: str) -> SpotifyActionResponse:
    action_map = {
        "play": ("PUT", "/me/player/play", "Playback resumed."),
        "pause": ("PUT", "/me/player/pause", "Playback paused."),
        "next": ("POST", "/me/player/next", "Skipped to next track."),
        "previous": ("POST", "/me/player/previous", "Skipped to previous track."),
    }

    if action not in action_map:
        raise SpotifyServiceError("Unsupported Spotify action.")

    method, path, message = action_map[action]
    _spotify_request(method, path, expected_statuses=(200, 202, 204))

    return SpotifyActionResponse(status="ok", message=message)


def _reset_for_tests() -> None:
    global _token_state

    _token_state = None
    _pending_states.clear()
