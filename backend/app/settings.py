"""Backend configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_version: str = "2.0.0-dev"
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

    # Local identity, trusted-device authentication, approvals, and audit data.
    identity_enabled: bool = True
    identity_mode: str = "development"
    identity_database_path: str = "data/mirrage-identity.sqlite3"
    identity_device_token_bytes: int = 32
    identity_session_ttl_seconds: int = 86400
    human_session_ttl_seconds: int = 900
    approval_ttl_seconds: int = 120
    audit_retention_days: int = 365
    identity_dev_bypass: bool = False

    # Smart home / Home Assistant configuration.
    smart_home_enabled: bool = False
    smart_home_timeout_seconds: float = 5.0
    home_assistant_enabled: bool = False
    home_assistant_base_url: str = "http://homeassistant.local:8123"
    home_assistant_token: str | None = None

    # Voice presence and wake word configuration.
    wake_word_enabled: bool = True
    wake_phrase: str = "Hey Mirrage"
    wake_word_engine: str = "adapter"
    wake_word_sensitivity: float = 0.55
    voice_microphone_device: str | None = None
    presence_inactivity_timeout_seconds: int = 25
    presence_automatic_sleep: bool = True

    # Local wake engine configuration. This is off by default so CI and normal
    # local development do not require a microphone, model file, or audio stack.
    wake_engine_enabled: bool = False
    wake_engine_provider: str = "openwakeword"
    wake_engine_model_path: str | None = None
    wake_engine_phrase: str = "Hey Mirrage"
    wake_engine_sensitivity: float = 0.5
    wake_engine_microphone: str | None = None
    wake_engine_sample_rate: int = 16000
    wake_engine_frame_ms: int = 80
    wake_engine_cooldown_seconds: float = 3.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MIRRAGE_",
        extra="ignore",
    )


settings = Settings()
