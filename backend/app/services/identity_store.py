"""Persistent SQLite store for identity, devices, approvals, and audit events."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.services.identity_models import (
    ApprovalResponse,
    AuditEventResponse,
    AuthenticatedPrincipal,
    IdentityUserResponse,
    PermissionOverrideResponse,
    TrustedDeviceEnrollmentResponse,
    TrustedDeviceResponse,
)
from backend.app.services.permissions import (
    ROLE_PERMISSIONS,
    is_registered_permission,
)
from backend.app.services.relationship_migrations import (
    RELATIONSHIP_SCHEMA_VERSION,
    migrate_relationship_schema,
)
from backend.app.services.relationship_models import default_profile_visibility
from backend.app.settings import settings

SCHEMA_VERSION = RELATIONSHIP_SCHEMA_VERSION
_REDACTED_METADATA_KEYS = (
    "api_key",
    "audio",
    "calendar",
    "memory",
    "secret",
    "token",
    "transcript",
    "value",
)


class IdentityStoreError(RuntimeError):
    """Base identity store error."""


class IdentityNotFoundError(IdentityStoreError):
    """Raised when a public identity resource does not exist."""


class IdentityConflictError(IdentityStoreError):
    """Raised when an identity safety invariant would be violated."""


class IdentityValidationError(IdentityStoreError):
    """Raised when input does not match the identity policy."""


class IdentityStore:
    """Small parameterized-SQL store with explicit schema ownership."""

    def initialize(self) -> None:
        path = self.database_path()
        if not str(path).strip():
            raise IdentityValidationError("Identity database path is required.")
        path.parent.mkdir(parents=True, exist_ok=True)

        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
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

                CREATE TABLE IF NOT EXISTS permission_overrides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    permission TEXT NOT NULL,
                    effect TEXT NOT NULL,
                    created_by_user_id INTEGER REFERENCES users(id),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, permission)
                );

                CREATE TABLE IF NOT EXISTS trusted_devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    public_id TEXT NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    display_name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    token_prefix TEXT NOT NULL UNIQUE,
                    token_hash TEXT NOT NULL,
                    trust_level TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT,
                    revoked_at TEXT
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    public_id TEXT NOT NULL UNIQUE,
                    requester_user_id INTEGER NOT NULL REFERENCES users(id),
                    requester_device_id INTEGER REFERENCES trusted_devices(id),
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    risk_level TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    reason TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    decided_at TEXT,
                    decided_by_user_id INTEGER REFERENCES users(id),
                    decision_reason TEXT,
                    correlation_id TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    public_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_user_public_id TEXT,
                    actor_role TEXT,
                    device_public_id TEXT,
                    authentication_method TEXT,
                    action TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    authorization_decision TEXT,
                    risk_level TEXT,
                    reason TEXT,
                    result TEXT,
                    correlation_id TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_users_status_role
                    ON users(status, role);
                CREATE INDEX IF NOT EXISTS idx_devices_status_user
                    ON trusted_devices(status, user_id);
                CREATE INDEX IF NOT EXISTS idx_approvals_status_expiry
                    ON approvals(status, expires_at);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                    ON audit_events(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_event_type
                    ON audit_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_audit_actor
                    ON audit_events(actor_user_public_id);
                CREATE INDEX IF NOT EXISTS idx_audit_decision
                    ON audit_events(authorization_decision);

                CREATE TRIGGER IF NOT EXISTS audit_events_no_update
                BEFORE UPDATE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit events are append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
                BEFORE DELETE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit events are append-only');
                END;
                """
            )
            connection.execute(
                """INSERT OR IGNORE INTO schema_migrations(version, applied_at)
                   VALUES (?, ?)""",
                (1, _now()),
            )
            migrate_relationship_schema(connection)

    def database_path(self) -> Path:
        return Path(settings.identity_database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path(), timeout=5.0, check_same_thread=False
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def schema_version(self) -> int:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT MAX(version) AS version FROM schema_migrations"
            ).fetchone()
        return int(row["version"] or 0)

    def status(self) -> dict[str, Any]:
        self.initialize()
        self.expire_approvals()
        with self.connect() as connection:
            active_users = connection.execute(
                "SELECT COUNT(*) AS count FROM users WHERE status = 'active'"
            ).fetchone()["count"]
            owners = connection.execute(
                """SELECT COUNT(*) AS count FROM users
                   WHERE status = 'active' AND role = 'owner'"""
            ).fetchone()["count"]
            devices = connection.execute(
                "SELECT COUNT(*) AS count FROM trusted_devices WHERE status = 'active'"
            ).fetchone()["count"]
            approvals = connection.execute(
                "SELECT COUNT(*) AS count FROM approvals WHERE status = 'pending'"
            ).fetchone()["count"]
            connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()

        return {
            "database_status": "ok",
            "schema_version": self.schema_version(),
            "active_user_count": int(active_users),
            "owner_present": bool(owners),
            "active_device_count": int(devices),
            "pending_approval_count": int(approvals),
            "audit_status": "ok",
        }

    def user_count(self) -> int:
        self.initialize()
        with self.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    def create_user(
        self,
        *,
        display_name: str,
        role: str,
        household_member: bool = True,
        public_id: str | None = None,
    ) -> IdentityUserResponse:
        self.initialize()
        cleaned_name = " ".join(display_name.split())
        if not cleaned_name:
            raise IdentityValidationError("Display name is required.")
        if role not in ROLE_PERMISSIONS:
            raise IdentityValidationError("Unknown identity role.")

        identifier = public_id or str(uuid4())
        timestamp = _now()
        try:
            with self.connect() as connection:
                connection.execute(
                    """INSERT INTO users(
                           public_id, display_name, role, status, household_member,
                           created_at, updated_at
                       ) VALUES (?, ?, ?, 'active', ?, ?, ?)""",
                    (
                        identifier,
                        cleaned_name,
                        role,
                        int(household_member),
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    """INSERT OR IGNORE INTO personalization_profiles(
                           user_id, preferred_display_name, visibility_json,
                           created_at, updated_at
                       ) VALUES(
                           (SELECT id FROM users WHERE public_id = ?), ?, ?, ?, ?
                       )""",
                    (
                        identifier,
                        cleaned_name,
                        json.dumps(default_profile_visibility(), separators=(",", ":")),
                        timestamp,
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise IdentityConflictError("Public user identity already exists.") from exc
        return self.get_user(identifier)

    def list_users(self) -> list[IdentityUserResponse]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT public_id, display_name, role, status, household_member,
                          created_at, updated_at, disabled_at
                   FROM users ORDER BY created_at"""
            ).fetchall()
        return [_user_response(row) for row in rows]

    def get_user(self, public_id: str) -> IdentityUserResponse:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                """SELECT public_id, display_name, role, status, household_member,
                          created_at, updated_at, disabled_at
                   FROM users WHERE public_id = ?""",
                (public_id,),
            ).fetchone()
        if row is None:
            raise IdentityNotFoundError("User was not found.")
        return _user_response(row)

    def update_user(
        self,
        public_id: str,
        *,
        display_name: str | None = None,
        role: str | None = None,
        household_member: bool | None = None,
    ) -> IdentityUserResponse:
        current = self.get_user(public_id)
        next_role = role or current.role
        if next_role not in ROLE_PERMISSIONS:
            raise IdentityValidationError("Unknown identity role.")
        if current.role == "owner" and next_role != "owner":
            self._require_another_active_owner(public_id)

        next_name = current.display_name
        if display_name is not None:
            next_name = " ".join(display_name.split())
            if not next_name:
                raise IdentityValidationError("Display name is required.")

        with self.connect() as connection:
            connection.execute(
                """UPDATE users
                   SET display_name = ?, role = ?, household_member = ?, updated_at = ?
                   WHERE public_id = ?""",
                (
                    next_name,
                    next_role,
                    int(
                        current.household_member
                        if household_member is None
                        else household_member
                    ),
                    _now(),
                    public_id,
                ),
            )
        return self.get_user(public_id)

    def disable_user(self, public_id: str) -> IdentityUserResponse:
        current = self.get_user(public_id)
        if current.status == "disabled":
            return current
        if current.role == "owner":
            self._require_another_active_owner(public_id)

        timestamp = _now()
        with self.connect() as connection:
            connection.execute(
                """UPDATE users SET status = 'disabled', disabled_at = ?, updated_at = ?
                   WHERE public_id = ?""",
                (timestamp, timestamp, public_id),
            )
            connection.execute(
                """UPDATE trusted_devices SET status = 'revoked', revoked_at = ?
                   WHERE user_id = (SELECT id FROM users WHERE public_id = ?)
                     AND status != 'revoked'""",
                (timestamp, public_id),
            )
        return self.get_user(public_id)

    def set_permission_override(
        self,
        *,
        user_public_id: str,
        permission: str,
        effect: str,
        actor_user_id: str | None,
    ) -> PermissionOverrideResponse:
        if not is_registered_permission(permission):
            raise IdentityValidationError("Unknown permission key.")
        if effect not in {"grant", "deny"}:
            raise IdentityValidationError("Permission effect must be grant or deny.")
        if actor_user_id == user_public_id and effect == "grant":
            raise IdentityConflictError("Self-escalation is not allowed.")

        self.get_user(user_public_id)
        timestamp = _now()
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO permission_overrides(
                       user_id, permission, effect, created_by_user_id,
                       created_at, updated_at
                   ) VALUES(
                       (SELECT id FROM users WHERE public_id = ?), ?, ?,
                       (SELECT id FROM users WHERE public_id = ?), ?, ?
                   )
                   ON CONFLICT(user_id, permission) DO UPDATE SET
                       effect = excluded.effect,
                       created_by_user_id = excluded.created_by_user_id,
                       updated_at = excluded.updated_at""",
                (
                    user_public_id,
                    permission,
                    effect,
                    actor_user_id,
                    timestamp,
                    timestamp,
                ),
            )
            row = connection.execute(
                """SELECT u.public_id AS user_public_id, po.permission, po.effect,
                          po.created_at, po.updated_at
                   FROM permission_overrides po
                   JOIN users u ON u.id = po.user_id
                   WHERE u.public_id = ? AND po.permission = ?""",
                (user_public_id, permission),
            ).fetchone()
        return _override_response(row)

    def permission_overrides(self, user_public_id: str) -> dict[str, str]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT po.permission, po.effect
                   FROM permission_overrides po
                   JOIN users u ON u.id = po.user_id
                   WHERE u.public_id = ?""",
                (user_public_id,),
            ).fetchall()
        return {str(row["permission"]): str(row["effect"]) for row in rows}

    def enroll_device(
        self,
        *,
        user_public_id: str,
        display_name: str,
        device_type: str,
        trust_level: str,
        metadata: dict[str, Any] | None = None,
    ) -> TrustedDeviceEnrollmentResponse:
        user = self.get_user(user_public_id)
        if user.status != "active":
            raise IdentityConflictError("Cannot enroll a device for a disabled user.")
        if device_type not in {
            "mirror",
            "phone",
            "desktop",
            "tablet",
            "vehicle",
            "wearable",
            "room_node",
            "other",
        }:
            raise IdentityValidationError("Unknown device type.")
        if trust_level not in {"limited", "trusted", "privileged"}:
            raise IdentityValidationError("Unknown device trust level.")
        if settings.identity_device_token_bytes < 32:
            raise IdentityValidationError("Device tokens must use at least 32 bytes.")

        public_id = str(uuid4())
        token_prefix = f"mrg_{public_id.replace('-', '')[:12]}"
        secret = secrets.token_urlsafe(settings.identity_device_token_bytes)
        token = f"{token_prefix}_{secret}"
        token_hash = _hash_token(token)
        timestamp = _now()
        safe_metadata = _redact_metadata(metadata or {})

        with self.connect() as connection:
            connection.execute(
                """INSERT INTO trusted_devices(
                       public_id, user_id, display_name, device_type,
                       token_prefix, token_hash, trust_level, status,
                       metadata_json, created_at
                   ) VALUES(
                       ?, (SELECT id FROM users WHERE public_id = ?), ?, ?, ?, ?, ?,
                       'active', ?, ?
                   )""",
                (
                    public_id,
                    user_public_id,
                    " ".join(display_name.split()),
                    device_type,
                    token_prefix,
                    token_hash,
                    trust_level,
                    json.dumps(safe_metadata, separators=(",", ":")),
                    timestamp,
                ),
            )

        return TrustedDeviceEnrollmentResponse(
            device=self.get_device(public_id), token=token
        )

    def list_devices(self) -> list[TrustedDeviceResponse]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                self._device_select() + " ORDER BY d.created_at"
            ).fetchall()
        return [_device_response(row) for row in rows]

    def get_device(self, public_id: str) -> TrustedDeviceResponse:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                self._device_select() + " WHERE d.public_id = ?", (public_id,)
            ).fetchone()
        if row is None:
            raise IdentityNotFoundError("Trusted device was not found.")
        return _device_response(row)

    def revoke_device(self, public_id: str) -> TrustedDeviceResponse:
        self.get_device(public_id)
        timestamp = _now()
        with self.connect() as connection:
            connection.execute(
                """UPDATE trusted_devices
                   SET status = 'revoked', revoked_at = ?
                   WHERE public_id = ?""",
                (timestamp, public_id),
            )
        return self.get_device(public_id)

    def authenticate_device_token(
        self, token: str
    ) -> tuple[IdentityUserResponse, TrustedDeviceResponse] | None:
        self.initialize()
        prefix = _token_prefix(token)
        if prefix is None:
            return None

        with self.connect() as connection:
            row = connection.execute(
                """SELECT d.public_id, d.token_hash
                   FROM trusted_devices d
                   JOIN users u ON u.id = d.user_id
                   WHERE d.token_prefix = ? AND d.status = 'active'
                     AND u.status = 'active'""",
                (prefix,),
            ).fetchone()
        if row is None or not hmac.compare_digest(
            row["token_hash"], _hash_token(token)
        ):
            return None

        timestamp = _now()
        with self.connect() as connection:
            connection.execute(
                "UPDATE trusted_devices SET last_seen_at = ? WHERE public_id = ?",
                (timestamp, row["public_id"]),
            )
            user_row = connection.execute(
                """SELECT u.public_id, u.display_name, u.role, u.status,
                          u.household_member, u.created_at, u.updated_at, u.disabled_at
                   FROM users u JOIN trusted_devices d ON d.user_id = u.id
                   WHERE d.public_id = ?""",
                (row["public_id"],),
            ).fetchone()
        return _user_response(user_row), self.get_device(row["public_id"])

    def create_approval(
        self,
        *,
        requester: AuthenticatedPrincipal,
        action: str,
        resource_type: str,
        resource_id: str | None,
        risk_level: str,
        reason: str,
    ) -> ApprovalResponse:
        if not requester.authenticated or requester.user_id is None:
            raise IdentityValidationError("Approval requests require authentication.")
        public_id = str(uuid4())
        requested_at = datetime.now(UTC)
        expires_at = requested_at + timedelta(seconds=settings.approval_ttl_seconds)
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO approvals(
                       public_id, requester_user_id, requester_device_id, action,
                       resource_type, resource_id, risk_level, status, reason,
                       requested_at, expires_at, correlation_id
                   ) VALUES(
                       ?, (SELECT id FROM users WHERE public_id = ?),
                       (SELECT id FROM trusted_devices WHERE public_id = ?),
                       ?, ?, ?, ?, 'pending', ?, ?, ?, ?
                   )""",
                (
                    public_id,
                    requester.user_id,
                    requester.device_id,
                    action,
                    resource_type,
                    resource_id,
                    risk_level,
                    reason,
                    requested_at.isoformat(),
                    expires_at.isoformat(),
                    requester.correlation_id,
                ),
            )
        return self.get_approval(public_id)

    def list_approvals(self, status: str | None = None) -> list[ApprovalResponse]:
        self.initialize()
        self.expire_approvals()
        query = self._approval_select()
        params: tuple[Any, ...] = ()
        if status:
            query += " WHERE a.status = ?"
            params = (status,)
        query += " ORDER BY a.requested_at DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_approval_response(row) for row in rows]

    def get_approval(self, public_id: str) -> ApprovalResponse:
        self.initialize()
        self.expire_approvals()
        with self.connect() as connection:
            row = connection.execute(
                self._approval_select() + " WHERE a.public_id = ?", (public_id,)
            ).fetchone()
        if row is None:
            raise IdentityNotFoundError("Approval request was not found.")
        return _approval_response(row)

    def decide_approval(
        self,
        public_id: str,
        *,
        status: str,
        decider_user_id: str,
        reason: str,
    ) -> ApprovalResponse:
        approval = self.get_approval(public_id)
        if approval.status != "pending":
            raise IdentityConflictError("Only pending approvals can be decided.")
        if status not in {"approved", "denied"}:
            raise IdentityValidationError(
                "Approval decision must be approved or denied."
            )
        with self.connect() as connection:
            connection.execute(
                """UPDATE approvals
                   SET status = ?, decided_at = ?,
                       decided_by_user_id = (SELECT id FROM users WHERE public_id = ?),
                       decision_reason = ?
                   WHERE public_id = ? AND status = 'pending'""",
                (status, _now(), decider_user_id, reason, public_id),
            )
        return self.get_approval(public_id)

    def cancel_approval(
        self, public_id: str, *, requester_user_id: str, reason: str
    ) -> ApprovalResponse:
        approval = self.get_approval(public_id)
        if approval.requester_user_id != requester_user_id:
            raise IdentityConflictError("Only the requester can cancel this approval.")
        if approval.status != "pending":
            raise IdentityConflictError("Only pending approvals can be cancelled.")
        with self.connect() as connection:
            connection.execute(
                """UPDATE approvals
                   SET status = 'cancelled', decided_at = ?, decision_reason = ?
                   WHERE public_id = ?""",
                (_now(), reason, public_id),
            )
        return self.get_approval(public_id)

    def expire_approvals(self) -> int:
        self.initialize()
        with self.connect() as connection:
            cursor = connection.execute(
                """UPDATE approvals SET status = 'expired', decided_at = ?
                   WHERE status = 'pending' AND expires_at <= ?""",
                (_now(), _now()),
            )
        return cursor.rowcount

    def append_audit_event(
        self,
        *,
        event_type: str,
        principal: AuthenticatedPrincipal | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        authorization_decision: str | None = None,
        risk_level: str | None = None,
        reason: str | None = None,
        result: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEventResponse:
        self.initialize()
        public_id = str(uuid4())
        safe_metadata = _redact_metadata(metadata or {})
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO audit_events(
                       public_id, timestamp, event_type, actor_user_public_id,
                       actor_role, device_public_id, authentication_method,
                       action, resource_type, resource_id, authorization_decision,
                       risk_level, reason, result, correlation_id, metadata_json
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    public_id,
                    _now(),
                    event_type,
                    principal.user_id if principal else None,
                    principal.role if principal else None,
                    principal.device_id if principal else None,
                    principal.authentication_method if principal else None,
                    action,
                    resource_type,
                    resource_id,
                    authorization_decision,
                    risk_level,
                    _safe_text(reason),
                    result,
                    correlation_id or (principal.correlation_id if principal else None),
                    json.dumps(safe_metadata, separators=(",", ":")),
                ),
            )
            row = connection.execute(
                self._audit_select() + " WHERE public_id = ?", (public_id,)
            ).fetchone()
        return _audit_response(row)

    def list_audit_events(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        event_type: str | None = None,
        user_id: str | None = None,
        decision: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[AuditEventResponse], int]:
        self.initialize()
        conditions: list[str] = []
        params: list[Any] = []
        for column, value in (
            ("event_type", event_type),
            ("actor_user_public_id", user_id),
            ("authorization_decision", decision),
        ):
            if value:
                conditions.append(f"{column} = ?")
                params.append(value)
        if date_from:
            conditions.append("timestamp >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("timestamp <= ?")
            params.append(date_to)
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        with self.connect() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM audit_events{where}", tuple(params)
                ).fetchone()[0]
            )
            rows = connection.execute(
                self._audit_select()
                + where
                + " ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (*params, max(1, min(limit, 200)), max(0, offset)),
            ).fetchall()
        return [_audit_response(row) for row in rows], total

    def raw_device_secret_columns(self, public_id: str) -> tuple[str, str]:
        """Internal test/maintenance helper; never expose through an API."""

        with self.connect() as connection:
            row = connection.execute(
                """SELECT token_prefix, token_hash FROM trusted_devices
                   WHERE public_id = ?""",
                (public_id,),
            ).fetchone()
        if row is None:
            raise IdentityNotFoundError("Trusted device was not found.")
        return str(row["token_prefix"]), str(row["token_hash"])

    def _require_another_active_owner(self, excluded_public_id: str) -> None:
        with self.connect() as connection:
            count = int(
                connection.execute(
                    """SELECT COUNT(*) FROM users
                       WHERE role = 'owner' AND status = 'active' AND public_id != ?""",
                    (excluded_public_id,),
                ).fetchone()[0]
            )
        if count == 0:
            raise IdentityConflictError("The final active owner cannot be changed.")

    @staticmethod
    def _device_select() -> str:
        return """SELECT d.public_id, u.public_id AS user_public_id,
                         d.display_name, d.device_type, d.trust_level, d.status,
                         d.metadata_json, d.created_at, d.last_seen_at, d.revoked_at
                  FROM trusted_devices d JOIN users u ON u.id = d.user_id"""

    @staticmethod
    def _approval_select() -> str:
        return """SELECT a.public_id, requester.public_id AS requester_public_id,
                         device.public_id AS requester_device_public_id,
                         a.action, a.resource_type, a.resource_id, a.risk_level,
                         a.status, a.reason, a.requested_at, a.expires_at,
                         a.decided_at, decider.public_id AS decider_public_id,
                         a.decision_reason, a.correlation_id
                  FROM approvals a
                  JOIN users requester ON requester.id = a.requester_user_id
                  LEFT JOIN trusted_devices device ON device.id = a.requester_device_id
                  LEFT JOIN users decider ON decider.id = a.decided_by_user_id"""

    @staticmethod
    def _audit_select() -> str:
        return """SELECT public_id, timestamp, event_type, actor_user_public_id,
                         actor_role, device_public_id, authentication_method,
                         action, resource_type, resource_id, authorization_decision,
                         risk_level, reason, result, correlation_id, metadata_json
                  FROM audit_events"""


def _user_response(row: sqlite3.Row) -> IdentityUserResponse:
    return IdentityUserResponse(
        public_id=row["public_id"],
        display_name=row["display_name"],
        role=row["role"],
        status=row["status"],
        household_member=bool(row["household_member"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        disabled_at=row["disabled_at"],
    )


def _override_response(row: sqlite3.Row) -> PermissionOverrideResponse:
    return PermissionOverrideResponse(
        user_id=row["user_public_id"],
        permission=row["permission"],
        effect=row["effect"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _device_response(row: sqlite3.Row) -> TrustedDeviceResponse:
    return TrustedDeviceResponse(
        public_id=row["public_id"],
        user_id=row["user_public_id"],
        display_name=row["display_name"],
        device_type=row["device_type"],
        trust_level=row["trust_level"],
        status=row["status"],
        created_at=row["created_at"],
        last_seen_at=row["last_seen_at"],
        revoked_at=row["revoked_at"],
        metadata=json.loads(row["metadata_json"] or "{}"),
    )


def _approval_response(row: sqlite3.Row) -> ApprovalResponse:
    return ApprovalResponse(
        public_id=row["public_id"],
        requester_user_id=row["requester_public_id"],
        requester_device_id=row["requester_device_public_id"],
        action=row["action"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        risk_level=row["risk_level"],
        status=row["status"],
        reason=row["reason"],
        requested_at=row["requested_at"],
        expires_at=row["expires_at"],
        decided_at=row["decided_at"],
        decided_by_user_id=row["decider_public_id"],
        decision_reason=row["decision_reason"],
        correlation_id=row["correlation_id"],
    )


def _audit_response(row: sqlite3.Row) -> AuditEventResponse:
    return AuditEventResponse(
        public_id=row["public_id"],
        timestamp=row["timestamp"],
        event_type=row["event_type"],
        actor_user_id=row["actor_user_public_id"],
        actor_role=row["actor_role"],
        device_id=row["device_public_id"],
        authentication_method=row["authentication_method"],
        action=row["action"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        authorization_decision=row["authorization_decision"],
        risk_level=row["risk_level"],
        reason=row["reason"],
        result=row["result"],
        correlation_id=row["correlation_id"],
        metadata=json.loads(row["metadata_json"] or "{}"),
    )


def _token_prefix(token: str) -> str | None:
    parts = token.split("_", 2)
    if len(parts) != 3 or parts[0] != "mrg" or not parts[1] or not parts[2]:
        return None
    return f"mrg_{parts[1]}"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _redact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        lowered = str(key).casefold()
        if any(term in lowered for term in _REDACTED_METADATA_KEYS):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)[:80]] = value[:500] if isinstance(value, str) else value
    return safe


def _safe_text(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.split())[:500]


def _now() -> str:
    return datetime.now(UTC).isoformat()


identity_store = IdentityStore()
