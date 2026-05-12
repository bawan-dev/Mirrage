"""Voice service boundary."""


def get_voice_status() -> dict[str, str | bool]:
    return {
        "status": "planned",
        "listening": False,
        "wake_word": "not_configured",
        "speech_to_text": "not_configured",
        "text_to_speech": "not_configured",
    }
