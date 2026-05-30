"""Shared pytest fixtures for the backend test suite."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    """A FastAPI test client bound to the application."""
    return TestClient(app)
