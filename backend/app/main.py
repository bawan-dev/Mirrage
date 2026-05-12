"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.services.system import get_system_status

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
