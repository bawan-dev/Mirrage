"""API route definitions."""

from fastapi import APIRouter

from backend.app.schemas import AssistantMessageRequest, AssistantMessageResponse
from backend.app.services.assistant import create_assistant_reply
from backend.app.services.system import get_system_status
from backend.app.services.voice import get_voice_status

router = APIRouter()


@router.get("/")
def read_root() -> dict[str, str]:
    return {
        "service": "mirrage-api",
        "status": "online",
    }


@router.get("/health")
def read_health() -> dict[str, str]:
    return {
        "service": "mirrage-api",
        "status": "online",
    }


@router.get("/api/system/status")
def read_system_status() -> dict[str, str]:
    return get_system_status()


@router.get("/api/voice/status")
def read_voice_status() -> dict[str, str | bool]:
    return get_voice_status()


@router.post("/api/assistant/message")
def create_assistant_message(
    message: AssistantMessageRequest,
) -> AssistantMessageResponse:
    return create_assistant_reply(message)
