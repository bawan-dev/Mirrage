"""Identity store, trusted-device authentication, and management tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.services.authorization import effective_permissions
from backend.app.services.backups import (
    create_identity_backup,
    create_memory_backup,
    restore_identity_backup,
)
from backend.app.services.identity_store import (
    SCHEMA_VERSION,
    IdentityConflictError,
    identity_store,
)
from backend.app.services.permissions import Permission, permissions_for_role
from backend.app.services.startup import validate_environment
from backend.app.settings import settings


def _user(role: str = "owner", name: str | None = None):
    return identity_store.create_user(
        display_name=name or role.replace("_", " ").title(),
        role=role,
        household_member=role not in {"guest", "service"},
    )


def _device(user, *, name: str = "Test Device"):
    return identity_store.enroll_device(
        user_public_id=user.public_id,
        display_name=name,
        device_type="mirror",
        trust_level="trusted",
    )


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _disable_dev_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "identity_dev_bypass", False)


def test_identity_database_initializes_with_schema_version() -> None:
    identity_store.initialize()

    assert identity_store.database_path().exists()
    assert identity_store.schema_version() == SCHEMA_VERSION


def test_user_creation_and_safe_response() -> None:
    user = _user("family", "Sample Family")

    assert user.public_id
    assert user.display_name == "Sample Family"
    assert user.role == "family"
    assert user.status == "active"
    assert "password" not in user.model_dump()


def test_duplicate_public_identity_is_rejected() -> None:
    identity_store.create_user(
        display_name="First",
        role="guest",
        public_id="fixed-public-id",
    )

    with pytest.raises(IdentityConflictError, match="already exists"):
        identity_store.create_user(
            display_name="Second",
            role="guest",
            public_id="fixed-public-id",
        )


def test_final_owner_cannot_be_disabled_or_demoted() -> None:
    owner = _user()

    with pytest.raises(IdentityConflictError, match="final active owner"):
        identity_store.disable_user(owner.public_id)
    with pytest.raises(IdentityConflictError, match="final active owner"):
        identity_store.update_user(owner.public_id, role="family")


def test_owner_can_be_changed_when_another_owner_exists() -> None:
    first = _user("owner", "First Owner")
    _user("owner", "Second Owner")

    updated = identity_store.update_user(first.public_id, role="family")

    assert updated.role == "family"


def test_disabling_user_revokes_their_devices() -> None:
    _user("owner")
    family = _user("family")
    enrollment = _device(family)

    disabled = identity_store.disable_user(family.public_id)

    assert disabled.status == "disabled"
    assert identity_store.get_device(enrollment.device.public_id).status == "revoked"
    assert identity_store.authenticate_device_token(enrollment.token) is None


@pytest.mark.parametrize(
    ("role", "allowed", "denied"),
    [
        ("owner", Permission.AUDIT_READ.value, None),
        (
            "family",
            Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            Permission.MEMORY_READ_PRIVATE.value,
        ),
        (
            "trusted_guest",
            Permission.SMART_HOME_READ.value,
            Permission.SMART_HOME_CONTROL_LOW_RISK.value,
        ),
        (
            "guest",
            Permission.WEATHER_READ.value,
            Permission.CALENDAR_READ_PRIVATE.value,
        ),
        (
            "service",
            Permission.SYSTEM_STATUS_READ.value,
            Permission.ASSISTANT_USE.value,
        ),
    ],
)
def test_default_role_policies(role: str, allowed: str, denied: str | None) -> None:
    permissions = permissions_for_role(role)

    assert allowed in permissions
    if denied:
        assert denied not in permissions


def test_explicit_grant_and_deny_precedence() -> None:
    owner = _user("owner")
    family = _user("family")
    identity_store.set_permission_override(
        user_public_id=family.public_id,
        permission=Permission.MEMORY_READ_PRIVATE.value,
        effect="grant",
        actor_user_id=owner.public_id,
    )
    assert Permission.MEMORY_READ_PRIVATE.value in effective_permissions(family)

    identity_store.set_permission_override(
        user_public_id=family.public_id,
        permission=Permission.SMART_HOME_CONTROL_LOW_RISK.value,
        effect="deny",
        actor_user_id=owner.public_id,
    )
    assert Permission.SMART_HOME_CONTROL_LOW_RISK.value not in effective_permissions(
        family
    )


def test_permission_override_blocks_self_escalation() -> None:
    guest = _user("guest")

    with pytest.raises(IdentityConflictError, match="Self-escalation"):
        identity_store.set_permission_override(
            user_public_id=guest.public_id,
            permission=Permission.AUDIT_READ.value,
            effect="grant",
            actor_user_id=guest.public_id,
        )


def test_device_token_is_random_one_time_and_only_hash_is_stored() -> None:
    owner = _user()
    enrollment = _device(owner)
    second_enrollment = _device(owner, name="Second Test Device")
    prefix, stored_hash = identity_store.raw_device_secret_columns(
        enrollment.device.public_id
    )

    assert enrollment.token.startswith(f"{prefix}_")
    assert enrollment.token != second_enrollment.token
    assert enrollment.token not in stored_hash
    assert len(stored_hash) == 64
    assert (
        "token"
        not in identity_store.get_device(enrollment.device.public_id).model_dump()
    )
    assert (
        "token_hash"
        not in identity_store.get_device(enrollment.device.public_id).model_dump()
    )


def test_valid_token_authenticates_and_updates_last_seen(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_dev_bypass(monkeypatch)
    owner = _user()
    enrollment = _device(owner)

    response = client.get("/api/identity/me", headers=_headers(enrollment.token))

    assert response.status_code == 200
    assert response.json()["user_id"] == owner.public_id
    assert response.json()["authentication_method"] == "trusted_device"
    assert (
        identity_store.get_device(enrollment.device.public_id).last_seen_at is not None
    )


@pytest.mark.parametrize("token", ["invalid", "Basic abc", "mrg_missing_bad"])
def test_invalid_or_malformed_token_is_denied(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    token: str,
) -> None:
    _disable_dev_bypass(monkeypatch)

    response = client.get("/api/identity/me", headers=_headers(token))

    assert response.status_code == 401


def test_revoked_token_is_denied(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_dev_bypass(monkeypatch)
    owner = _user()
    enrollment = _device(owner)
    identity_store.revoke_device(enrollment.device.public_id)

    response = client.get("/api/identity/me", headers=_headers(enrollment.token))

    assert response.status_code == 401


def test_missing_token_is_anonymous_and_required_route_denies(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_dev_bypass(monkeypatch)

    assert client.get("/api/identity/status").status_code == 200
    assert client.get("/api/identity/me").status_code == 401


def test_development_bypass_is_explicit(client: TestClient) -> None:
    response = client.get("/api/identity/me")

    assert response.status_code == 200
    assert response.json()["authentication_method"] == "development"
    assert response.json()["assurance_level"] == "low"


def test_production_rejects_development_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "identity_mode", "enforced")
    monkeypatch.setattr(settings, "identity_dev_bypass", True)
    _user("owner")

    fields = {issue.field for issue in validate_environment() if issue.level == "error"}

    assert "MIRRAGE_IDENTITY_DEV_BYPASS" in fields


def test_enforced_mode_requires_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "identity_mode", "enforced")

    fields = {issue.field for issue in validate_environment() if issue.level == "error"}

    assert "MIRRAGE_IDENTITY_DATABASE_PATH" in fields


def test_owner_management_endpoints_do_not_return_device_secrets(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_dev_bypass(monkeypatch)
    owner = _user()
    owner_device = _device(owner)
    family = client.post(
        "/api/identity/users",
        headers=_headers(owner_device.token),
        json={"display_name": "Sample Family", "role": "family"},
    ).json()
    enrollment = client.post(
        "/api/identity/devices",
        headers=_headers(owner_device.token),
        json={
            "user_id": family["public_id"],
            "display_name": "Family Phone",
            "device_type": "phone",
            "trust_level": "trusted",
        },
    )

    assert enrollment.status_code == 201
    token = enrollment.json()["token"]
    listed = client.get("/api/identity/devices", headers=_headers(owner_device.token))
    assert token not in json.dumps(listed.json())
    assert "token_hash" not in json.dumps(listed.json())


def test_guest_cannot_manage_users(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_dev_bypass(monkeypatch)
    _user("owner")
    guest = _user("guest")
    token = _device(guest).token

    response = client.post(
        "/api/identity/users",
        headers=_headers(token),
        json={"display_name": "Escalated", "role": "owner"},
    )

    assert response.status_code == 403


def test_explicit_deny_is_enforced_on_owner_management_route(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_dev_bypass(monkeypatch)
    owner = _user()
    owner_device = _device(owner)
    identity_store.set_permission_override(
        user_public_id=owner.public_id,
        permission=Permission.IDENTITY_DEVICES_MANAGE.value,
        effect="deny",
        actor_user_id=None,
    )

    response = client.post(
        "/api/identity/devices",
        headers=_headers(owner_device.token),
        json={
            "user_id": owner.public_id,
            "display_name": "Denied Device",
            "device_type": "phone",
            "trust_level": "trusted",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["policy_id"] == (
        "permission.effective.default_deny"
    )


def test_identity_health_is_safe(
    client: TestClient,
) -> None:
    _user("owner", "Private Owner Name")

    response = client.get("/api/health/full")

    identity = next(
        check for check in response.json()["checks"] if check["name"] == "identity"
    )
    assert identity["details"]["owner_present"] is True
    assert "Private Owner Name" not in json.dumps(identity)


def test_identity_backup_and_restore_preserves_memory_backup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    backup_dir = tmp_path / "backups"
    memory_path = tmp_path / "memory.sqlite3"
    monkeypatch.setattr(settings, "backup_directory", str(backup_dir))
    monkeypatch.setattr(settings, "memory_database_path", str(memory_path))
    original = _user("owner", "Original Owner")
    identity_backup = create_identity_backup()
    memory_backup = create_memory_backup()
    identity_store.update_user(original.public_id, display_name="Changed Owner")

    restore_identity_backup(identity_backup.destination)

    assert identity_store.get_user(original.public_id).display_name == "Original Owner"
    assert Path(memory_backup.destination).exists()


def test_audit_metadata_redacts_private_values() -> None:
    event = identity_store.append_audit_event(
        event_type="redaction_test",
        metadata={
            "token": "must-not-appear",
            "memory_value": "private memory",
            "calendar_title": "private event",
            "safe_count": 2,
        },
    )

    payload = json.dumps(event.model_dump())
    assert "must-not-appear" not in payload
    assert "private memory" not in payload
    assert "private event" not in payload
    assert event.metadata == {"safe_count": 2}


def test_audit_events_are_append_only() -> None:
    event = identity_store.append_audit_event(event_type="append_only_test")

    with identity_store.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE audit_events SET event_type = 'changed' WHERE public_id = ?",
                (event.public_id,),
            )


def test_audit_api_paginates_and_filters(
    client: TestClient,
) -> None:
    identity_store.append_audit_event(event_type="first")
    identity_store.append_audit_event(event_type="second")

    response = client.get("/api/audit/events?event_type=second&limit=1")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["items"][0]["event_type"] == "second"
