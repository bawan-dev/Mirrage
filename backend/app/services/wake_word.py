"""Wake word service boundary.

This service does not process raw microphone audio itself. A local wake engine
such as OpenWakeWord or Porcupine can run beside Mirrage and call the wake
adapter endpoint when it detects the configured phrase.
"""

from __future__ import annotations

import logging
import re

from backend.app.schemas import WakeWordDetectionRequest
from backend.app.services.presence import assistant_state_manager

logger = logging.getLogger(__name__)


def _normalize_phrase(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


class WakeWordService:
    """Validates wake detections from a local wake-word engine."""

    def status(self) -> dict[str, str | bool | float | None]:
        presence_settings = assistant_state_manager.settings()
        return {
            "enabled": presence_settings.wake_word_enabled,
            "phrase": presence_settings.wake_phrase,
            "engine": presence_settings.wake_word_engine,
            "sensitivity": presence_settings.sensitivity,
            "microphone_device": presence_settings.microphone_device,
            "mode": "local_adapter",
            "message": (
                "Wake audio is expected to stay inside the configured local "
                "wake engine. Mirrage receives only detection events."
            ),
        }

    def is_match(self, phrase: str) -> bool:
        configured = _normalize_phrase(assistant_state_manager.settings().wake_phrase)
        candidate = _normalize_phrase(phrase)
        return bool(configured and candidate == configured)

    def handle_detection(self, request: WakeWordDetectionRequest) -> tuple[bool, str]:
        presence_settings = assistant_state_manager.settings()
        if not presence_settings.wake_word_enabled:
            logger.warning(
                "Wake detection ignored because wake word is disabled.",
                extra={"event": "wake_ignored", "subsystem": "wake_word"},
            )
            return False, "Wake word detection is disabled."

        if not self.is_match(request.phrase):
            logger.warning(
                "Wake detection did not match configured phrase.",
                extra={
                    "event": "wake_mismatch",
                    "subsystem": "wake_word",
                    "engine": request.engine,
                },
            )
            return False, "Wake phrase did not match the configured phrase."

        logger.info(
            "Wake phrase detected.",
            extra={
                "event": "wake_word_detected",
                "subsystem": "wake_word",
                "engine": request.engine,
            },
        )
        assistant_state_manager.transition(
            "wake_detected",
            event="wake_word_detected",
            source=request.source,
            message=(f"Wake phrase detected by {request.engine or 'local adapter'}."),
        )
        return True, "Wake phrase detected."


wake_word_service = WakeWordService()
