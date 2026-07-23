"""Phase 40 bounded-agent persistence, safety, and API tests."""

from __future__ import annotations

import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock

import pytest
from fastapi.testclient import TestClient

from ai.context_builder import build_runtime_context
from ai.models import AssistantResult
from ai.providers.stub import StubAssistantProvider
from backend.app.services import agents as _agents_package  # noqa: F401
from backend.app.services.agents import executor as executor_module
from backend.app.services.agents.models import AgentToolExecutionOutput
from backend.app.services.agents.registry import agent_tool_registry
from backend.app.services.agents.store import agent_store
from backend.app.services.authorization import effective_permissions
from backend.app.services.backups import (
    create_identity_backup,
    restore_identity_backup,
)
from backend.app.services.identity_store import SCHEMA_VERSION, identity_store
from backend.app.services.memory import list_memories
from backend.app.services.permissions import Permission
from backend.app.services.relationship_models import RelationshipCreateRequest
from backend.app.services.relationship_store import relationship_store
from backend.app.services.smart_home import smart_home_service
from backend.app.settings import settings


@pytest.fixture(autouse=True)
def enable_agents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "agents_enabled", True)
    monkeypatch.setattr(settings, "agent_max_steps", 10)
    monkeypatch.setattr(settings, "agent_max_runtime_seconds", 300)
    monkeypatch.setattr(settings, "agent_max_retries", 2)
    monkeypatch.setattr(settings, "agent_max_concurrent_runs", 2)
    monkeypatch.setattr(settings, "agent_approval_ttl_seconds", 300)
    monkeypatch.setattr(settings, "identity_dev_bypass", False)
    monkeypatch.setattr(
        settings, "memory_database_path", str(tmp_path / "agent-memory.sqlite3")
    )


def _identity(role: str = "owner", name: str = "Agent User"):
    user = identity_store.create_user(display_name=name, role=role)
    enrollment = identity_store.enroll_device(
        user_public_id=user.public_id,
        display_name=f"{name} desktop",
        device_type="desktop",
        trust_level="trusted",
    )
    return user, enrollment


def _headers(enrollment) -> dict[str, str]:
    return {"Authorization": f"Bearer {enrollment.token}"}


def _create_run(
    client: TestClient,
    headers: dict[str, str],
    *,
    agent_type: str = "planning",
    goal: str = "Check safe system status",
    max_steps: int | None = None,
) -> dict:
    payload: dict[str, object] = {"agent_type": agent_type, "goal": goal}
    if max_steps is not None:
        payload["max_steps"] = max_steps
    response = client.post("/api/agents/runs", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _plan(
    client: TestClient,
    headers: dict[str, str],
    run_id: str,
    tool_name: str = "system.read_safe_status",
    arguments: dict[str, object] | None = None,
) -> dict:
    response = client.post(
        f"/api/agents/runs/{run_id}/plan",
        headers=headers,
        json={
            "steps": [
                {
                    "description": "Run the registered safe tool.",
                    "tool_name": tool_name,
                    "arguments": arguments or {},
                }
            ]
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_schema_migration_adds_agent_tables_without_losing_users() -> None:
    user, _enrollment = _identity()
    assert identity_store.schema_version() == SCHEMA_VERSION == 3
    assert identity_store.get_user(user.public_id).display_name == "Agent User"
    with identity_store.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """SELECT name FROM sqlite_master
                   WHERE type = 'table' AND name LIKE 'agent_%'"""
            )
        }
    assert tables == {"agent_runs", "agent_steps", "agent_events"}


def test_run_creation_plan_execution_and_sse_history(client: TestClient) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    created = _create_run(client, headers)
    run_id = created["run"]["public_id"]
    planned = _plan(client, headers, run_id)
    assert planned["run"]["status"] == "ready"
    assert planned["steps"][0]["tool_name"] == "system.read_safe_status"

    completed = client.post(f"/api/agents/runs/{run_id}/start", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["run"]["status"] == "completed", completed.json()["run"][
        "error_summary"
    ]
    assert completed.json()["run"]["final_result"]

    history = client.get(f"/api/agents/runs/{run_id}/events", headers=headers)
    assert history.status_code == 200
    event_types = {item["event_type"] for item in history.json()["items"]}
    assert {"run_created", "plan_ready", "step_completed", "completed"} <= event_types

    stream = client.get(f"/api/agents/runs/{run_id}/events/stream", headers=headers)
    assert stream.status_code == 200
    assert "event: completed" in stream.text
    assert "arguments" not in stream.text


def test_cross_user_run_access_is_hidden(client: TestClient) -> None:
    _first, first_device = _identity(name="First Owner")
    _second, second_device = _identity(name="Second Owner")
    created = _create_run(client, _headers(first_device))
    run_id = created["run"]["public_id"]

    response = client.get(f"/api/agents/runs/{run_id}", headers=_headers(second_device))
    assert response.status_code == 404
    assert created["run"]["goal"] not in response.text


def test_unknown_tools_and_step_limits_are_rejected(client: TestClient) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    created = _create_run(client, headers, max_steps=1)
    run_id = created["run"]["public_id"]
    unknown = client.post(
        f"/api/agents/runs/{run_id}/plan",
        headers=headers,
        json={
            "steps": [
                {
                    "description": "Invent a tool.",
                    "tool_name": "shell.execute",
                    "arguments": {"command": "whoami"},
                }
            ]
        },
    )
    assert unknown.status_code == 422
    assert "whoami" not in unknown.text

    second = _create_run(client, headers, max_steps=1)
    too_many = client.post(
        f"/api/agents/runs/{second['run']['public_id']}/plan",
        headers=headers,
        json={
            "steps": [
                {
                    "description": "Read status once.",
                    "tool_name": "system.read_safe_status",
                    "arguments": {},
                },
                {
                    "description": "Read status twice.",
                    "tool_name": "system.read_safe_status",
                    "arguments": {},
                },
            ]
        },
    )
    assert too_many.status_code == 422


def test_registered_tools_reject_unexpected_arguments(client: TestClient) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    created = _create_run(client, headers)
    marker = "whoami-private-marker"
    response = client.post(
        f"/api/agents/runs/{created['run']['public_id']}/plan",
        headers=headers,
        json={
            "steps": [
                {
                    "description": "Try an invented tool argument.",
                    "tool_name": "system.read_safe_status",
                    "arguments": {"command": marker},
                }
            ]
        },
    )

    assert response.status_code == 422
    assert marker not in response.text
    stored = client.get(
        f"/api/agents/runs/{created['run']['public_id']}",
        headers=headers,
    )
    assert stored.json()["steps"] == []
    assert stored.json()["run"]["error_summary"] == "Plan validation failed safely."


def test_step_and_approval_descriptions_are_registry_owned(
    client: TestClient,
) -> None:
    _requester, requester_device = _identity("owner", "Requester")
    _approver, approver_device = _identity("owner", "Approver")
    headers = _headers(requester_device)
    marker = "private-description-marker"
    created = _create_run(client, headers, agent_type="memory")
    response = client.post(
        f"/api/agents/runs/{created['run']['public_id']}/plan",
        headers=headers,
        json={
            "steps": [
                {
                    "description": marker,
                    "tool_name": "memory.create_own",
                    "arguments": {
                        "kind": "fact",
                        "key": "safe-description",
                        "value": "Approved value",
                    },
                }
            ]
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["steps"][0]["description"] == (
        "Create one entry in the owner-private memory store."
    )
    queue = client.get(
        "/api/agents/approvals",
        headers=_headers(approver_device),
    )
    assert queue.status_code == 200
    assert marker not in queue.text


def test_research_goal_is_not_duplicated_into_step_arguments(
    client: TestClient,
) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    marker = "private-research-marker"
    created = _create_run(
        client,
        headers,
        agent_type="research",
        goal=f"{marker}\nCompare local wake engine notes",
    )
    planned = client.post(
        f"/api/agents/runs/{created['run']['public_id']}/plan",
        headers=headers,
        json={},
    )

    assert planned.status_code == 200, planned.text
    assert planned.json()["steps"][0]["arguments"] == {"source": "run_goal"}
    assert marker not in json.dumps(planned.json()["steps"][0]["arguments"])

    completed = client.post(
        f"/api/agents/runs/{created['run']['public_id']}/start",
        headers=headers,
    )
    assert completed.status_code == 200
    assert completed.json()["run"]["status"] == "completed"
    assert marker in completed.json()["run"]["final_result"]


def test_missing_information_pauses_without_persisting_steps(
    client: TestClient,
) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    created = _create_run(
        client,
        headers,
        agent_type="memory",
        goal="Remember something important",
    )
    planned = client.post(
        f"/api/agents/runs/{created['run']['public_id']}/plan",
        headers=headers,
        json={},
    )

    assert planned.status_code == 200, planned.text
    assert planned.json()["run"]["status"] == "awaiting_user_input"
    assert planned.json()["run"]["clarification_prompt"]
    assert planned.json()["steps"] == []
    start = client.post(
        f"/api/agents/runs/{created['run']['public_id']}/start",
        headers=headers,
    )
    assert start.status_code == 409


def test_guest_and_explicit_deny_cannot_execute_agent_tools(
    client: TestClient,
) -> None:
    guest, guest_device = _identity("guest", "Guest")
    guest_run = _create_run(client, _headers(guest_device))
    denied = client.post(
        f"/api/agents/runs/{guest_run['run']['public_id']}/plan",
        headers=_headers(guest_device),
        json={
            "steps": [
                {
                    "description": "Read safe status.",
                    "tool_name": "system.read_safe_status",
                    "arguments": {},
                }
            ]
        },
    )
    assert denied.status_code == 422
    assert Permission.AGENTS_EXECUTE_READ_ONLY.value not in effective_permissions(guest)

    family, family_device = _identity("family", "Family")
    identity_store.set_permission_override(
        user_public_id=family.public_id,
        permission=Permission.AGENTS_EXECUTE_READ_ONLY.value,
        effect="deny",
        actor_user_id=None,
    )
    family_run = _create_run(client, _headers(family_device))
    explicit_denial = client.post(
        f"/api/agents/runs/{family_run['run']['public_id']}/plan",
        headers=_headers(family_device),
        json={
            "steps": [
                {
                    "description": "Read safe status.",
                    "tool_name": "system.read_safe_status",
                    "arguments": {},
                }
            ]
        },
    )
    assert explicit_denial.status_code == 422


def test_concurrent_run_limit_is_enforced_atomically(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    monkeypatch.setattr(settings, "agent_max_concurrent_runs", 1)
    barrier = Barrier(2)

    def create(index: int):
        barrier.wait()
        return client.post(
            "/api/agents/runs",
            headers=headers,
            json={
                "agent_type": "planning",
                "goal": f"Create bounded run {index}",
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(create, range(2)))

    assert sorted(response.status_code for response in responses) == [201, 409]
    listed = client.get("/api/agents/runs", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["count"] == 1


def test_relationship_does_not_grant_agent_execution(client: TestClient) -> None:
    owner, _owner_device = _identity("owner", "Owner")
    guest, guest_device = _identity("guest", "Related Guest")
    relationship = relationship_store.propose_relationship(
        owner.public_id,
        RelationshipCreateRequest(
            target_user_id=guest.public_id,
            relationship_type="friend",
        ),
    )
    relationship_store.respond_relationship(
        relationship.public_id, guest.public_id, "active"
    )
    assert relationship_store.active_relationship(owner.public_id, guest.public_id)
    assert Permission.AGENTS_EXECUTE_READ_ONLY.value not in effective_permissions(guest)
    run = _create_run(client, _headers(guest_device))
    response = client.post(
        f"/api/agents/runs/{run['run']['public_id']}/plan",
        headers=_headers(guest_device),
        json={
            "steps": [
                {
                    "description": "Read safe status.",
                    "tool_name": "system.read_safe_status",
                    "arguments": {},
                }
            ]
        },
    )
    assert response.status_code == 422


def test_memory_write_needs_separate_approval_and_cannot_self_approve(
    client: TestClient,
) -> None:
    _requester, requester_device = _identity("owner", "Requester")
    _approver, approver_device = _identity("owner", "Approver")
    requester_headers = _headers(requester_device)
    run = _create_run(
        client,
        requester_headers,
        agent_type="memory",
        goal="Store memory: goal | portfolio | Finish Mirrage",
    )
    planned = _plan(
        client,
        requester_headers,
        run["run"]["public_id"],
        "memory.create_own",
        {"kind": "goal", "key": "portfolio", "value": "Finish Mirrage"},
    )
    approval_id = planned["steps"][0]["approval_id"]
    assert planned["run"]["status"] == "awaiting_approval"

    self_decision = client.post(
        f"/api/agents/approvals/{approval_id}/approve",
        headers=requester_headers,
        json={"reason": "I approve my own request"},
    )
    assert self_decision.status_code == 409

    approved = client.post(
        f"/api/agents/approvals/{approval_id}/approve",
        headers=_headers(approver_device),
        json={"reason": "Reviewed as a separate owner"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert "goal" not in approved.text

    completed = client.post(
        f"/api/agents/runs/{run['run']['public_id']}/start",
        headers=requester_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["run"]["status"] == "completed", completed.json()
    memories = list_memories(kind="goal")
    assert [(item.key, item.value) for item in memories.items] == [
        ("portfolio", "Finish Mirrage")
    ]


def test_concurrent_approval_decisions_allow_only_one_winner(
    client: TestClient,
) -> None:
    _requester, requester_device = _identity("owner", "Requester")
    _first_approver, first_device = _identity("owner", "First Approver")
    _second_approver, second_device = _identity("owner", "Second Approver")
    requester_headers = _headers(requester_device)
    run = _create_run(client, requester_headers, agent_type="memory")
    planned = _plan(
        client,
        requester_headers,
        run["run"]["public_id"],
        "memory.create_own",
        {"kind": "fact", "key": "bounded", "value": "One decision wins"},
    )
    approval_id = planned["steps"][0]["approval_id"]
    barrier = Barrier(2)

    def approve(headers: dict[str, str]):
        barrier.wait()
        return client.post(
            f"/api/agents/approvals/{approval_id}/approve",
            headers=headers,
            json={"reason": "Separate owner reviewed this action"},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(approve, (_headers(first_device), _headers(second_device)))
        )

    assert sorted(response.status_code for response in responses) == [200, 409]
    detail = client.get(
        f"/api/agents/runs/{run['run']['public_id']}",
        headers=requester_headers,
    )
    assert detail.json()["run"]["status"] == "ready"
    assert detail.json()["steps"][0]["status"] == "ready"


def test_denial_cancels_other_pending_agent_approvals(client: TestClient) -> None:
    _requester, requester_device = _identity("owner", "Requester")
    _approver, approver_device = _identity("owner", "Approver")
    headers = _headers(requester_device)
    run = _create_run(client, headers, agent_type="memory")
    response = client.post(
        f"/api/agents/runs/{run['run']['public_id']}/plan",
        headers=headers,
        json={
            "steps": [
                {
                    "description": "First proposed write.",
                    "tool_name": "memory.create_own",
                    "arguments": {
                        "kind": "fact",
                        "key": "first",
                        "value": "First value",
                    },
                },
                {
                    "description": "Second proposed write.",
                    "tool_name": "memory.create_own",
                    "arguments": {
                        "kind": "fact",
                        "key": "second",
                        "value": "Second value",
                    },
                },
            ]
        },
    )
    assert response.status_code == 200, response.text
    approval_ids = [step["approval_id"] for step in response.json()["steps"]]

    denied = client.post(
        f"/api/agents/approvals/{approval_ids[0]}/deny",
        headers=_headers(approver_device),
        json={"reason": "The requested write should not proceed"},
    )

    assert denied.status_code == 200
    statuses = {
        identity_store.get_approval(approval_id).status for approval_id in approval_ids
    }
    assert statuses == {"denied", "cancelled"}
    detail = client.get(
        f"/api/agents/runs/{run['run']['public_id']}",
        headers=headers,
    )
    assert detail.json()["run"]["status"] == "failed"
    assert {step["status"] for step in detail.json()["steps"]} == {"cancelled"}


def test_expired_approval_cannot_execute(client: TestClient) -> None:
    _requester, requester_device = _identity("owner", "Requester")
    requester_headers = _headers(requester_device)
    run = _create_run(client, requester_headers, agent_type="memory")
    planned = _plan(
        client,
        requester_headers,
        run["run"]["public_id"],
        "memory.create_own",
        {"kind": "fact", "key": "expired", "value": "Must not write"},
    )
    approval_id = planned["steps"][0]["approval_id"]
    with identity_store.connect() as connection:
        connection.execute(
            "UPDATE approvals SET expires_at = '2000-01-01T00:00:00+00:00' "
            "WHERE public_id = ?",
            (approval_id,),
        )

    response = client.post(
        f"/api/agents/runs/{run['run']['public_id']}/start",
        headers=requester_headers,
    )
    assert response.status_code == 200
    assert response.json()["run"]["status"] == "failed"
    assert list_memories(query="expired").count == 0


def test_smart_home_low_risk_action_uses_safe_service_boundary(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str]] = []
            self.configured = True

        def states(self):
            return [
                {
                    "entity_id": "light.office",
                    "state": "off",
                    "attributes": {"friendly_name": "Office"},
                    "last_changed": "2026-01-01T00:00:00+00:00",
                }
            ]

        def state(self, _entity_id: str):
            return {
                "entity_id": "light.office",
                "state": "on",
                "attributes": {"friendly_name": "Office"},
                "last_changed": "2026-01-01T00:00:00+00:00",
            }

        def call_service(self, *, domain: str, service: str, entity_id: str):
            self.calls.append((domain, service, entity_id))

    provider = FakeProvider()
    monkeypatch.setattr(settings, "smart_home_enabled", True)
    monkeypatch.setattr(settings, "home_assistant_enabled", True)
    monkeypatch.setattr(settings, "home_assistant_token", "not-exposed")
    monkeypatch.setattr(smart_home_service, "provider", provider)
    _requester, requester_device = _identity("owner", "Requester")
    _approver, approver_device = _identity("owner", "Approver")
    headers = _headers(requester_device)
    run = _create_run(client, headers, agent_type="smart_home")
    planned = _plan(
        client,
        headers,
        run["run"]["public_id"],
        "smart_home.turn_on_approved_light",
        {"entity_id": "light.office"},
    )
    approval_id = planned["steps"][0]["approval_id"]
    approved = client.post(
        f"/api/agents/approvals/{approval_id}/approve",
        headers=_headers(approver_device),
        json={"reason": "Low-risk light action reviewed"},
    )
    assert approved.status_code == 200
    completed = client.post(
        f"/api/agents/runs/{run['run']['public_id']}/start", headers=headers
    )
    assert completed.json()["run"]["status"] == "completed", completed.json()["run"][
        "error_summary"
    ]
    assert provider.calls == [("light", "turn_on", "light.office")]

    blocked = _create_run(client, headers, agent_type="smart_home")
    response = client.post(
        f"/api/agents/runs/{blocked['run']['public_id']}/plan",
        headers=headers,
        json={
            "steps": [
                {
                    "description": "Attempt a blocked lock action.",
                    "tool_name": "smart_home.turn_on_approved_light",
                    "arguments": {"entity_id": "lock.front_door"},
                }
            ]
        },
    )
    assert response.status_code == 422
    assert not any(call[0] == "lock" for call in provider.calls)


def test_pause_resume_and_cancel_are_persistent(client: TestClient) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    first = _create_run(client, headers)
    _plan(client, headers, first["run"]["public_id"])
    paused = client.post(
        f"/api/agents/runs/{first['run']['public_id']}/pause", headers=headers
    )
    assert paused.json()["run"]["status"] == "paused"
    resumed = client.post(
        f"/api/agents/runs/{first['run']['public_id']}/resume", headers=headers
    )
    assert resumed.json()["run"]["status"] == "completed"

    second = _create_run(client, headers)
    _plan(client, headers, second["run"]["public_id"])
    cancelled = client.post(
        f"/api/agents/runs/{second['run']['public_id']}/cancel", headers=headers
    )
    assert cancelled.json()["run"]["status"] == "cancelled"
    assert cancelled.json()["steps"][0]["status"] == "cancelled"


def test_concurrent_start_claim_executes_a_step_once(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    run = _create_run(client, headers)
    _plan(client, headers, run["run"]["public_id"])
    barrier = Barrier(2)
    call_lock = Lock()
    call_count = 0

    def slow_tool(*_args, **_kwargs):
        nonlocal call_count
        with call_lock:
            call_count += 1
        time.sleep(0.1)
        return AgentToolExecutionOutput(
            safe_summary="Read safe status once.",
            result_text="System status read once.",
        )

    monkeypatch.setattr(executor_module, "execute_registered_tool", slow_tool)

    def start():
        barrier.wait()
        return client.post(
            f"/api/agents/runs/{run['run']['public_id']}/start",
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _index: start(), range(2)))

    assert sorted(response.status_code for response in responses) == [200, 409]
    assert call_count == 1
    detail = client.get(
        f"/api/agents/runs/{run['run']['public_id']}",
        headers=headers,
    )
    assert detail.json()["run"]["status"] == "completed"


def test_concurrent_events_keep_unique_order(client: TestClient) -> None:
    user, enrollment = _identity()
    headers = _headers(enrollment)
    run = _create_run(client, headers)
    run_id = run["run"]["public_id"]

    with ThreadPoolExecutor(max_workers=6) as pool:
        events = list(
            pool.map(
                lambda index: agent_store.append_event(
                    run_id,
                    "test_event",
                    f"Safe event {index}",
                ),
                range(6),
            )
        )

    sequences = [event.sequence for event in events]
    assert len(set(sequences)) == 6
    persisted = agent_store.list_events(run_id, user.public_id)
    assert [event.sequence for event in persisted] == list(range(1, len(persisted) + 1))


def test_runtime_limit_stops_a_slow_tool(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    run = _create_run(client, headers)
    _plan(client, headers, run["run"]["public_id"])
    monkeypatch.setattr(settings, "agent_max_runtime_seconds", 0.001)

    def slow_tool(*_args, **_kwargs):
        time.sleep(0.02)
        return AgentToolExecutionOutput(
            safe_summary="Slow result.", result_text="Slow result."
        )

    monkeypatch.setattr(executor_module, "execute_registered_tool", slow_tool)
    response = client.post(
        f"/api/agents/runs/{run['run']['public_id']}/start", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["run"]["status"] == "failed"
    assert "runtime limit" in response.json()["run"]["error_summary"].casefold()


def test_run_expiry_closes_steps_and_pending_approvals(
    client: TestClient,
) -> None:
    _requester, requester_device = _identity("owner", "Requester")
    _approver, approver_device = _identity("owner", "Approver")
    headers = _headers(requester_device)
    run = _create_run(client, headers, agent_type="memory")
    planned = _plan(
        client,
        headers,
        run["run"]["public_id"],
        "memory.create_own",
        {"kind": "fact", "key": "expiry", "value": "Never written"},
    )
    approval_id = planned["steps"][0]["approval_id"]
    with identity_store.connect() as connection:
        connection.execute(
            "UPDATE agent_runs SET expires_at = '2000-01-01T00:00:00+00:00' "
            "WHERE public_id = ?",
            (run["run"]["public_id"],),
        )

    detail = client.get(
        f"/api/agents/runs/{run['run']['public_id']}",
        headers=headers,
    )

    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "expired"
    assert detail.json()["steps"][0]["status"] == "cancelled"
    assert identity_store.get_approval(approval_id).status == "expired"
    queue = client.get(
        "/api/agents/approvals",
        headers=_headers(approver_device),
    )
    assert approval_id not in queue.text


def test_ai_planning_uses_structured_runtime_and_private_context(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _user, enrollment = _identity()
    captured: list[str] = []

    def structured_reply(_provider, message: str) -> AssistantResult:
        captured.append(message)
        return AssistantResult(
            reply=json.dumps(
                {
                    "assumptions": ["Use safe internal state only."],
                    "steps": [
                        {
                            "description": "Read safe status.",
                            "tool_name": "system.read_safe_status",
                            "arguments": {},
                        }
                    ],
                    "expected_outcome": "Return system status.",
                    "stop_conditions": ["Stop on denial."],
                    "clarification_prompt": None,
                }
            ),
            provider="stub",
            model=None,
        )

    monkeypatch.setattr(StubAssistantProvider, "reply", structured_reply)
    headers = _headers(enrollment)
    run = _create_run(client, headers, goal="Make a bounded status plan")
    response = client.post(
        f"/api/agents/runs/{run['run']['public_id']}/plan",
        headers=headers,
        json={},
    )
    assert response.status_code == 200
    assert response.json()["steps"][0]["tool_name"] == "system.read_safe_status"
    assert captured
    context = build_runtime_context(
        "private-goal-marker",
        task_type="agent_planning",
    )
    assert context.privacy_level == "private"
    assert context.sources == []
    assert "Active goals:" not in context.cloud_prompt


def test_registry_has_no_arbitrary_execution_or_web_tools() -> None:
    names = {tool.name for tool in agent_tool_registry.descriptors()}
    assert "shell.execute" not in names
    assert "python.execute" not in names
    assert "filesystem.read" not in names
    assert "web.fetch" not in names
    assert all(
        "url" not in json.dumps(tool.input_schema).casefold()
        for tool in agent_tool_registry.descriptors()
    )


def test_health_and_backup_include_agents(client: TestClient, tmp_path: Path) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    created = _create_run(client, headers)
    run_id = created["run"]["public_id"]

    health = client.get("/api/health/full", headers=headers)
    assert health.status_code == 200
    agents = next(item for item in health.json()["checks"] if item["name"] == "agents")
    assert agents["details"]["enabled"] is True
    assert "goal" not in json.dumps(agents)

    backup = create_identity_backup(tmp_path)
    with sqlite3.connect(backup.destination) as connection:
        assert connection.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0] == 1
    with identity_store.connect() as connection:
        connection.execute("DELETE FROM agent_events")
        connection.execute("DELETE FROM agent_steps")
        connection.execute("DELETE FROM agent_runs")
    restore_identity_backup(backup.destination)
    assert agent_store.get_run(run_id, created["run"]["owner_user_id"])


def test_agent_audit_does_not_store_goal_or_tool_arguments(
    client: TestClient,
) -> None:
    _user, enrollment = _identity()
    headers = _headers(enrollment)
    secret_marker = "private-goal-marker"
    run = _create_run(client, headers, goal=secret_marker)
    _plan(client, headers, run["run"]["public_id"])
    events, _count = identity_store.list_audit_events(limit=200)
    serialized = json.dumps([event.model_dump(mode="json") for event in events])
    assert secret_marker not in serialized
    assert "arguments" not in serialized
