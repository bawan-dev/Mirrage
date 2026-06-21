"""Backend configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    frontend_url: str = "http://127.0.0.1:5173"

    # Weather location (defaults to Auckland, NZ).
    weather_latitude: float = -36.8485
    weather_longitude: float = 174.7633
    weather_location: str = "Auckland"

    # Spotify OAuth / Web API configuration.
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    spotify_redirect_uri: str = (
        "http://127.0.0.1:8000/api/integrations/spotify/callback"
    )

    # Google Calendar OAuth / API configuration.
    google_calendar_client_id: str | None = None
    google_calendar_client_secret: str | None = None
    google_calendar_redirect_uri: str = (
        "http://127.0.0.1:8000/api/integrations/calendar/callback"
    )
    google_calendar_id: str = "primary"
    google_calendar_time_zone: str = "Europe/London"

    # Local privacy-first memory store.
    memory_database_path: str = "data/mirrage-memory.sqlite3"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MIRRAGE_",
        extra="ignore",
    )


settings = Settings()
