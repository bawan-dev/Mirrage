"""Tests for the AI runtime and provider router."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai import context_builder as context_builder_module
from ai import runtime as runtime_module
from ai.config import ai_settings
from ai.context_builder import build_runtime_context
from ai.models import RuntimeContext, RuntimeResult
from ai.providers.base import AIProviderError
from ai.providers.ollama import OllamaProvider
from ai.router import provider_router
from backend.app.schemas import MemoryCreateRequest
from backend.app.services import assistant as assistant_service
from backend.app.services import memory as memory_service
from backend.app.settings import settings


@pytest.fixture(autouse=True)
def reset_ai_runtime_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai_settings, "provider", "stub")
    monkeypatch.setattr(ai_settings, "model", None)
    monkeypatch.setattr(ai_settings, "runtime_mode", "standard")
    monkeypatch.setattr(ai_settings, "local_first", False)
    monkeypatch.setattr(ai_settings, "local_only", False)
    monkeypatch.setattr(ai_settings, "fallback_provider", "stub")
    monkeypatch.setattr(ai_settings, "default_task_model", None)
    monkeypatch.setattr(ai_settings, "summary_model", None)
    monkeypatch.setattr(ai_settings, "planning_model", None)
    monkeypatch.setattr(ai_settings, "streaming_enabled", True)
    monkeypatch.setattr(ai_settings, "privacy_mode", "limited_cloud_context")


def _runtime_context(
    message: str = "hello",
    task_type: str | None = None,  # noqa: ARG001
) -> RuntimeContext:
    return RuntimeContext(
        user_message=message,
        task_type="conversation",
        privacy_level="standard",
        local_prompt=f"Local prompt: {message}",
        cloud_prompt=f"Cloud prompt: {message}",
        sources=["test"],
    )


def test_runtime_status_endpoint_is_safe(client: TestClient) -> None:
    response = client.get("/api/ai/runtime/status")

    assert response.status_code == 200
    body = response.json()
    assert body["runtime_mode"] == "standard"
    assert body["configured_provider"] == "stub"
    assert body["fallback_provider"] == "stub"
    assert body["local_only"] is False
    assert "stub" in body["available_providers"]
    assert "api_key" not in body


def test_provider_list_endpoint_does_not_expose_secrets(client: TestClient) -> None:
    response = client.get("/api/ai/providers")

    assert response.status_code == 200
    providers = response.json()["providers"]
    provider_names = {provider["name"] for provider in providers}
    assert {"stub", "ollama", "openai"}.issubset(provider_names)
    assert all("api_key" not in provider for provider in providers)


def test_local_only_routing_never_selects_cloud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ai_settings, "provider", "openai")
    monkeypatch.setattr(ai_settings, "fallback_provider", "openai")
    monkeypatch.setattr(ai_settings, "local_only", True)

    selection = provider_router.select_provider(_runtime_context())

    assert selection.provider != "openai"
    assert selection.is_local is True
    assert selection.fallback_provider == "stub"


def test_private_context_prefers_local_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ai_settings, "provider", "openai")

    context = RuntimeContext(
        user_message="use my memory",
        task_type="memory",
        privacy_level="private",
        local_prompt="local",
        cloud_prompt="cloud",
    )

    selection = provider_router.select_provider(context)

    assert selection.provider == "ollama"
    assert selection.is_local is True


def test_runtime_falls_back_to_stub_when_primary_provider_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ai_settings, "provider", "ollama")
    monkeypatch.setattr(ai_settings, "fallback_provider", "stub")
    monkeypatch.setattr(runtime_module, "build_runtime_context", _runtime_context)

    def fail(self: OllamaProvider, message: str):  # noqa: ARG001
        raise AIProviderError("ollama unavailable")

    monkeypatch.setattr(OllamaProvider, "reply", fail)

    result = runtime_module.assistant_runtime.run_assistant_request("hello")

    assert result.provider == "stub"
    assert result.used_fallback is True


def test_context_builder_limits_memory_for_cloud_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        settings,
        "memory_database_path",
        str(tmp_path / "runtime-memory.sqlite3"),
    )
    memory_service.create_memory(
        MemoryCreateRequest(
            kind="goal",
            key="goal: private prototype",
            value="Do not send this raw goal value to cloud prompts.",
        )
    )
    monkeypatch.setattr(context_builder_module, "_safe_daily_context", lambda: None)
    monkeypatch.setattr(context_builder_module, "_safe_proactive_summary", lambda: None)

    context = build_runtime_context("help me plan")

    assert "Do not send this raw goal value" in context.local_prompt
    assert "Do not send this raw goal value" not in context.cloud_prompt
    assert "details withheld" in context.cloud_prompt
    assert context.memory_items_included == 1


def test_assistant_route_uses_runtime_for_unknown_messages(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reply(message: str, *, principal=None) -> RuntimeResult:  # noqa: ARG001
        return RuntimeResult(
            reply=f"runtime handled {message}",
            provider="runtime-test",
            model="test-model",
            task_type="conversation",
            runtime_mode="test",
            used_fallback=False,
            context_sources=["test"],
        )

    monkeypatch.setattr(
        assistant_service.assistant_runtime,
        "run_assistant_request",
        reply,
    )

    response = client.post("/api/assistant/message", json={"message": "hello"})

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "runtime-test"
    assert body["model"] == "test-model"


def test_deterministic_memory_handler_still_runs_before_runtime(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        settings,
        "memory_database_path",
        str(tmp_path / "deterministic-memory.sqlite3"),
    )

    def fail(message: str) -> RuntimeResult:  # noqa: ARG001
        raise AssertionError("runtime should not be called")

    monkeypatch.setattr(
        assistant_service.assistant_runtime,
        "run_assistant_request",
        fail,
    )

    response = client.post(
        "/api/assistant/message",
        json={"message": "remember my favorite color is blue"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "memory"
    assert body["memory_action"] == "stored"


def test_streaming_endpoint_uses_runtime_fallback_shape(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reply(message: str, *, principal=None) -> RuntimeResult:  # noqa: ARG001
        return RuntimeResult(
            reply=f"streamed {message}",
            provider="stub",
            model=None,
            task_type="conversation",
            runtime_mode="test",
            used_fallback=False,
            context_sources=["test"],
        )

    monkeypatch.setattr(
        runtime_module.assistant_runtime, "run_assistant_request", reply
    )

    response = client.post("/api/assistant/stream", json={"message": "hello"})

    assert response.status_code == 200
    body = response.text
    assert "event: chunk" in body
    assert "streamed hello" in body
    assert "event: done" in body
