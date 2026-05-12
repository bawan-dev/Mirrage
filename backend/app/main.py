"""FastAPI application entry point."""

from fastapi import FastAPI

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
