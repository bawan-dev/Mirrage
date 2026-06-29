"""Assistant presence state manager and event stream."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

from backend.app.schemas import (
    PresenceSettings,
    PresenceSettingsUpdate,
    PresenceSnapshot,
    PresenceState,
)
from backend.app.settings import settings


@dataclass
class _PresenceSubscriber:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[PresenceSnapshot]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class AssistantStateManager:
    """Owns the global assistant lifecycle state for this backend process."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: list[_PresenceSubscriber] = []
        self._default_settings = PresenceSettings(
            wake_word_enabled=settings.wake_word_enabled,
            wake_phrase=settings.wake_phrase,
            wake_word_engine=settings.wake_word_engine,
            sensitivity=settings.wake_word_sensitivity,
            microphone_device=settings.voice_microphone_device,
            inactivity_timeout_seconds=settings.presence_inactivity_timeout_seconds,
            automatic_sleep=settings.presence_automatic_sleep,
            privacy_mode="wake_audio_local_only",
            message=(
                "Wake word audio stays local to the configured wake engine. "
                "Assistant speech recognition starts after wake detection."
            ),
        )
        self._reset_state()

    def _reset_state(self) -> None:
        self._sequence = 0
        self._settings = self._default_settings.model_copy(deep=True)
        self._snapshot = PresenceSnapshot(
            state="idle",
            previous_state=None,
            event="startup",
            sequence=self._sequence,
            wake_phrase=self._settings.wake_phrase,
            wake_word_enabled=self._settings.wake_word_enabled,
            wake_word_engine=self._settings.wake_word_engine,
            source="presence_service",
            message="Assistant presence is idle.",
            updated_at=_now_iso(),
        )

    def reset_for_tests(self) -> PresenceSnapshot:
        with self._lock:
            self._reset_state()
            return self._snapshot.model_copy(deep=True)

    def snapshot(self) -> PresenceSnapshot:
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def settings(self) -> PresenceSettings:
        with self._lock:
            return self._settings.model_copy(deep=True)

    def update_settings(self, update: PresenceSettingsUpdate) -> PresenceSettings:
        with self._lock:
            values = self._settings.model_dump()
            update_values = update.model_dump(exclude_unset=True)

            if "wake_phrase" in update_values and update_values["wake_phrase"]:
                update_values["wake_phrase"] = update_values["wake_phrase"].strip()

            values.update(update_values)
            self._settings = PresenceSettings(**values)
            self._snapshot = self._snapshot.model_copy(
                update={
                    "wake_phrase": self._settings.wake_phrase,
                    "wake_word_enabled": self._settings.wake_word_enabled,
                    "wake_word_engine": self._settings.wake_word_engine,
                }
            )

        self.transition(
            self._snapshot.state,
            event="settings_updated",
            source="presence_service",
            message="Presence settings updated.",
        )
        return self.settings()

    def transition(
        self,
        state: PresenceState,
        *,
        event: str,
        source: str,
        message: str,
        transcript: str | None = None,
        interim_transcript: str | None = None,
        assistant_reply: str | None = None,
    ) -> PresenceSnapshot:
        with self._lock:
            previous_state = self._snapshot.state
            self._sequence += 1
            self._snapshot = PresenceSnapshot(
                state=state,
                previous_state=previous_state,
                event=event,
                sequence=self._sequence,
                wake_phrase=self._settings.wake_phrase,
                wake_word_enabled=self._settings.wake_word_enabled,
                wake_word_engine=self._settings.wake_word_engine,
                transcript=transcript,
                interim_transcript=interim_transcript,
                assistant_reply=assistant_reply,
                source=source,
                message=message,
                updated_at=_now_iso(),
            )
            snapshot = self._snapshot.model_copy(deep=True)
            subscribers = list(self._subscribers)

        stale_subscribers: list[_PresenceSubscriber] = []
        for subscriber in subscribers:
            try:
                subscriber.loop.call_soon_threadsafe(
                    subscriber.queue.put_nowait,
                    snapshot,
                )
            except RuntimeError:
                stale_subscribers.append(subscriber)

        if stale_subscribers:
            with self._lock:
                self._subscribers = [
                    subscriber
                    for subscriber in self._subscribers
                    if subscriber not in stale_subscribers
                ]

        return snapshot

    async def events(self) -> AsyncIterator[str]:
        queue: asyncio.Queue[PresenceSnapshot] = asyncio.Queue(maxsize=32)
        subscriber = _PresenceSubscriber(asyncio.get_running_loop(), queue)

        with self._lock:
            self._subscribers.append(subscriber)
            current = self._snapshot.model_copy(deep=True)

        yield self._format_sse(current)

        try:
            while True:
                snapshot = await queue.get()
                yield self._format_sse(snapshot)
        finally:
            with self._lock:
                self._subscribers = [
                    item for item in self._subscribers if item is not subscriber
                ]

    @staticmethod
    def _format_sse(snapshot: PresenceSnapshot) -> str:
        payload = json.dumps(snapshot.model_dump(), separators=(",", ":"))
        return f"event: presence\ndata: {payload}\n\n"


assistant_state_manager = AssistantStateManager()
