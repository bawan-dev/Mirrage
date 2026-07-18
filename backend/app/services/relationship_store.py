"""Persistence for private profiles, consented relationships, and shared context."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.app.services.identity_store import (
    IdentityConflictError,
    IdentityNotFoundError,
    IdentityValidationError,
    identity_store,
)
from backend.app.services.relationship_models import (
    HumanSessionEnrollmentResponse,
    HumanSessionResponse,
    PersonalizationProfileResponse,
    PersonalizationProfileUpdate,
    RelationshipCreateRequest,
    RelationshipResponse,
    SharedContextCreateRequest,
    SharedContextResponse,
    SharedContextUpdateRequest,
    default_profile_visibility,
)
from backend.app.settings import settings

_SENSITIVE_TERMS = {
    "political",
    "politics",
    "religion",
    "religious",
    "sexuality",
    "diagnosis",
    "medical",
    "medication",
    "mental health",
    "therapy",
    "bank account",
    "credit score",
    "financial status",
    "relationship quality",
    "emotional state",
}


class RelationshipStore:
    """Owns Phase 39 data without changing Phase 38 authorization policy."""

    def ensure_profile(self, user_id: str) -> PersonalizationProfileResponse:
        user = identity_store.get_user(user_id)
        timestamp = _now()
        with identity_store.connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO personalization_profiles(
                       user_id, preferred_display_name, visibility_json,
                       created_at, updated_at
                   ) VALUES(
                       (SELECT id FROM users WHERE public_id = ?), ?, ?, ?, ?
                   )""",
                (
                    user.public_id,
                    user.display_name,
                    json.dumps(default_profile_visibility(), separators=(",", ":")),
                    timestamp,
                    timestamp,
                ),
            )
        return self.get_profile(user_id)

    def get_profile(self, user_id: str) -> PersonalizationProfileResponse:
        identity_store.initialize()
        with identity_store.connect() as connection:
            row = connection.execute(
                _PROFILE_SELECT + " WHERE u.public_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            identity_store.get_user(user_id)
            return self.ensure_profile(user_id)
        return _profile_response(row)

    def update_profile(
        self, user_id: str, update: PersonalizationProfileUpdate
    ) -> PersonalizationProfileResponse:
        current = self.get_profile(user_id)
        changes = update.model_dump(exclude_unset=True)
        visibility_changes = changes.pop("visibility", None)
        if "time_zone" in changes:
            _validate_time_zone(str(changes["time_zone"]))

        visibility = dict(current.visibility)
        if visibility_changes:
            visibility.update(visibility_changes)

        columns = {
            "preferred_display_name": current.preferred_display_name,
            "preferred_language": current.preferred_language,
            "response_tone": current.response_tone,
            "response_length": current.response_length,
            "greeting_style": current.greeting_style,
            "humour": current.humour,
            "proactivity": current.proactivity,
            "quiet_hours_start": current.quiet_hours_start,
            "quiet_hours_end": current.quiet_hours_end,
            "time_zone": current.time_zone,
            "spoken_announcements": current.spoken_announcements,
            "personalized_greeting": current.personalized_greeting,
            "cloud_personalization_opt_in": current.cloud_personalization_opt_in,
        }
        columns.update(changes)
        timestamp = _now()
        with identity_store.connect() as connection:
            connection.execute(
                """UPDATE personalization_profiles SET
                       preferred_display_name = ?, preferred_language = ?,
                       response_tone = ?, response_length = ?, greeting_style = ?,
                       humour = ?, proactivity = ?, quiet_hours_start = ?,
                       quiet_hours_end = ?, time_zone = ?,
                       spoken_announcements = ?, personalized_greeting = ?,
                       cloud_personalization_opt_in = ?, visibility_json = ?,
                       updated_at = ?
                   WHERE user_id = (SELECT id FROM users WHERE public_id = ?)""",
                (
                    columns["preferred_display_name"],
                    columns["preferred_language"],
                    columns["response_tone"],
                    columns["response_length"],
                    columns["greeting_style"],
                    columns["humour"],
                    columns["proactivity"],
                    columns["quiet_hours_start"],
                    columns["quiet_hours_end"],
                    columns["time_zone"],
                    int(bool(columns["spoken_announcements"])),
                    int(bool(columns["personalized_greeting"])),
                    int(bool(columns["cloud_personalization_opt_in"])),
                    json.dumps(visibility, separators=(",", ":")),
                    timestamp,
                    user_id,
                ),
            )
        return self.get_profile(user_id)

    def propose_relationship(
        self, proposer_id: str, request: RelationshipCreateRequest
    ) -> RelationshipResponse:
        if proposer_id == request.target_user_id:
            raise IdentityValidationError(
                "A user cannot have a relationship with self."
            )
        proposer = identity_store.get_user(proposer_id)
        target = identity_store.get_user(request.target_user_id)
        if proposer.status != "active" or target.status != "active":
            raise IdentityConflictError("Relationships require two active users.")

        public_id = str(uuid4())
        timestamp = _now()
        try:
            with identity_store.connect() as connection:
                proposer_row = _user_row(connection, proposer_id)
                target_row = _user_row(connection, request.target_user_id)
                user_a, user_b = sorted(
                    (int(proposer_row["id"]), int(target_row["id"]))
                )
                connection.execute(
                    """INSERT INTO relationships(
                           public_id, user_a_id, user_b_id, proposed_by_user_id,
                           proposed_to_user_id, relationship_type, custom_label,
                           status, created_at, updated_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                    (
                        public_id,
                        user_a,
                        user_b,
                        proposer_row["id"],
                        target_row["id"],
                        request.relationship_type,
                        request.custom_label,
                        timestamp,
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise IdentityConflictError(
                "A pending or active relationship already exists for these users."
            ) from exc
        return self.get_relationship(public_id, proposer_id)

    def list_relationships(self, user_id: str) -> list[RelationshipResponse]:
        identity_store.initialize()
        with identity_store.connect() as connection:
            rows = connection.execute(
                _RELATIONSHIP_SELECT
                + " WHERE ua.public_id = ? OR ub.public_id = ?"
                + " ORDER BY r.created_at DESC",
                (user_id, user_id),
            ).fetchall()
        return [_relationship_response(row) for row in rows]

    def get_relationship(
        self, relationship_id: str, actor_user_id: str
    ) -> RelationshipResponse:
        with identity_store.connect() as connection:
            row = connection.execute(
                _RELATIONSHIP_SELECT + " WHERE r.public_id = ?",
                (relationship_id,),
            ).fetchone()
        if row is None:
            raise IdentityNotFoundError("Relationship was not found.")
        result = _relationship_response(row)
        if actor_user_id not in {result.user_a_id, result.user_b_id}:
            raise IdentityNotFoundError("Relationship was not found.")
        return result

    def respond_relationship(
        self, relationship_id: str, actor_user_id: str, decision: str
    ) -> RelationshipResponse:
        relationship = self.get_relationship(relationship_id, actor_user_id)
        if relationship.status != "pending":
            raise IdentityConflictError("Only pending relationships can be answered.")
        if relationship.proposed_to_user_id != actor_user_id:
            raise IdentityConflictError(
                "Only the invited user can answer this request."
            )
        if decision not in {"active", "rejected"}:
            raise IdentityValidationError("Unknown relationship decision.")
        timestamp = _now()
        with identity_store.connect() as connection:
            connection.execute(
                """UPDATE relationships SET status = ?, updated_at = ?, responded_at = ?
                   WHERE public_id = ?""",
                (decision, timestamp, timestamp, relationship_id),
            )
        return self.get_relationship(relationship_id, actor_user_id)

    def archive_relationship(
        self, relationship_id: str, actor_user_id: str
    ) -> RelationshipResponse:
        relationship = self.get_relationship(relationship_id, actor_user_id)
        if relationship.status == "archived":
            return relationship
        timestamp = _now()
        with identity_store.connect() as connection:
            connection.execute(
                """UPDATE relationships SET status = 'archived', updated_at = ?,
                          archived_at = ? WHERE public_id = ?""",
                (timestamp, timestamp, relationship_id),
            )
        return self.get_relationship(relationship_id, actor_user_id)

    def active_relationship(self, first_user_id: str, second_user_id: str) -> bool:
        if first_user_id == second_user_id:
            return False
        with identity_store.connect() as connection:
            row = connection.execute(
                """SELECT 1 FROM relationships r
                   JOIN users ua ON ua.id = r.user_a_id
                   JOIN users ub ON ub.id = r.user_b_id
                   WHERE r.status = 'active'
                     AND ((ua.public_id = ? AND ub.public_id = ?)
                       OR (ua.public_id = ? AND ub.public_id = ?))""",
                (first_user_id, second_user_id, second_user_id, first_user_id),
            ).fetchone()
        return row is not None

    def create_shared_context(
        self, owner_id: str, request: SharedContextCreateRequest
    ) -> SharedContextResponse:
        _validate_shared_content(request.title, request.value)
        identity_store.get_user(owner_id)
        public_id = str(uuid4())
        timestamp = _now()
        with identity_store.connect() as connection:
            connection.execute(
                """INSERT INTO shared_context_items(
                       public_id, owner_user_id, context_type, title, value,
                       visibility, status, created_at, updated_at
                   ) VALUES(
                       ?, (SELECT id FROM users WHERE public_id = ?), ?, ?, ?, ?,
                       'active', ?, ?
                   )""",
                (
                    public_id,
                    owner_id,
                    request.context_type,
                    request.title.strip(),
                    request.value.strip(),
                    request.visibility,
                    timestamp,
                    timestamp,
                ),
            )
        return self.get_shared_context(public_id, owner_id)

    def list_shared_context(self, viewer_id: str) -> list[SharedContextResponse]:
        viewer = identity_store.get_user(viewer_id)
        with identity_store.connect() as connection:
            rows = connection.execute(
                _SHARED_CONTEXT_SELECT
                + " WHERE sci.status = 'active' ORDER BY sci.created_at DESC"
            ).fetchall()
        return [
            _shared_context_response(row, self._shared_user_ids(int(row["id"])))
            for row in rows
            if self._can_view_shared_row(row, viewer.public_id, viewer.household_member)
        ]

    def get_shared_context(
        self, context_id: str, viewer_id: str
    ) -> SharedContextResponse:
        viewer = identity_store.get_user(viewer_id)
        with identity_store.connect() as connection:
            row = connection.execute(
                _SHARED_CONTEXT_SELECT + " WHERE sci.public_id = ?", (context_id,)
            ).fetchone()
        if row is None or not self._can_view_shared_row(
            row, viewer.public_id, viewer.household_member
        ):
            raise IdentityNotFoundError("Shared context was not found.")
        return _shared_context_response(row, self._shared_user_ids(int(row["id"])))

    def update_shared_context(
        self,
        context_id: str,
        owner_id: str,
        update: SharedContextUpdateRequest,
    ) -> SharedContextResponse:
        current = self._owned_shared_context(context_id, owner_id)
        changes = update.model_dump(exclude_unset=True)
        title = str(changes.get("title", current.title))
        value = str(changes.get("value", current.value))
        _validate_shared_content(title, value)
        with identity_store.connect() as connection:
            connection.execute(
                """UPDATE shared_context_items SET context_type = ?, title = ?,
                          value = ?, visibility = ?, updated_at = ?
                   WHERE public_id = ?""",
                (
                    changes.get("context_type", current.context_type),
                    title.strip(),
                    value.strip(),
                    changes.get("visibility", current.visibility),
                    _now(),
                    context_id,
                ),
            )
        return self.get_shared_context(context_id, owner_id)

    def share_context(
        self, context_id: str, owner_id: str, target_user_id: str
    ) -> SharedContextResponse:
        self._owned_shared_context(context_id, owner_id)
        if owner_id == target_user_id:
            raise IdentityValidationError("Context is already visible to its owner.")
        target = identity_store.get_user(target_user_id)
        if target.status != "active":
            raise IdentityConflictError(
                "Context can only be shared with an active user."
            )
        with identity_store.connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO shared_context_access(
                       context_item_id, user_id, created_at
                   ) VALUES(
                       (SELECT id FROM shared_context_items WHERE public_id = ?),
                       (SELECT id FROM users WHERE public_id = ?), ?
                   )""",
                (context_id, target_user_id, _now()),
            )
        return self.get_shared_context(context_id, owner_id)

    def revoke_context(
        self, context_id: str, owner_id: str, target_user_id: str
    ) -> SharedContextResponse:
        self._owned_shared_context(context_id, owner_id)
        with identity_store.connect() as connection:
            connection.execute(
                """DELETE FROM shared_context_access
                   WHERE context_item_id = (
                       SELECT id FROM shared_context_items WHERE public_id = ?
                   ) AND user_id = (SELECT id FROM users WHERE public_id = ?)""",
                (context_id, target_user_id),
            )
        return self.get_shared_context(context_id, owner_id)

    def archive_context(self, context_id: str, owner_id: str) -> SharedContextResponse:
        self._owned_shared_context(context_id, owner_id)
        timestamp = _now()
        with identity_store.connect() as connection:
            connection.execute(
                """UPDATE shared_context_items SET status = 'archived',
                          archived_at = ?, updated_at = ? WHERE public_id = ?""",
                (timestamp, timestamp, context_id),
            )
        return self.get_shared_context(context_id, owner_id)

    def create_human_session(
        self, user_id: str, device_id: str, duration_seconds: int | None = None
    ) -> HumanSessionEnrollmentResponse:
        device = identity_store.get_device(device_id)
        if device.user_id != user_id:
            raise IdentityConflictError("The device and selected user do not match.")
        duration = duration_seconds or settings.human_session_ttl_seconds
        if not 60 <= duration <= 86400:
            raise IdentityValidationError("Human session duration is out of range.")
        public_id = str(uuid4())
        prefix = f"mhs_{public_id.replace('-', '')[:12]}"
        token = f"{prefix}_{secrets.token_urlsafe(32)}"
        timestamp = datetime.now(UTC)
        with identity_store.connect() as connection:
            connection.execute(
                """INSERT INTO interaction_sessions(
                       public_id, user_id, device_id, token_prefix, token_hash,
                       status, created_at, expires_at, last_seen_at
                   ) VALUES(
                       ?, (SELECT id FROM users WHERE public_id = ?),
                       (SELECT id FROM trusted_devices WHERE public_id = ?),
                       ?, ?, 'active', ?, ?, ?
                   )""",
                (
                    public_id,
                    user_id,
                    device_id,
                    prefix,
                    _hash(token),
                    timestamp.isoformat(),
                    (timestamp + timedelta(seconds=duration)).isoformat(),
                    timestamp.isoformat(),
                ),
            )
        return HumanSessionEnrollmentResponse(
            session=self.get_human_session(public_id, user_id), token=token
        )

    def authenticate_human_session(
        self, token: str, user_id: str, device_id: str
    ) -> HumanSessionResponse | None:
        prefix = _session_prefix(token)
        if prefix is None:
            return None
        with identity_store.connect() as connection:
            row = connection.execute(
                _SESSION_SELECT + " WHERE s.token_prefix = ?", (prefix,)
            ).fetchone()
            if row is None or not hmac.compare_digest(
                str(row["token_hash"]), _hash(token)
            ):
                return None
            if row["user_public_id"] != user_id or row["device_public_id"] != device_id:
                return None
            if row["status"] != "active":
                return None
            if datetime.fromisoformat(row["expires_at"]) <= datetime.now(UTC):
                connection.execute(
                    """UPDATE interaction_sessions SET status = 'expired', ended_at = ?
                       WHERE id = ?""",
                    (_now(), row["id"]),
                )
                return None
            connection.execute(
                "UPDATE interaction_sessions SET last_seen_at = ? WHERE id = ?",
                (_now(), row["id"]),
            )
        return _session_response(row)

    def get_human_session(self, session_id: str, user_id: str) -> HumanSessionResponse:
        with identity_store.connect() as connection:
            row = connection.execute(
                _SESSION_SELECT + " WHERE s.public_id = ? AND u.public_id = ?",
                (session_id, user_id),
            ).fetchone()
        if row is None:
            raise IdentityNotFoundError("Interaction session was not found.")
        return _session_response(row)

    def end_human_session(self, session_id: str, user_id: str) -> HumanSessionResponse:
        self.get_human_session(session_id, user_id)
        with identity_store.connect() as connection:
            connection.execute(
                """UPDATE interaction_sessions SET status = 'ended', ended_at = ?
                   WHERE public_id = ? AND user_id = (
                       SELECT id FROM users WHERE public_id = ?
                   )""",
                (_now(), session_id, user_id),
            )
        return self.get_human_session(session_id, user_id)

    def status(self) -> dict[str, Any]:
        identity_store.initialize()
        with identity_store.connect() as connection:
            result = {
                "database_status": "ok",
                "profile_count": connection.execute(
                    "SELECT COUNT(*) FROM personalization_profiles"
                ).fetchone()[0],
                "active_relationship_count": connection.execute(
                    "SELECT COUNT(*) FROM relationships WHERE status = 'active'"
                ).fetchone()[0],
                "pending_relationship_count": connection.execute(
                    "SELECT COUNT(*) FROM relationships WHERE status = 'pending'"
                ).fetchone()[0],
                "active_shared_context_count": connection.execute(
                    "SELECT COUNT(*) FROM shared_context_items WHERE status = 'active'"
                ).fetchone()[0],
                "active_human_session_count": connection.execute(
                    """SELECT COUNT(*) FROM interaction_sessions
                       WHERE status = 'active' AND expires_at > ?""",
                    (_now(),),
                ).fetchone()[0],
            }
        return {
            key: int(value) if key.endswith("_count") else value
            for key, value in result.items()
        }

    def _owned_shared_context(
        self, context_id: str, owner_id: str
    ) -> SharedContextResponse:
        item = self.get_shared_context(context_id, owner_id)
        if item.owner_user_id != owner_id:
            raise IdentityNotFoundError("Shared context was not found.")
        return item

    def _shared_user_ids(self, item_id: int) -> list[str]:
        with identity_store.connect() as connection:
            rows = connection.execute(
                """SELECT u.public_id FROM shared_context_access sca
                   JOIN users u ON u.id = sca.user_id
                   WHERE sca.context_item_id = ? ORDER BY u.public_id""",
                (item_id,),
            ).fetchall()
        return [str(row["public_id"]) for row in rows]

    def _can_view_shared_row(
        self, row: sqlite3.Row, viewer_id: str, viewer_household: bool
    ) -> bool:
        owner_id = str(row["owner_public_id"])
        if viewer_id == owner_id:
            return True
        if viewer_id in self._shared_user_ids(int(row["id"])):
            return True
        if row["visibility"] == "public":
            return True
        if row["visibility"] == "household" and viewer_household:
            owner = identity_store.get_user(owner_id)
            return owner.household_member
        if row["visibility"] == "relationship":
            return self.active_relationship(owner_id, viewer_id)
        return False


_PROFILE_SELECT = """SELECT u.public_id AS user_public_id,
    p.preferred_display_name, p.preferred_language, p.response_tone,
    p.response_length, p.greeting_style, p.humour, p.proactivity,
    p.quiet_hours_start, p.quiet_hours_end, p.time_zone,
    p.spoken_announcements, p.personalized_greeting,
    p.cloud_personalization_opt_in, p.visibility_json,
    p.created_at, p.updated_at
    FROM personalization_profiles p JOIN users u ON u.id = p.user_id"""

_RELATIONSHIP_SELECT = """SELECT r.public_id,
    ua.public_id AS user_a_public_id, ub.public_id AS user_b_public_id,
    proposer.public_id AS proposed_by_public_id,
    target.public_id AS proposed_to_public_id, r.relationship_type,
    r.custom_label, r.status, r.created_at, r.updated_at,
    r.responded_at, r.archived_at
    FROM relationships r
    JOIN users ua ON ua.id = r.user_a_id
    JOIN users ub ON ub.id = r.user_b_id
    JOIN users proposer ON proposer.id = r.proposed_by_user_id
    JOIN users target ON target.id = r.proposed_to_user_id"""

_SHARED_CONTEXT_SELECT = """SELECT sci.id, sci.public_id,
    owner.public_id AS owner_public_id, sci.context_type, sci.title,
    sci.value, sci.visibility, sci.status, sci.created_at, sci.updated_at,
    sci.archived_at FROM shared_context_items sci
    JOIN users owner ON owner.id = sci.owner_user_id"""

_SESSION_SELECT = """SELECT s.id, s.public_id, u.public_id AS user_public_id,
    d.public_id AS device_public_id, s.token_hash, s.status, s.created_at,
    s.expires_at, s.ended_at, s.last_seen_at FROM interaction_sessions s
    JOIN users u ON u.id = s.user_id JOIN trusted_devices d ON d.id = s.device_id"""


def _profile_response(row: sqlite3.Row) -> PersonalizationProfileResponse:
    return PersonalizationProfileResponse(
        user_id=row["user_public_id"],
        preferred_display_name=row["preferred_display_name"],
        preferred_language=row["preferred_language"],
        response_tone=row["response_tone"],
        response_length=row["response_length"],
        greeting_style=row["greeting_style"],
        humour=row["humour"],
        proactivity=row["proactivity"],
        quiet_hours_start=row["quiet_hours_start"],
        quiet_hours_end=row["quiet_hours_end"],
        time_zone=row["time_zone"],
        spoken_announcements=bool(row["spoken_announcements"]),
        personalized_greeting=bool(row["personalized_greeting"]),
        cloud_personalization_opt_in=bool(row["cloud_personalization_opt_in"]),
        visibility=json.loads(row["visibility_json"] or "{}"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _relationship_response(row: sqlite3.Row) -> RelationshipResponse:
    return RelationshipResponse(
        public_id=row["public_id"],
        user_a_id=row["user_a_public_id"],
        user_b_id=row["user_b_public_id"],
        proposed_by_user_id=row["proposed_by_public_id"],
        proposed_to_user_id=row["proposed_to_public_id"],
        relationship_type=row["relationship_type"],
        custom_label=row["custom_label"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        responded_at=row["responded_at"],
        archived_at=row["archived_at"],
    )


def _shared_context_response(
    row: sqlite3.Row, shared_user_ids: list[str]
) -> SharedContextResponse:
    return SharedContextResponse(
        public_id=row["public_id"],
        owner_user_id=row["owner_public_id"],
        context_type=row["context_type"],
        title=row["title"],
        value=row["value"],
        visibility=row["visibility"],
        status=row["status"],
        shared_with_user_ids=shared_user_ids,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        archived_at=row["archived_at"],
    )


def _session_response(row: sqlite3.Row) -> HumanSessionResponse:
    status = row["status"]
    if status == "active" and datetime.fromisoformat(row["expires_at"]) <= datetime.now(
        UTC
    ):
        status = "expired"
    return HumanSessionResponse(
        public_id=row["public_id"],
        user_id=row["user_public_id"],
        device_id=row["device_public_id"],
        status=status,
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        ended_at=row["ended_at"],
        last_seen_at=row["last_seen_at"],
    )


def _user_row(connection: sqlite3.Connection, public_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT id FROM users WHERE public_id = ?", (public_id,)
    ).fetchone()
    if row is None:
        raise IdentityNotFoundError("User was not found.")
    return row


def _validate_time_zone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise IdentityValidationError("Unknown time zone.") from exc


def _validate_shared_content(title: str, value: str) -> None:
    normalized = f"{title} {value}".casefold()
    if any(term in normalized for term in _SENSITIVE_TERMS):
        raise IdentityValidationError(
            "Sensitive personal categories are not supported by shared context."
        )


def _session_prefix(token: str) -> str | None:
    parts = token.split("_", 2)
    if len(parts) != 3 or parts[0] != "mhs" or not parts[1] or not parts[2]:
        return None
    return f"mhs_{parts[1]}"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


relationship_store = RelationshipStore()
