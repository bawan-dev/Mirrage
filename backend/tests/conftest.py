"""Shared pytest fixtures for the backend test suite."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.presence import assistant_state_manager
from backend.app.services.wake_engine import wake_engine_service
from backend.app.services.wake_word import wake_word_service


@pytest.fixture
def client() -> TestClient:
    """A FastAPI test client bound to the application."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_presence_state() -> None:
    """Keep the process-global presence state isolated between tests."""
    assistant_state_manager.reset_for_tests()
    wake_word_service.reset_for_tests()
    wake_engine_service.reset_for_tests()
