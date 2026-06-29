"""System status service boundary."""


def get_system_status() -> dict[str, str]:
    return {
        "status": "online",
        "frontend": "running",
        "backend": "online",
        "ai": "planned",
        "voice": "ready",
        "hardware": "planned",
    }
