"""Backend configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_port: int = 8000
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    frontend_url: str = "http://127.0.0.1:5173"
    log_level: str = "INFO"
    log_json: bool = True
    log_file: str | None = None

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
    backup_directory: str = "backups"

    # Voice presence and wake word configuration.
    wake_word_enabled: bool = True
    wake_phrase: str = "Hey Mirrage"
    wake_word_engine: str = "adapter"
    wake_word_sensitivity: float = 0.55
    voice_microphone_device: str | None = None
    presence_inactivity_timeout_seconds: int = 25
    presence_automatic_sleep: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MIRRAGE_",
        extra="ignore",
    )


settings = Settings()
