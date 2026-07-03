"""Backend-owned local wake engine manager."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from backend.app.schemas import WakeEngineActionResponse, WakeEngineStatusResponse
from backend.app.services.openwakeword_engine import OpenWakeWordEngine
from backend.app.services.wake_engine_models import (
    WakeEngineConfig,
    WakeEngineRuntimeError,
    get_wake_engine_config,
    validate_wake_engine_config,
)
from backend.app.services.wake_word import wake_word_service

logger = logging.getLogger(__name__)


WakeEngineProviderFactory = Callable[[WakeEngineConfig], OpenWakeWordEngine]


class WakeEngineService:
    """Owns wake engine lifecycle and bridges detections into presence."""

    def __init__(
        self,
        provider_factory: WakeEngineProviderFactory | None = None,
    ) -> None:
        self._provider_factory = provider_factory or self._create_provider
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._last_detection_time: str | None = None
        self._last_detection_latency_ms: float | None = None
        self._last_error: str | None = None

    def status(self) -> WakeEngineStatusResponse:
        config = get_wake_engine_config()
        issues = validate_wake_engine_config(config)
        running = self._is_running()

        if not config.enabled:
            status = "disabled"
            configured = False
            message = (
                "Local wake engine is disabled. Push-to-talk and adapter "
                "detection still work."
            )
        elif issues:
            status = "unconfigured"
            configured = False
            message = issues[0]
        elif running:
            status = "running"
            configured = True
            message = "Local wake engine is listening."
        else:
            status = "stopped"
            configured = True
            message = "Local wake engine is configured but not running."

        with self._lock:
            return WakeEngineStatusResponse(
                enabled=config.enabled,
                configured=configured,
                provider=config.provider,
                phrase=config.phrase,
                sensitivity=config.sensitivity,
                microphone_device=config.microphone,
                microphone_configured=config.microphone_configured,
                model_configured=config.model_configured,
                running=running,
                status=status,
                sample_rate=config.sample_rate,
                frame_ms=config.frame_ms,
                cooldown_seconds=config.cooldown_seconds,
                last_detection_time=self._last_detection_time,
                last_detection_latency_ms=self._last_detection_latency_ms,
                error_message=self._last_error,
                message=self._last_error or message,
            )

    def start(self) -> WakeEngineActionResponse:
        config = get_wake_engine_config()
        issues = validate_wake_engine_config(config)

        if not config.enabled:
            return WakeEngineActionResponse(
                status="disabled",
                message="Local wake engine is disabled.",
                running=False,
            )

        if issues:
            message = issues[0]
            self._set_error(message)
            logger.warning(
                "Wake engine start skipped because configuration is incomplete.",
                extra={
                    "event": "wake_engine_start_unconfigured",
                    "subsystem": "wake_engine",
                    "provider": config.provider,
                },
            )
            return WakeEngineActionResponse(
                status="unconfigured",
                message=message,
                running=False,
            )

        if self._is_running():
            return WakeEngineActionResponse(
                status="running",
                message="Local wake engine is already running.",
                running=True,
            )

        stop_event = threading.Event()
        provider = self._provider_factory(config)
        thread = threading.Thread(
            target=self._run_provider,
            args=(provider, config, stop_event),
            name=f"mirrage-wake-engine-{config.provider}",
            daemon=True,
        )

        with self._lock:
            self._stop_event = stop_event
            self._thread = thread
            self._last_error = None

        thread.start()
        logger.info(
            "Wake engine start requested.",
            extra={
                "event": "wake_engine_start_requested",
                "subsystem": "wake_engine",
                "provider": config.provider,
            },
        )
        return WakeEngineActionResponse(
            status="starting",
            message="Local wake engine is starting.",
            running=True,
        )

    def stop(self) -> WakeEngineActionResponse:
        with self._lock:
            stop_event = self._stop_event
            thread = self._thread

        if stop_event is None or thread is None:
            return WakeEngineActionResponse(
                status="stopped",
                message="Local wake engine is already stopped.",
                running=False,
            )

        stop_event.set()
        thread.join(timeout=2)
        with self._lock:
            if self._thread is thread:
                self._thread = None
                self._stop_event = None

        logger.info(
            "Wake engine stopped.",
            extra={"event": "wake_engine_stopped", "subsystem": "wake_engine"},
        )
        return WakeEngineActionResponse(
            status="stopped",
            message="Local wake engine stopped.",
            running=False,
        )

    def record_detection(
        self,
        *,
        confidence: float,
        detection_timestamp: str | None,
        provider: str | None = None,
    ) -> bool:
        config = get_wake_engine_config()
        result = wake_word_service.handle_detection_from_engine(
            phrase=config.phrase,
            engine=provider or config.provider,
            confidence=confidence,
            source=f"wake_engine:{provider or config.provider}",
            detection_timestamp=detection_timestamp,
        )

        if result.accepted:
            with self._lock:
                self._last_detection_time = result.event_timestamp
                self._last_detection_latency_ms = result.latency_ms
                self._last_error = None

        return result.accepted

    def reset_for_tests(self) -> None:
        self.stop()
        with self._lock:
            self._last_detection_time = None
            self._last_detection_latency_ms = None
            self._last_error = None

    def _run_provider(
        self,
        provider: OpenWakeWordEngine,
        config: WakeEngineConfig,
        stop_event: threading.Event,
    ) -> None:
        try:
            provider.listen(
                config,
                stop_event,
                lambda confidence, timestamp: self.record_detection(
                    confidence=confidence,
                    detection_timestamp=timestamp,
                    provider=provider.name,
                ),
            )
        except WakeEngineRuntimeError as exc:
            self._set_error(str(exc))
            logger.warning(
                "Wake engine runtime failed.",
                extra={
                    "event": "wake_engine_runtime_failed",
                    "subsystem": "wake_engine",
                    "provider": config.provider,
                },
            )
        finally:
            with self._lock:
                if self._thread is threading.current_thread():
                    self._thread = None
                    self._stop_event = None

    def _is_running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message

    @staticmethod
    def _create_provider(config: WakeEngineConfig) -> OpenWakeWordEngine:
        if config.provider == "openwakeword":
            return OpenWakeWordEngine()
        raise WakeEngineRuntimeError(f"{config.provider} is not implemented.")


wake_engine_service = WakeEngineService()
