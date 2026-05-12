"""AI provider configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    provider: str = "stub"
    model: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MIRRAGE_AI_",
        extra="ignore",
    )


ai_settings = AISettings()
