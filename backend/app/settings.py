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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MIRRAGE_",
        extra="ignore",
    )


settings = Settings()
