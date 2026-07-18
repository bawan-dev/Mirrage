"""Authorization, approvals, private-data, and smart-home safety tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.services.authorization import (
    authorization_service,
    principal_for_device,
)
from backend.app.services.identity_models import AuthorizationRequest
from backend.app.services.identity_store import identity_store
from backend.app.services.permissions import Permission
from backend.app.services.smart_home import smart_home_service
from backend.app.settings import settings


class FakeProvider:
    configured = True

    def __init__(self) -> None:
        self.states_payload = [
            {
                "entity_id": "light.office",
                "state": "off",
                "attributes": {"friendly_name": "Office Light"},
                "last_updated": "2026-07-18T12:00:00+00:00",
            }
        ]

    def states(self) -> list[dict]:
        return self.states_payload

    def state(self, entity_id: str) -> dict:
        return next(
            item for item in self.states_payload if item["entity_id"] == entity_id
        )

    def call_service(self, *, domain: str, service: str, entity_id: str) -> dict:
        item = self.state(entity_id)
        item["state"] = "on" if service == "turn_on" else "off"
        return item


def _identity(role: str, name: str | None = None):
    user = identity_store.create_user(
        display_name=name or role.title(), role=role, household_member=True
    )
    enrollment = identity_store.enroll_device(
        user_public_id=user.public_id,
        display_name=f"{role} device",
        device_type="mirror",
        trust_level="trusted",
    )
    return user, enrollment


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def no_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "identity_dev_bypass", False)


@pytest.fixture
def enabled_home(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setattr(settings, "smart_home_enabled", True)
    monkeypatch.setattr(settings, "home_assistant_enabled", True)
    monkeypatch.setattr(settings, "home_assistant_token", "not-returned")
    monkeypatch.setattr(smart_home_service, "provider", provider)
    smart_home_service._last_entities = []
    return provider


def test_authorization_allows_permission_and_defaults_to_deny() -> None:
    owner, enrollment = _identity("owner")
    principal = principal_for_device(
        owner, enrollment.device, correlation_id="allow-test"
    )

    allowed = authorization_service.decide(
        principal,
        AuthorizationRequest(permission=Permission.AUDIT_READ.value),
    )
    denied = authorization_service.decide(
        principal,
        AuthorizationRequest(permission="unknown.permission"),
    )

    assert allowed.decision == "allowed"
    assert allowed.policy_id == "permission.effective.allow"
    assert denied.decision == "denied"
    assert denied.policy_id == "permission.unknown.default_deny"


def test_medium_risk_requires_approval() -> None:
    family, enrollment = _identity("family")
    principal = principal_for_device(
        family, enrollment.device, correlation_id="approval-test"
    )

    decision = authorization_service.decide(
        principal,
        AuthorizationRequest(
            permission=Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            resource_type="future_action",
            risk_level="medium",
        ),
    )

    assert decision.decision == "approval_required"
    assert decision.policy_id == "risk.approval.required"


def test_ai_context_cannot_override_denial() -> None:
    guest, enrollment = _identity("guest")
    principal = principal_for_device(
        guest, enrollment.device, correlation_id="ai-boundary"
    )

    decision = authorization_service.decide(
        principal,
        AuthorizationRequest(
            permission=Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            resource_type="smart_home",
            risk_level="low",
            context={"ai_says_allowed": True, "model_role": "owner"},
        ),
    )

    assert decision.decision == "denied"


def test_blocked_smart_home_domain_denied_for_owner() -> None:
    owner, enrollment = _identity("owner")
    principal = principal_for_device(
        owner, enrollment.device, correlation_id="blocked-domain"
    )

    decision = authorization_service.decide(
        principal,
        AuthorizationRequest(
            permission=Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            resource_type="smart_home",
            resource_id="lock.front_door",
            risk_level="high",
            context={"smart_home_domain": "lock"},
        ),
    )

    assert decision.decision == "denied"
    assert decision.policy_id == "smart_home.high_risk.global_block"


def test_guest_private_routes_are_denied(
    client: TestClient,
    no_bypass: None,
) -> None:
    _identity("owner")
    _guest, enrollment = _identity("guest")
    headers = _headers(enrollment.token)

    assert client.get("/api/memory", headers=headers).status_code == 403
    assert client.get("/api/context/daily", headers=headers).status_code == 403
    assert (
        client.get(
            "/api/integrations/calendar/events/today", headers=headers
        ).status_code
        == 403
    )


def test_guest_memory_command_is_denied_before_memory_access(
    client: TestClient,
    no_bypass: None,
) -> None:
    _identity("owner")
    _guest, enrollment = _identity("guest")

    response = client.post(
        "/api/assistant/message",
        headers=_headers(enrollment.token),
        json={"message": "what do you remember about me?"},
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]["permission"] == Permission.MEMORY_READ_PRIVATE.value
    )


@pytest.mark.parametrize("role", ["owner", "family"])
def test_owner_and_family_can_control_low_risk_light(
    client: TestClient,
    no_bypass: None,
    enabled_home: FakeProvider,
    role: str,
) -> None:
    if role != "owner":
        _identity("owner")
    _user, enrollment = _identity(role)

    response = client.post(
        "/api/smart-home/entities/light.office/turn-on",
        headers=_headers(enrollment.token),
    )

    assert response.status_code == 200
    assert response.json()["entity"]["state"] == "on"
    events, _count = identity_store.list_audit_events(
        event_type="smart_home_control_result"
    )
    assert events[0].result == "success"


@pytest.mark.parametrize("role", ["trusted_guest", "guest"])
def test_guests_cannot_control_smart_home(
    client: TestClient,
    no_bypass: None,
    enabled_home: FakeProvider,
    role: str,
) -> None:
    _identity("owner")
    _user, enrollment = _identity(role)

    response = client.post(
        "/api/smart-home/entities/light.office/turn-on",
        headers=_headers(enrollment.token),
    )

    assert response.status_code == 403


def test_anonymous_smart_home_control_is_denied(
    client: TestClient,
    no_bypass: None,
    enabled_home: FakeProvider,
) -> None:
    response = client.post("/api/smart-home/entities/light.office/turn-on")

    assert response.status_code == 401


def test_owner_lock_control_stays_blocked(
    client: TestClient,
    no_bypass: None,
    enabled_home: FakeProvider,
) -> None:
    owner, enrollment = _identity("owner")

    response = client.post(
        "/api/smart-home/entities/lock.front_door/turn-on",
        headers=_headers(enrollment.token),
    )

    assert response.status_code == 403
    events, _count = identity_store.list_audit_events(
        event_type="smart_home_control_attempt"
    )
    assert events[0].actor_user_id == owner.public_id
    assert events[0].result == "blocked"


def test_approval_create_approve_deny_and_cancel(
    client: TestClient,
    no_bypass: None,
) -> None:
    owner, owner_enrollment = _identity("owner")
    family, family_enrollment = _identity("family")
    request = {
        "action": "future.medium.action",
        "resource_type": "future_resource",
        "resource_id": "sample",
        "risk_level": "medium",
        "reason": "Request owner review.",
    }
    created = client.post(
        "/api/approvals", headers=_headers(family_enrollment.token), json=request
    )
    assert created.status_code == 201

    approved = client.post(
        f"/api/approvals/{created.json()['public_id']}/approve",
        headers=_headers(owner_enrollment.token),
        json={"reason": "Reviewed."},
    )
    assert approved.json()["status"] == "approved"
    assert approved.json()["decided_by_user_id"] == owner.public_id

    denied_request = client.post(
        "/api/approvals", headers=_headers(family_enrollment.token), json=request
    ).json()
    denied = client.post(
        f"/api/approvals/{denied_request['public_id']}/deny",
        headers=_headers(owner_enrollment.token),
        json={"reason": "Not appropriate."},
    )
    assert denied.json()["status"] == "denied"

    cancel_request = client.post(
        "/api/approvals", headers=_headers(family_enrollment.token), json=request
    ).json()
    cancelled = client.post(
        f"/api/approvals/{cancel_request['public_id']}/cancel",
        headers=_headers(family_enrollment.token),
        json={"reason": "No longer needed."},
    )
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["requester_user_id"] == family.public_id


def test_unauthorized_approver_is_denied(
    client: TestClient,
    no_bypass: None,
) -> None:
    _identity("owner")
    _family, family_enrollment = _identity("family")
    created = client.post(
        "/api/approvals",
        headers=_headers(family_enrollment.token),
        json={
            "action": "future.action",
            "resource_type": "future_resource",
            "risk_level": "medium",
            "reason": "Review this.",
        },
    ).json()

    response = client.post(
        f"/api/approvals/{created['public_id']}/approve",
        headers=_headers(family_enrollment.token),
        json={"reason": "Self approve."},
    )

    assert response.status_code == 403


def test_expired_approval_cannot_be_reused(
    client: TestClient,
    no_bypass: None,
) -> None:
    _owner, owner_enrollment = _identity("owner")
    _family, family_enrollment = _identity("family")
    approval = client.post(
        "/api/approvals",
        headers=_headers(family_enrollment.token),
        json={
            "action": "future.action",
            "resource_type": "future_resource",
            "risk_level": "medium",
            "reason": "Review this.",
        },
    ).json()
    expired = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    with identity_store.connect() as connection:
        connection.execute(
            "UPDATE approvals SET expires_at = ? WHERE public_id = ?",
            (expired, approval["public_id"]),
        )

    response = client.post(
        f"/api/approvals/{approval['public_id']}/approve",
        headers=_headers(owner_enrollment.token),
        json={"reason": "Too late."},
    )

    assert response.status_code == 409
    assert identity_store.get_approval(approval["public_id"]).status == "expired"


def test_approval_decision_is_audited(
    client: TestClient,
    no_bypass: None,
) -> None:
    _owner, owner_enrollment = _identity("owner")
    _family, family_enrollment = _identity("family")
    approval = client.post(
        "/api/approvals",
        headers=_headers(family_enrollment.token),
        json={
            "action": "future.action",
            "resource_type": "future_resource",
            "risk_level": "medium",
            "reason": "Review this.",
        },
    ).json()
    client.post(
        f"/api/approvals/{approval['public_id']}/deny",
        headers=_headers(owner_enrollment.token),
        json={"reason": "Denied."},
    )

    events, count = identity_store.list_audit_events(event_type="approval_decided")

    assert count == 1
    assert events[0].authorization_decision == "denied"
