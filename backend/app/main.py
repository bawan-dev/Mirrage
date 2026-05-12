"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.routes import router

app = FastAPI(
    title="Mirrage API",
    version="0.1.0",
    description="Backend API for the Mirrage smart mirror system.",
)

app.include_router(router)
