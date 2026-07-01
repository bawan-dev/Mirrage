"""AI provider configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    provider: str = "stub"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    timeout: float = 30.0
    runtime_mode: str = "standard"
    local_first: bool = False
    local_only: bool = False
    fallback_provider: str = "stub"
    default_task_model: str | None = None
    summary_model: str | None = None
    planning_model: str | None = None
    streaming_enabled: bool = True
    privacy_mode: str = "limited_cloud_context"
    system_prompt: str = (
        "You are Mirrage, a calm and concise smart mirror assistant. "
        "Answer briefly and helpfully."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MIRRAGE_AI_",
        extra="ignore",
    )


ai_settings = AISettings()
