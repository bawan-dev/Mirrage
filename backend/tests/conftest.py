"""Shared pytest fixtures for the backend test suite."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.presence import assistant_state_manager
from backend.app.services.wake_engine import wake_engine_service
from backend.app.services.wake_word import wake_word_service
from backend.app.settings import settings


@pytest.fixture
def client() -> TestClient:
    """A FastAPI test client bound to the application."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def isolate_runtime_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Keep process-global and private database state isolated between tests."""
    monkeypatch.setattr(
        settings,
        "identity_database_path",
        str(tmp_path / "mirrage-identity-test.sqlite3"),
    )
    monkeypatch.setattr(settings, "identity_enabled", True)
    monkeypatch.setattr(settings, "identity_mode", "development")
    monkeypatch.setattr(settings, "identity_dev_bypass", True)
    monkeypatch.setattr(settings, "app_env", "test")
    assistant_state_manager.reset_for_tests()
    wake_word_service.reset_for_tests()
    wake_engine_service.reset_for_tests()
