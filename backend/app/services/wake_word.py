"""Wake word service boundary.

This service does not process raw microphone audio itself. A local wake engine
such as OpenWakeWord or Porcupine can run beside Mirrage and call the wake
adapter endpoint when it detects the configured phrase.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from datetime import UTC, datetime

from backend.app.schemas import WakeWordDetectionRequest
from backend.app.services.presence import assistant_state_manager
from backend.app.settings import settings

logger = logging.getLogger(__name__)


def _normalize_phrase(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        cleaned = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class WakeWordDetectionResult:
    accepted: bool
    message: str
    status_code: int
    event_timestamp: str | None = None
    latency_ms: float | None = None


class WakeWordService:
    """Validates wake detections from a local wake-word engine."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._last_detection_at: datetime | None = None

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

    def handle_detection(
        self,
        request: WakeWordDetectionRequest,
    ) -> WakeWordDetectionResult:
        presence_settings = assistant_state_manager.settings()
        if not presence_settings.wake_word_enabled:
            logger.warning(
                "Wake detection ignored because wake word is disabled.",
                extra={"event": "wake_ignored", "subsystem": "wake_word"},
            )
            return WakeWordDetectionResult(
                accepted=False,
                message="Wake word detection is disabled.",
                status_code=400,
            )

        if not self.is_match(request.phrase):
            logger.warning(
                "Wake detection did not match configured phrase.",
                extra={
                    "event": "wake_mismatch",
                    "subsystem": "wake_word",
                    "engine": request.engine,
                },
            )
            return WakeWordDetectionResult(
                accepted=False,
                message="Wake phrase did not match the configured phrase.",
                status_code=400,
            )

        event_time = _now()
        with self._lock:
            if (
                self._last_detection_at is not None
                and settings.wake_engine_cooldown_seconds > 0
                and (event_time - self._last_detection_at).total_seconds()
                < settings.wake_engine_cooldown_seconds
            ):
                logger.info(
                    "Wake detection suppressed by cooldown.",
                    extra={
                        "event": "wake_detection_suppressed",
                        "subsystem": "wake_word",
                        "engine": request.engine,
                    },
                )
                return WakeWordDetectionResult(
                    accepted=False,
                    message="Wake detection suppressed by cooldown.",
                    status_code=429,
                )

            self._last_detection_at = event_time

        detection_time = _parse_timestamp(request.detection_timestamp)
        latency_ms = (
            round((event_time - detection_time).total_seconds() * 1000, 2)
            if detection_time is not None
            else None
        )

        logger.info(
            "Wake phrase detected.",
            extra={
                "event": "wake_word_detected",
                "subsystem": "wake_word",
                "engine": request.engine,
                "latency_ms": latency_ms,
            },
        )
        assistant_state_manager.transition(
            "wake_detected",
            event="wake_word_detected",
            source=request.source,
            message=(f"Wake phrase detected by {request.engine or 'local adapter'}."),
        )
        logger.info(
            "Wake detection emitted presence event.",
            extra={
                "event": "wake_presence_emitted",
                "subsystem": "wake_word",
                "engine": request.engine,
                "latency_ms": latency_ms,
            },
        )
        return WakeWordDetectionResult(
            accepted=True,
            message="Wake phrase detected.",
            status_code=200,
            event_timestamp=event_time.isoformat(),
            latency_ms=latency_ms,
        )

    def handle_detection_from_engine(
        self,
        *,
        phrase: str,
        engine: str,
        confidence: float | None,
        source: str,
        detection_timestamp: str | None,
    ) -> WakeWordDetectionResult:
        return self.handle_detection(
            WakeWordDetectionRequest(
                phrase=phrase,
                engine=engine,
                confidence=confidence,
                source=source,
                detection_timestamp=detection_timestamp,
            )
        )

    def reset_for_tests(self) -> None:
        with self._lock:
            self._last_detection_at = None


wake_word_service = WakeWordService()
