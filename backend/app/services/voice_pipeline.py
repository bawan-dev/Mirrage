"""Voice pipeline stage transitions for Mirrage."""

from __future__ import annotations

from backend.app.schemas import PresenceSnapshot
from backend.app.services.presence import assistant_state_manager


class VoicePipeline:
    """Emits lifecycle stages without depending on a specific AI provider."""

    def wake_detected(self, source: str = "wake_word_engine") -> PresenceSnapshot:
        return assistant_state_manager.transition(
            "wake_detected",
            event="wake_word_detected",
            source=source,
            message="Wake word detected. Preparing microphone.",
        )

    def listening(
        self,
        *,
        source: str = "frontend_voice",
        interim_transcript: str | None = None,
    ) -> PresenceSnapshot:
        return assistant_state_manager.transition(
            "listening",
            event="speech_recognition_started",
            source=source,
            interim_transcript=interim_transcript,
            message="Listening for the user's request.",
        )

    def processing(
        self,
        transcript: str,
        *,
        source: str = "assistant_route",
    ) -> PresenceSnapshot:
        return assistant_state_manager.transition(
            "processing",
            event="intent_processing_started",
            source=source,
            transcript=transcript,
            message="Processing the spoken request.",
        )

    def speaking(
        self,
        reply: str,
        *,
        transcript: str | None = None,
        source: str = "assistant_route",
    ) -> PresenceSnapshot:
        return assistant_state_manager.transition(
            "speaking",
            event="speech_synthesis_started",
            source=source,
            transcript=transcript,
            assistant_reply=reply,
            message="Assistant response is ready to speak.",
        )

    def returning_to_idle(self, source: str = "frontend_voice") -> PresenceSnapshot:
        return assistant_state_manager.transition(
            "returning_to_idle",
            event="conversation_ending",
            source=source,
            message="Conversation is ending.",
        )

    def idle(self, source: str = "presence_service") -> PresenceSnapshot:
        return assistant_state_manager.transition(
            "idle",
            event="conversation_idle",
            source=source,
            message="Assistant presence is idle.",
        )

    def sleeping(self, source: str = "presence_service") -> PresenceSnapshot:
        return assistant_state_manager.transition(
            "sleeping",
            event="automatic_sleep",
            source=source,
            message="Mirror is sleeping.",
        )


voice_pipeline = VoicePipeline()
