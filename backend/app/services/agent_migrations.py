"""Schema migration for persistent bounded agent runs."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

AGENT_SCHEMA_VERSION = 3


def migrate_agent_schema(connection: sqlite3.Connection) -> None:
    """Add Phase 40 tables without changing existing identity data."""

    current = connection.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()[0]
    if int(current) >= AGENT_SCHEMA_VERSION:
        return

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            owner_user_id INTEGER NOT NULL REFERENCES users(id),
            created_by_device_id INTEGER REFERENCES trusted_devices(id),
            agent_type TEXT NOT NULL,
            goal TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            risk_level TEXT NOT NULL DEFAULT 'read_only',
            current_step INTEGER NOT NULL DEFAULT 0,
            total_steps INTEGER NOT NULL DEFAULT 0,
            max_steps INTEGER NOT NULL,
            provider TEXT,
            model TEXT,
            assumptions_json TEXT NOT NULL DEFAULT '[]',
            expected_outcome TEXT,
            stop_conditions_json TEXT NOT NULL DEFAULT '[]',
            clarification_prompt TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            paused_at TEXT,
            cancelled_at TEXT,
            expires_at TEXT NOT NULL,
            final_result TEXT,
            error_summary TEXT,
            correlation_id TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            run_id INTEGER NOT NULL REFERENCES agent_runs(id),
            step_number INTEGER NOT NULL,
            description TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'proposed',
            risk_level TEXT NOT NULL,
            approval_required INTEGER NOT NULL DEFAULT 0,
            approval_id INTEGER REFERENCES approvals(id),
            started_at TEXT,
            completed_at TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            output_summary TEXT,
            error_summary TEXT,
            UNIQUE(run_id, step_number)
        );

        CREATE TABLE IF NOT EXISTS agent_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            run_id INTEGER NOT NULL REFERENCES agent_runs(id),
            step_id INTEGER REFERENCES agent_steps(id),
            sequence INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, sequence)
        );

        CREATE INDEX IF NOT EXISTS idx_agent_runs_owner_status
            ON agent_runs(owner_user_id, status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_agent_runs_active_expiry
            ON agent_runs(status, expires_at);
        CREATE INDEX IF NOT EXISTS idx_agent_steps_run_status
            ON agent_steps(run_id, status, step_number);
        CREATE INDEX IF NOT EXISTS idx_agent_steps_approval
            ON agent_steps(approval_id);
        CREATE INDEX IF NOT EXISTS idx_agent_events_run_sequence
            ON agent_events(run_id, sequence);
        """
    )
    connection.execute(
        "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
        (AGENT_SCHEMA_VERSION, datetime.now(UTC).isoformat()),
    )
