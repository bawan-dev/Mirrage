"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes import router
from backend.app.settings import settings

app = FastAPI(
    title="Mirrage API",
    version="0.1.0",
    description="Backend API for the Mirrage smart mirror system.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
