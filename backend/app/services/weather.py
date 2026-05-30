"""Weather service: live current conditions from Open-Meteo (no API key)."""

import time

import httpx

from backend.app.schemas import WeatherResponse
from backend.app.settings import settings

_API_URL = "https://api.open-meteo.com/v1/forecast"
_CACHE_TTL_SECONDS = 600.0

# WMO weather interpretation codes -> short human text.
_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers",
    81: "Showers",
    82: "Violent showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm",
}

_cache_value: WeatherResponse | None = None
_cache_expires = 0.0


def _describe(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return _WEATHER_CODES.get(code, "Unknown")


def get_weather() -> WeatherResponse:
    """Return current weather, cached for a few minutes and resilient to failures."""
    global _cache_value, _cache_expires

    now = time.monotonic()
    if _cache_value is not None and now < _cache_expires:
        return _cache_value

    try:
        response = httpx.get(
            _API_URL,
            params={
                "latitude": settings.weather_latitude,
                "longitude": settings.weather_longitude,
                "current": "temperature_2m,weather_code",
                "timezone": "auto",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        current = response.json()["current"]
        result = WeatherResponse(
            status="online",
            location=settings.weather_location,
            temperature_c=current["temperature_2m"],
            condition=_describe(current.get("weather_code")),
            updated=current.get("time"),
        )
    except (httpx.HTTPError, KeyError, ValueError):
        # Serve the last good value if we have one; otherwise report unavailable.
        if _cache_value is not None:
            return _cache_value
        return WeatherResponse(
            status="unavailable",
            location=settings.weather_location,
            temperature_c=None,
            condition="Unavailable",
            updated=None,
        )

    _cache_value = result
    _cache_expires = now + _CACHE_TTL_SECONDS
    return result
