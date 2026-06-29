"""Voice service boundary."""

from backend.app.services.presence import assistant_state_manager
from backend.app.services.wake_word import wake_word_service


def get_voice_status() -> dict[str, str | bool | float | None]:
    presence = assistant_state_manager.snapshot()
    wake_status = wake_word_service.status()

    return {
        "status": "ready",
        "listening": presence.state == "listening",
        "wake_word": "enabled" if wake_status["enabled"] else "disabled",
        "wake_phrase": wake_status["phrase"],
        "wake_word_engine": wake_status["engine"],
        "wake_word_mode": wake_status["mode"],
        "sensitivity": wake_status["sensitivity"],
        "microphone_device": wake_status["microphone_device"],
        "presence_state": presence.state,
        "speech_to_text": "browser_after_wake",
        "text_to_speech": "browser_synthesis",
    }
