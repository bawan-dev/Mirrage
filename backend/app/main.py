"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.logging_config import configure_logging
from backend.app.routes import router
from backend.app.services.startup import run_startup_validation
from backend.app.services.wake_engine import wake_engine_service
from backend.app.settings import settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    run_startup_validation()
    wake_engine_service.start()
    try:
        yield
    finally:
        wake_engine_service.stop()


app = FastAPI(
    title="Mirrage API",
    version="0.1.0",
    description="Backend API for the Mirrage smart mirror system.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
