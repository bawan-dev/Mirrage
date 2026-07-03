"""Provider-independent wake engine configuration and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.app.settings import settings

SUPPORTED_WAKE_ENGINE_PROVIDERS = ("openwakeword",)
FUTURE_WAKE_ENGINE_PROVIDERS = ("porcupine",)


class WakeEngineError(RuntimeError):
    """Base error for wake engine operations."""


class WakeEngineConfigurationError(WakeEngineError):
    """Raised when wake engine configuration is not ready."""


class WakeEngineRuntimeError(WakeEngineError):
    """Raised when a wake engine fails while running."""


@dataclass(frozen=True)
class WakeEngineConfig:
    enabled: bool
    provider: str
    model_path: str | None
    phrase: str
    sensitivity: float
    microphone: str | None
    sample_rate: int
    frame_ms: int
    cooldown_seconds: float

    @property
    def frame_samples(self) -> int:
        return max(1, int(self.sample_rate * (self.frame_ms / 1000)))

    @property
    def microphone_configured(self) -> bool:
        return bool(self.microphone)

    @property
    def model_configured(self) -> bool:
        if not self.model_path:
            return False
        return Path(self.model_path).expanduser().exists()


def get_wake_engine_config() -> WakeEngineConfig:
    return WakeEngineConfig(
        enabled=settings.wake_engine_enabled,
        provider=settings.wake_engine_provider.strip().lower(),
        model_path=settings.wake_engine_model_path,
        phrase=settings.wake_engine_phrase.strip() or settings.wake_phrase,
        sensitivity=settings.wake_engine_sensitivity,
        microphone=settings.wake_engine_microphone,
        sample_rate=settings.wake_engine_sample_rate,
        frame_ms=settings.wake_engine_frame_ms,
        cooldown_seconds=settings.wake_engine_cooldown_seconds,
    )


def validate_wake_engine_config(config: WakeEngineConfig) -> list[str]:
    issues: list[str] = []

    if config.provider in FUTURE_WAKE_ENGINE_PROVIDERS:
        issues.append(
            f"{config.provider} is documented as a future wake provider but is "
            "not implemented yet."
        )
    elif config.provider not in SUPPORTED_WAKE_ENGINE_PROVIDERS:
        issues.append(f"{config.provider} is not a supported wake engine provider.")

    if not 0 <= config.sensitivity <= 1:
        issues.append("Wake engine sensitivity must be between 0.0 and 1.0.")

    if config.sample_rate <= 0:
        issues.append("Wake engine sample rate must be greater than zero.")

    if config.frame_ms <= 0:
        issues.append("Wake engine frame size must be greater than zero milliseconds.")

    if config.cooldown_seconds < 0:
        issues.append("Wake engine cooldown must be zero or greater.")

    if config.enabled:
        if not config.model_path:
            issues.append("Wake engine model path is not configured.")
        elif not config.model_configured:
            issues.append("Wake engine model file was not found.")

    return issues
