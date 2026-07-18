"""Schema migrations for relationship and personalization data."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from backend.app.services.relationship_models import default_profile_visibility

RELATIONSHIP_SCHEMA_VERSION = 2


def migrate_relationship_schema(connection: sqlite3.Connection) -> None:
    """Apply the Phase 39 schema without changing Phase 38 records."""

    current = connection.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()[0]
    if int(current) >= RELATIONSHIP_SCHEMA_VERSION:
        return

    timestamp = datetime.now(UTC).isoformat()
    visibility = json.dumps(default_profile_visibility(), separators=(",", ":"))
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS personalization_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            preferred_display_name TEXT NOT NULL,
            preferred_language TEXT NOT NULL DEFAULT 'en-GB',
            response_tone TEXT NOT NULL DEFAULT 'neutral',
            response_length TEXT NOT NULL DEFAULT 'concise',
            greeting_style TEXT NOT NULL DEFAULT 'minimal',
            humour TEXT NOT NULL DEFAULT 'off',
            proactivity TEXT NOT NULL DEFAULT 'silent',
            quiet_hours_start TEXT,
            quiet_hours_end TEXT,
            time_zone TEXT NOT NULL DEFAULT 'Europe/London',
            spoken_announcements INTEGER NOT NULL DEFAULT 0,
            personalized_greeting INTEGER NOT NULL DEFAULT 0,
            cloud_personalization_opt_in INTEGER NOT NULL DEFAULT 0,
            visibility_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            user_a_id INTEGER NOT NULL REFERENCES users(id),
            user_b_id INTEGER NOT NULL REFERENCES users(id),
            proposed_by_user_id INTEGER NOT NULL REFERENCES users(id),
            proposed_to_user_id INTEGER NOT NULL REFERENCES users(id),
            relationship_type TEXT NOT NULL,
            custom_label TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            responded_at TEXT,
            archived_at TEXT,
            CHECK(user_a_id < user_b_id)
        );

        CREATE TABLE IF NOT EXISTS shared_context_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            owner_user_id INTEGER NOT NULL REFERENCES users(id),
            context_type TEXT NOT NULL,
            title TEXT NOT NULL,
            value TEXT NOT NULL,
            visibility TEXT NOT NULL DEFAULT 'private',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT
        );

        CREATE TABLE IF NOT EXISTS shared_context_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context_item_id INTEGER NOT NULL REFERENCES shared_context_items(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            UNIQUE(context_item_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS interaction_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            device_id INTEGER NOT NULL REFERENCES trusted_devices(id),
            token_prefix TEXT NOT NULL UNIQUE,
            token_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ended_at TEXT,
            last_seen_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_profiles_user
            ON personalization_profiles(user_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_users_status
            ON relationships(user_a_id, user_b_id, status);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_relationships_pending_active_unique
            ON relationships(user_a_id, user_b_id)
            WHERE status IN ('pending', 'active');
        CREATE INDEX IF NOT EXISTS idx_shared_context_owner_status
            ON shared_context_items(owner_user_id, status);
        CREATE INDEX IF NOT EXISTS idx_shared_context_visibility_status
            ON shared_context_items(visibility, status);
        CREATE INDEX IF NOT EXISTS idx_shared_context_access_user
            ON shared_context_access(user_id, context_item_id);
        CREATE INDEX IF NOT EXISTS idx_interaction_sessions_lookup
            ON interaction_sessions(token_prefix, status, expires_at);
        """
    )
    connection.execute(
        """INSERT OR IGNORE INTO personalization_profiles(
               user_id, preferred_display_name, preferred_language,
               response_tone, response_length, greeting_style, humour,
               proactivity, time_zone, spoken_announcements,
               personalized_greeting, cloud_personalization_opt_in,
               visibility_json, created_at, updated_at
           )
           SELECT id, display_name, 'en-GB', 'neutral', 'concise', 'minimal',
                  'off', 'silent', 'Europe/London', 0, 0, 0, ?, ?, ?
           FROM users""",
        (visibility, timestamp, timestamp),
    )
    connection.execute(
        "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
        (RELATIONSHIP_SCHEMA_VERSION, timestamp),
    )
