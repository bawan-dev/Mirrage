"""OpenWakeWord provider boundary for local wake detection.

The optional OpenWakeWord and audio packages are imported only when the provider
starts. CI and normal development can run without them installed.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.services.wake_engine_models import (
    WakeEngineConfig,
    WakeEngineRuntimeError,
)

logger = logging.getLogger(__name__)


class OpenWakeWordEngine:
    """Runs OpenWakeWord against a local microphone stream."""

    name = "openwakeword"

    def listen(
        self,
        config: WakeEngineConfig,
        stop_event: threading.Event,
        on_detection: Callable[[float, str], None],
    ) -> None:
        try:
            import numpy as np  # type: ignore[import-not-found]
            import sounddevice as sd  # type: ignore[import-not-found]
            from openwakeword.model import Model  # type: ignore[import-not-found]
        except ImportError as exc:
            raise WakeEngineRuntimeError(
                "OpenWakeWord runtime is not installed. Install openwakeword, "
                "sounddevice, and numpy on the target device."
            ) from exc

        model_path = Path(config.model_path or "").expanduser()
        if not model_path.exists():
            raise WakeEngineRuntimeError("OpenWakeWord model file was not found.")

        try:
            model = Model(wakeword_models=[str(model_path)])
        except Exception as exc:
            raise WakeEngineRuntimeError(
                "OpenWakeWord model could not be loaded."
            ) from exc

        device = _parse_microphone_device(config.microphone)
        logger.info(
            "OpenWakeWord listener started.",
            extra={
                "event": "wake_engine_openwakeword_started",
                "subsystem": "wake_engine",
                "provider": self.name,
            },
        )

        try:
            with sd.InputStream(
                channels=1,
                dtype="int16",
                samplerate=config.sample_rate,
                blocksize=config.frame_samples,
                device=device,
            ) as stream:
                while not stop_event.is_set():
                    audio, overflowed = stream.read(config.frame_samples)
                    if overflowed:
                        logger.warning(
                            "Wake engine audio input overflow.",
                            extra={
                                "event": "wake_engine_audio_overflow",
                                "subsystem": "wake_engine",
                                "provider": self.name,
                            },
                        )

                    mono_audio = np.asarray(audio).reshape(-1)
                    prediction = model.predict(mono_audio)
                    score = _extract_score(prediction)
                    if score >= config.sensitivity:
                        on_detection(score, datetime.now(UTC).isoformat())
        except Exception as exc:
            raise WakeEngineRuntimeError(
                "OpenWakeWord microphone listener failed."
            ) from exc


def _parse_microphone_device(value: str | None) -> int | str | None:
    if value is None:
        return None

    cleaned = value.strip()
    if cleaned.isdigit():
        return int(cleaned)
    return cleaned or None


def _extract_score(prediction: Any) -> float:
    if isinstance(prediction, dict):
        values = [
            float(value)
            for value in prediction.values()
            if isinstance(value, int | float)
        ]
        return max(values, default=0.0)

    if isinstance(prediction, int | float):
        return float(prediction)

    return 0.0
