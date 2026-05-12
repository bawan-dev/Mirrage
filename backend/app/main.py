"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.schemas import AssistantMessageRequest, AssistantMessageResponse
from backend.app.services.assistant import create_assistant_reply
from backend.app.services.system import get_system_status
from backend.app.services.voice import get_voice_status

app = FastAPI(
    title="Mirrage API",
    version="0.1.0",
    description="Backend API for the Mirrage smart mirror system.",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "service": "mirrage-api",
        "status": "online",
    }


@app.get("/health")
def read_health() -> dict[str, str]:
    return {
        "service": "mirrage-api",
        "status": "online",
    }


@app.get("/api/system/status")
def read_system_status() -> dict[str, str]:
    return get_system_status()


@app.get("/api/voice/status")
def read_voice_status() -> dict[str, str | bool]:
    return get_voice_status()


@app.post("/api/assistant/message")
def create_assistant_message(
    message: AssistantMessageRequest,
) -> AssistantMessageResponse:
    return create_assistant_reply(message)
