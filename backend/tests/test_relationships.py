"""Phase 39 relationship, personalization, privacy, and session tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from ai.context_builder import build_runtime_context
from backend.app.services.authorization import (
    effective_permissions,
    principal_for_device,
)
from backend.app.services.backups import create_identity_backup
from backend.app.services.identity_store import identity_store
from backend.app.services.personalization import (
    build_safe_personalization_context,
    greeting_for,
    is_quiet_hours,
)
from backend.app.services.proactive import get_proactive_summary
from backend.app.services.relationship_models import (
    PersonalizationProfileUpdate,
    RelationshipCreateRequest,
)
from backend.app.services.relationship_store import relationship_store
from backend.app.settings import settings


def _user(role: str, name: str, *, household: bool = True):
    return identity_store.create_user(
        display_name=name, role=role, household_member=household
    )


def _device(user, *, device_type: str = "mirror"):
    return identity_store.enroll_device(
        user_public_id=user.public_id,
        display_name=f"{user.display_name} device",
        device_type=device_type,
        trust_level="trusted",
    )


def _device_headers(enrollment) -> dict[str, str]:
    return {"Authorization": f"Bearer {enrollment.token}"}


def _session_headers(client: TestClient, enrollment) -> dict[str, str]:
    headers = _device_headers(enrollment)
    response = client.post("/api/sessions", headers=headers, json={})
    assert response.status_code == 201, response.text
    return {
        **headers,
        "X-Mirrage-Human-Session": response.json()["token"],
    }


@pytest.fixture
def enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "identity_dev_bypass", False)


def test_phase_38_database_migrates_to_profiles_without_data_loss() -> None:
    path = identity_store.database_path()
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                household_member INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                disabled_at TEXT
            );
            INSERT INTO schema_migrations VALUES (1, '2026-01-01T00:00:00+00:00');
            INSERT INTO users(
                public_id, display_name, role, status, household_member,
                created_at, updated_at
            ) VALUES(
                'sample-owner', 'Sample Owner', 'owner', 'active', 1,
                '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'
            );
            """
        )

    identity_store.initialize()
    identity_store.initialize()

    assert identity_store.schema_version() == 2
    assert identity_store.get_user("sample-owner").display_name == "Sample Owner"
    profile = relationship_store.get_profile("sample-owner")
    assert profile.preferred_display_name == "Sample Owner"
    assert set(profile.visibility.values()) == {"private"}


def test_profile_is_owned_and_owner_role_is_not_a_privacy_bypass(
    client: TestClient, enforced: None
) -> None:
    owner = _user("owner", "Sample Owner")
    family = _user("family", "Sample Family")
    owner_headers = _session_headers(client, _device(owner))
    family_headers = _session_headers(client, _device(family))

    updated = client.patch(
        "/api/profile/me",
        headers=family_headers,
        json={
            "preferred_display_name": "Family Preferred",
            "response_tone": "warm",
            "visibility": {"response_tone": "public"},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["preferred_display_name"] == "Family Preferred"

    visible = client.get(f"/api/profiles/{family.public_id}", headers=owner_headers)
    assert visible.status_code == 200
    assert visible.json()["fields"] == {"response_tone": "warm"}


def test_relationship_requires_consent_and_never_changes_permissions(
    client: TestClient, enforced: None
) -> None:
    owner = _user("owner", "Sample Owner")
    family = _user("family", "Sample Family")
    owner_headers = _session_headers(client, _device(owner))
    family_headers = _session_headers(client, _device(family))
    before = effective_permissions(family)

    created = client.post(
        "/api/relationships",
        headers=owner_headers,
        json={"target_user_id": family.public_id, "relationship_type": "relative"},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "pending"

    duplicate = client.post(
        "/api/relationships",
        headers=owner_headers,
        json={"target_user_id": family.public_id, "relationship_type": "relative"},
    )
    assert duplicate.status_code == 409

    accepted = client.post(
        f"/api/relationships/{created.json()['public_id']}/accept",
        headers=family_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "active"
    assert effective_permissions(family) == before


def test_relationship_rejection_and_archive(client: TestClient, enforced: None) -> None:
    owner = _user("owner", "Sample Owner")
    family = _user("family", "Sample Family")
    guest = _user("trusted_guest", "Sample Guest", household=False)
    owner_headers = _session_headers(client, _device(owner))
    family_headers = _session_headers(client, _device(family))
    guest_headers = _session_headers(client, _device(guest))

    rejected_request = client.post(
        "/api/relationships",
        headers=owner_headers,
        json={"target_user_id": guest.public_id, "relationship_type": "friend"},
    ).json()
    rejected = client.post(
        f"/api/relationships/{rejected_request['public_id']}/reject",
        headers=guest_headers,
    )
    assert rejected.json()["status"] == "rejected"

    active_request = client.post(
        "/api/relationships",
        headers=owner_headers,
        json={"target_user_id": family.public_id, "relationship_type": "relative"},
    ).json()
    client.post(
        f"/api/relationships/{active_request['public_id']}/accept",
        headers=family_headers,
    )
    archived = client.post(
        f"/api/relationships/{active_request['public_id']}/archive",
        headers=owner_headers,
    )
    assert archived.json()["status"] == "archived"


def test_self_relationship_is_rejected(client: TestClient, enforced: None) -> None:
    owner = _user("owner", "Sample Owner")
    headers = _session_headers(client, _device(owner))
    response = client.post(
        "/api/relationships",
        headers=headers,
        json={"target_user_id": owner.public_id, "relationship_type": "friend"},
    )
    assert response.status_code == 422


def test_shared_context_defaults_private_and_sharing_is_revocable(
    client: TestClient, enforced: None
) -> None:
    owner = _user("owner", "Sample Owner")
    family = _user("family", "Sample Family")
    owner_headers = _session_headers(client, _device(owner))
    family_headers = _session_headers(client, _device(family))

    created = client.post(
        "/api/shared-context",
        headers=owner_headers,
        json={"context_type": "project", "title": "Mirror", "value": "Test frame"},
    )
    assert created.status_code == 201
    item = created.json()
    assert item["visibility"] == "private"
    assert (
        client.get("/api/shared-context", headers=family_headers).json()["count"] == 0
    )

    shared = client.post(
        f"/api/shared-context/{item['public_id']}/share",
        headers=owner_headers,
        json={"user_id": family.public_id},
    )
    assert family.public_id in shared.json()["shared_with_user_ids"]
    family_items = client.get("/api/shared-context", headers=family_headers).json()
    assert family_items["items"][0]["value"] == "Test frame"

    revoked = client.post(
        f"/api/shared-context/{item['public_id']}/revoke",
        headers=owner_headers,
        json={"user_id": family.public_id},
    )
    assert revoked.json()["shared_with_user_ids"] == []
    assert (
        client.get("/api/shared-context", headers=family_headers).json()["count"] == 0
    )


def test_relationship_and_household_visibility_are_explicit(
    client: TestClient, enforced: None
) -> None:
    owner = _user("owner", "Sample Owner")
    family = _user("family", "Sample Family")
    owner_headers = _session_headers(client, _device(owner))
    family_headers = _session_headers(client, _device(family))
    relationship = client.post(
        "/api/relationships",
        headers=owner_headers,
        json={"target_user_id": family.public_id, "relationship_type": "relative"},
    ).json()
    client.post(
        f"/api/relationships/{relationship['public_id']}/accept",
        headers=family_headers,
    )

    client.post(
        "/api/shared-context",
        headers=owner_headers,
        json={
            "context_type": "plan",
            "title": "Dinner",
            "value": "At seven",
            "visibility": "relationship",
        },
    )
    household = client.post(
        "/api/shared-context",
        headers=owner_headers,
        json={
            "context_type": "fact",
            "title": "Bins",
            "value": "Thursday",
            "visibility": "household",
        },
    )
    assert household.status_code == 201
    assert (
        client.get("/api/shared-context", headers=family_headers).json()["count"] == 2
    )


def test_sensitive_shared_context_categories_are_rejected(
    client: TestClient, enforced: None
) -> None:
    owner = _user("owner", "Sample Owner")
    headers = _session_headers(client, _device(owner))
    response = client.post(
        "/api/shared-context",
        headers=headers,
        json={
            "context_type": "fact",
            "title": "Medical note",
            "value": "Private detail",
        },
    )
    assert response.status_code == 422


def test_mirror_device_requires_explicit_human_session(
    client: TestClient, enforced: None
) -> None:
    owner = _user("owner", "Sample Owner")
    enrollment = _device(owner)
    device_headers = _device_headers(enrollment)

    blocked = client.get("/api/profile/me", headers=device_headers)
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["policy_id"] == "human_session.required_for_mirror"
    greeting = client.get("/api/greeting", headers=device_headers).json()
    assert greeting["text"] == "Hello."
    assert greeting["personalized"] is False
    anonymous = client.get("/api/greeting").json()
    assert anonymous["text"] == "Hello."
    assert anonymous["spoken_allowed"] is False

    session_headers = _session_headers(client, enrollment)
    assert client.get("/api/profile/me", headers=session_headers).status_code == 200
    me = client.get("/api/identity/me", headers=session_headers).json()
    assert me["human_session_active"] is True


def test_unverified_mirror_proactive_context_keeps_principal_filtering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _user("owner", "Sample Owner")
    enrollment = _device(owner)
    principal = principal_for_device(
        owner, enrollment.device, correlation_id="proactive-private"
    )
    captured = None

    def unavailable_context(current_principal=None):
        nonlocal captured
        captured = current_principal
        raise RuntimeError("context unavailable")

    monkeypatch.setattr(
        "backend.app.services.proactive.get_daily_context", unavailable_context
    )
    summary = get_proactive_summary(principal)

    assert captured is principal
    assert summary.status == "unavailable"


def test_human_session_token_is_returned_once_and_stored_as_hash(
    client: TestClient, enforced: None
) -> None:
    owner = _user("owner", "Sample Owner")
    enrollment = _device(owner)
    created = client.post("/api/sessions", headers=_device_headers(enrollment), json={})
    token = created.json()["token"]
    session_id = created.json()["session"]["public_id"]
    with identity_store.connect() as connection:
        row = connection.execute(
            "SELECT token_hash FROM interaction_sessions WHERE public_id = ?",
            (session_id,),
        ).fetchone()
    assert row["token_hash"] != token
    assert token not in str(client.get("/api/health/full").json())


def test_greeting_quiet_hours_and_proactivity_are_deterministic() -> None:
    owner = _user("owner", "Sample Owner")
    enrollment = _device(owner, device_type="desktop")
    relationship_store.update_profile(
        owner.public_id,
        PersonalizationProfileUpdate(
            preferred_display_name="Sample",
            greeting_style="warm",
            proactivity="standard",
            personalized_greeting=True,
            spoken_announcements=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            time_zone="UTC",
        ),
    )
    profile = relationship_store.get_profile(owner.public_id)
    assert is_quiet_hours(profile, datetime(2026, 7, 18, 23, 0, tzinfo=UTC))
    principal = principal_for_device(
        owner, enrollment.device, correlation_id="greeting"
    )
    greeting = greeting_for(principal)
    assert "Sample" in greeting.text


def test_local_and_cloud_personalization_are_separated() -> None:
    owner = _user("owner", "Sample Owner")
    enrollment = _device(owner, device_type="desktop")
    relationship_store.update_profile(
        owner.public_id,
        PersonalizationProfileUpdate(
            preferred_display_name="Private Preferred",
            response_tone="warm",
            cloud_personalization_opt_in=True,
            visibility={"preferred_display_name": "private"},
        ),
    )
    principal = principal_for_device(owner, enrollment.device, correlation_id="ai")
    context = build_safe_personalization_context(principal)
    assert "Private Preferred" in " ".join(context.local_lines)
    assert "Private Preferred" not in " ".join(context.cloud_lines)
    assert "Response tone: warm" in " ".join(context.cloud_lines)

    runtime = build_runtime_context("Hello", principal=principal)
    assert "Private Preferred" in runtime.local_prompt
    assert "Private Preferred" not in runtime.cloud_prompt


def test_profile_and_sharing_audits_exclude_private_values(
    client: TestClient, enforced: None
) -> None:
    owner = _user("owner", "Sample Owner")
    headers = _session_headers(client, _device(owner))
    private_value = "Do not copy this private content into audit logs"
    client.patch(
        "/api/profile/me",
        headers=headers,
        json={"preferred_display_name": "Private Preferred"},
    )
    client.post(
        "/api/shared-context",
        headers=headers,
        json={"context_type": "project", "title": "Private", "value": private_value},
    )
    events, _ = identity_store.list_audit_events(limit=100)
    serialized = " ".join(str(event.model_dump()) for event in events)
    assert private_value not in serialized
    assert "Private Preferred" not in serialized


def test_relationship_health_and_backup_include_phase_39_tables(
    client: TestClient, tmp_path, enforced: None
) -> None:
    owner = _user("owner", "Sample Owner")
    headers = _session_headers(client, _device(owner))
    health = client.get("/api/health/full", headers=headers)
    relationship_check = next(
        item for item in health.json()["checks"] if item["name"] == "relationships"
    )
    assert relationship_check["status"] == "ok"
    assert relationship_check["details"]["profile_count"] == 1

    backup = create_identity_backup(tmp_path / "backup")
    with sqlite3.connect(backup.destination) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM personalization_profiles"
            ).fetchone()[0]
            == 1
        )
        connection.execute("SELECT COUNT(*) FROM relationships").fetchone()
        connection.execute("SELECT COUNT(*) FROM shared_context_items").fetchone()


def test_relationship_store_rejects_implicit_or_invalid_relationships() -> None:
    owner = _user("owner", "Sample Owner")
    with pytest.raises(Exception, match="self"):
        relationship_store.propose_relationship(
            owner.public_id,
            RelationshipCreateRequest(
                target_user_id=owner.public_id, relationship_type="friend"
            ),
        )
