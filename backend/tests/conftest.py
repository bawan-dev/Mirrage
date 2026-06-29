"""Shared pytest fixtures for the backend test suite."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.presence import assistant_state_manager


@pytest.fixture
def client() -> TestClient:
    """A FastAPI test client bound to the application."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_presence_state() -> None:
    """Keep the process-global presence state isolated between tests."""
    assistant_state_manager.reset_for_tests()
