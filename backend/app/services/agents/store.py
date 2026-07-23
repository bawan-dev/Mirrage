"""Persistent storage for bounded, user-owned agent runs."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from backend.app.services.agents.models import (
    AgentApprovalQueueItem,
    AgentEventResponse,
    AgentRunCreateRequest,
    AgentRunDetailResponse,
    AgentRunResponse,
    AgentStepResponse,
    PlannerResult,
    ValidatedAgentStep,
)
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.identity_store import identity_store
from backend.app.settings import settings

_TERMINAL_RUN_STATUSES = frozenset({"completed", "failed", "cancelled", "expired"})
_ACTIVE_RUN_STATUSES = frozenset(
    {
        "draft",
        "planning",
        "awaiting_approval",
        "awaiting_user_input",
        "ready",
        "running",
        "paused",
    }
)


class AgentStoreError(RuntimeError):
    """Base persistent agent error."""


class AgentNotFoundError(AgentStoreError):
    """Raised when a run or step is absent or not visible to the caller."""


class AgentConflictError(AgentStoreError):
    """Raised when a requested state transition is invalid."""


class AgentValidationError(AgentStoreError):
    """Raised when agent state violates a bounded-execution invariant."""


class AgentStore:
    def initialize(self) -> None:
        identity_store.initialize()

    def create_run(
        self,
        principal: AuthenticatedPrincipal,
        request: AgentRunCreateRequest,
    ) -> AgentRunResponse:
        if not principal.user_id:
            raise AgentValidationError("An authenticated user is required.")
        max_steps = request.max_steps or settings.agent_max_steps
        if max_steps > settings.agent_max_steps:
            raise AgentValidationError(
                f"Runs are limited to {settings.agent_max_steps} steps."
            )

        public_id = str(uuid4())
        created_at = _now()
        expires_at = (
            datetime.now(UTC)
            + timedelta(seconds=max(3600, settings.agent_max_runtime_seconds * 12))
        ).isoformat()
        self.initialize()
        with identity_store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._expire_runs_in_connection(connection)
            placeholders = ",".join("?" for _ in _ACTIVE_RUN_STATUSES)
            active_statuses = tuple(_ACTIVE_RUN_STATUSES)
            global_count = int(
                connection.execute(
                    f"""SELECT COUNT(*) FROM agent_runs
                        WHERE status IN ({placeholders})""",
                    active_statuses,
                ).fetchone()[0]
            )
            owner_count = int(
                connection.execute(
                    f"""SELECT COUNT(*) FROM agent_runs
                        WHERE status IN ({placeholders})
                          AND owner_user_id = (
                              SELECT id FROM users WHERE public_id = ?
                          )""",
                    (*active_statuses, principal.user_id),
                ).fetchone()[0]
            )
            if global_count >= settings.agent_max_concurrent_runs:
                raise AgentConflictError(
                    "The installation agent-run limit was reached."
                )
            if owner_count >= settings.agent_max_concurrent_runs:
                raise AgentConflictError("The active agent-run limit has been reached.")
            connection.execute(
                """INSERT INTO agent_runs(
                       public_id, owner_user_id, created_by_device_id, agent_type,
                       goal, status, risk_level, max_steps, created_at, expires_at,
                       correlation_id
                   ) VALUES(
                       ?, (SELECT id FROM users WHERE public_id = ?),
                       (SELECT id FROM trusted_devices WHERE public_id = ?),
                       ?, ?, 'draft', 'read_only', ?, ?, ?, ?
                   )""",
                (
                    public_id,
                    principal.user_id,
                    principal.device_id,
                    request.agent_type,
                    request.goal.strip(),
                    max_steps,
                    created_at,
                    expires_at,
                    principal.correlation_id,
                ),
            )
        return self.get_run(public_id, principal.user_id)

    def list_runs(self, owner_user_id: str) -> list[AgentRunResponse]:
        self.initialize()
        self._expire_runs()
        with identity_store.connect() as connection:
            rows = connection.execute(
                self._run_select()
                + """ WHERE owner.public_id = ?
                      ORDER BY run.created_at DESC""",
                (owner_user_id,),
            ).fetchall()
        return [_run_response(row) for row in rows]

    def get_run(self, run_id: str, owner_user_id: str) -> AgentRunResponse:
        self.initialize()
        self._expire_runs()
        with identity_store.connect() as connection:
            row = connection.execute(
                self._run_select() + " WHERE run.public_id = ? AND owner.public_id = ?",
                (run_id, owner_user_id),
            ).fetchone()
        if row is None:
            raise AgentNotFoundError("Agent run was not found.")
        return _run_response(row)

    def get_run_for_approver(self, run_id: str) -> AgentRunResponse:
        """Load a run for a separately authorized approval decision."""

        self.initialize()
        self._expire_runs()
        with identity_store.connect() as connection:
            row = connection.execute(
                self._run_select() + " WHERE run.public_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise AgentNotFoundError("Agent run was not found.")
        return _run_response(row)

    def get_detail(self, run_id: str, owner_user_id: str) -> AgentRunDetailResponse:
        return AgentRunDetailResponse(
            run=self.get_run(run_id, owner_user_id),
            steps=self.list_steps(run_id, owner_user_id),
        )

    def claim_run_for_planning(
        self, run_id: str, owner_user_id: str
    ) -> AgentRunResponse:
        self.get_run(run_id, owner_user_id)
        with identity_store.connect() as connection:
            cursor = connection.execute(
                """UPDATE agent_runs SET status = 'planning'
                   WHERE public_id = ?
                     AND owner_user_id = (
                         SELECT id FROM users WHERE public_id = ?
                     )
                     AND status = 'draft'""",
                (run_id, owner_user_id),
            )
        if cursor.rowcount != 1:
            raise AgentConflictError("Only a draft run can enter planning.")
        return self.get_run(run_id, owner_user_id)

    def claim_run_for_execution(
        self, run_id: str, owner_user_id: str
    ) -> AgentRunResponse:
        self.get_run(run_id, owner_user_id)
        with identity_store.connect() as connection:
            cursor = connection.execute(
                """UPDATE agent_runs
                   SET status = 'running', started_at = COALESCE(started_at, ?),
                       paused_at = NULL
                   WHERE public_id = ?
                     AND owner_user_id = (
                         SELECT id FROM users WHERE public_id = ?
                     )
                     AND status = 'ready'""",
                (_now(), run_id, owner_user_id),
            )
        if cursor.rowcount != 1:
            raise AgentConflictError("This run was not ready to start.")
        return self.get_run(run_id, owner_user_id)

    def save_plan(
        self,
        run_id: str,
        owner_user_id: str,
        plan: PlannerResult,
        steps: list[ValidatedAgentStep],
    ) -> AgentRunDetailResponse:
        run = self.get_run(run_id, owner_user_id)
        if run.status not in {"draft", "planning", "awaiting_user_input"}:
            raise AgentConflictError("Only an unstarted run can be planned.")
        if len(steps) > run.max_steps:
            raise AgentValidationError("The proposed plan exceeds the run step limit.")

        status = "ready"
        if plan.clarification_prompt:
            status = "awaiting_user_input"
        elif any(step.approval_required for step in steps):
            status = "awaiting_approval"
        risk = _maximum_risk(step.risk_level for step in steps)
        with identity_store.connect() as connection:
            internal_run_id = self._internal_run_id(connection, run_id, owner_user_id)
            existing = int(
                connection.execute(
                    "SELECT COUNT(*) FROM agent_steps WHERE run_id = ?",
                    (internal_run_id,),
                ).fetchone()[0]
            )
            if existing:
                raise AgentConflictError("This run already has a persisted plan.")
            for number, validated in enumerate(steps, start=1):
                proposal = validated.proposal
                connection.execute(
                    """INSERT INTO agent_steps(
                           public_id, run_id, step_number, description, tool_name,
                           arguments_json, status, risk_level, approval_required
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid4()),
                        internal_run_id,
                        number,
                        proposal.description,
                        proposal.tool_name,
                        json.dumps(proposal.arguments, separators=(",", ":")),
                        (
                            "awaiting_approval"
                            if validated.approval_required
                            else "ready"
                        ),
                        validated.risk_level,
                        int(validated.approval_required),
                    ),
                )
            connection.execute(
                """UPDATE agent_runs
                   SET status = ?, risk_level = ?, total_steps = ?,
                       provider = ?, model = ?, assumptions_json = ?,
                       expected_outcome = ?, stop_conditions_json = ?,
                       clarification_prompt = ?
                   WHERE id = ?""",
                (
                    status,
                    risk,
                    len(steps),
                    plan.provider,
                    plan.model,
                    json.dumps(plan.assumptions, separators=(",", ":")),
                    plan.expected_outcome,
                    json.dumps(plan.stop_conditions, separators=(",", ":")),
                    plan.clarification_prompt,
                    internal_run_id,
                ),
            )
        return self.get_detail(run_id, owner_user_id)

    def list_steps(self, run_id: str, owner_user_id: str) -> list[AgentStepResponse]:
        self.get_run(run_id, owner_user_id)
        identity_store.expire_approvals()
        with identity_store.connect() as connection:
            rows = connection.execute(
                self._step_select()
                + """ WHERE run.public_id = ?
                      ORDER BY step.step_number""",
                (run_id,),
            ).fetchall()
        return [_step_response(row) for row in rows]

    def get_step(self, step_id: str) -> AgentStepResponse:
        self.initialize()
        with identity_store.connect() as connection:
            row = connection.execute(
                self._step_select() + " WHERE step.public_id = ?",
                (step_id,),
            ).fetchone()
        if row is None:
            raise AgentNotFoundError("Agent step was not found.")
        return _step_response(row)

    def attach_approval(self, step_id: str, approval_id: str) -> None:
        with identity_store.connect() as connection:
            cursor = connection.execute(
                """UPDATE agent_steps
                   SET approval_id = (
                       SELECT id FROM approvals WHERE public_id = ?
                   ), status = 'awaiting_approval'
                   WHERE public_id = ? AND approval_required = 1""",
                (approval_id, step_id),
            )
        if cursor.rowcount != 1:
            raise AgentNotFoundError("Approval step was not found.")

    def update_run_status(
        self,
        run_id: str,
        owner_user_id: str,
        status: str,
        *,
        final_result: str | None = None,
        error_summary: str | None = None,
        current_step: int | None = None,
        expected_statuses: set[str] | frozenset[str] | None = None,
    ) -> AgentRunResponse:
        self.get_run(run_id, owner_user_id)
        timestamp_fields = {
            "running": ("started_at", _now()),
            "paused": ("paused_at", _now()),
            "completed": ("completed_at", _now()),
            "failed": ("completed_at", _now()),
            "cancelled": ("cancelled_at", _now()),
        }
        assignments = ["status = ?"]
        values: list[Any] = [status]
        if status in timestamp_fields:
            field, value = timestamp_fields[status]
            assignments.append(f"{field} = COALESCE({field}, ?)")
            values.append(value)
        if status == "running":
            assignments.append("paused_at = NULL")
        if final_result is not None:
            assignments.append("final_result = ?")
            values.append(_safe_text(final_result, 4000))
        if error_summary is not None:
            assignments.append("error_summary = ?")
            values.append(_safe_text(error_summary, 500))
        if current_step is not None:
            assignments.append("current_step = ?")
            values.append(current_step)
        values.extend([run_id, owner_user_id])
        expected_clause = ""
        if expected_statuses:
            placeholders = ",".join("?" for _ in expected_statuses)
            expected_clause = f" AND status IN ({placeholders})"
            values.extend(sorted(expected_statuses))
        with identity_store.connect() as connection:
            cursor = connection.execute(
                f"""UPDATE agent_runs SET {", ".join(assignments)}
                    WHERE public_id = ? AND owner_user_id = (
                        SELECT id FROM users WHERE public_id = ?
                    ){expected_clause}""",
                tuple(values),
            )
        if cursor.rowcount != 1:
            raise AgentConflictError("The run changed before this transition.")
        return self.get_run(run_id, owner_user_id)

    def update_step(
        self,
        step_id: str,
        status: str,
        *,
        output_summary: str | None = None,
        error_summary: str | None = None,
        retry_count: int | None = None,
        expected_statuses: set[str] | frozenset[str] | None = None,
    ) -> AgentStepResponse:
        assignments = ["status = ?"]
        values: list[Any] = [status]
        if status == "running":
            assignments.append("started_at = COALESCE(started_at, ?)")
            values.append(_now())
        if status in {"completed", "failed", "cancelled", "skipped"}:
            assignments.append("completed_at = ?")
            values.append(_now())
        if output_summary is not None:
            assignments.append("output_summary = ?")
            values.append(_safe_text(output_summary, 500))
        if error_summary is not None:
            assignments.append("error_summary = ?")
            values.append(_safe_text(error_summary, 500))
        if retry_count is not None:
            assignments.append("retry_count = ?")
            values.append(retry_count)
        values.append(step_id)
        expected_clause = ""
        if expected_statuses:
            placeholders = ",".join("?" for _ in expected_statuses)
            expected_clause = f" AND status IN ({placeholders})"
            values.extend(sorted(expected_statuses))
        with identity_store.connect() as connection:
            cursor = connection.execute(
                f"""UPDATE agent_steps SET {", ".join(assignments)}
                    WHERE public_id = ?{expected_clause}""",
                tuple(values),
            )
        if cursor.rowcount != 1:
            if expected_statuses:
                raise AgentConflictError("The step changed before this transition.")
            raise AgentNotFoundError("Agent step was not found.")
        return self.get_step(step_id)

    def cancel_pending_steps(self, run_id: str) -> None:
        with identity_store.connect() as connection:
            connection.execute(
                """UPDATE agent_steps
                   SET status = 'cancelled', completed_at = ?
                   WHERE run_id = (
                       SELECT id FROM agent_runs WHERE public_id = ?
                   ) AND status IN (
                       'proposed', 'validated', 'awaiting_approval', 'ready'
                   )""",
                (_now(), run_id),
            )

    def append_event(
        self,
        run_id: str,
        event_type: str,
        message: str,
        *,
        step_id: str | None = None,
    ) -> AgentEventResponse:
        self.initialize()
        public_id = str(uuid4())
        with identity_store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            internal_run_id = self._internal_run_id(connection, run_id)
            internal_step_id = None
            if step_id:
                row = connection.execute(
                    """SELECT id FROM agent_steps
                       WHERE public_id = ? AND run_id = ?""",
                    (step_id, internal_run_id),
                ).fetchone()
                if row is None:
                    raise AgentNotFoundError("Agent step was not found.")
                internal_step_id = int(row["id"])
            sequence = int(
                connection.execute(
                    """SELECT COALESCE(MAX(sequence), 0) + 1
                       FROM agent_events WHERE run_id = ?""",
                    (internal_run_id,),
                ).fetchone()[0]
            )
            connection.execute(
                """INSERT INTO agent_events(
                       public_id, run_id, step_id, sequence, event_type,
                       message, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    public_id,
                    internal_run_id,
                    internal_step_id,
                    sequence,
                    event_type,
                    _safe_text(message, 500),
                    _now(),
                ),
            )
        return self.get_event(public_id)

    def get_event(self, event_id: str) -> AgentEventResponse:
        with identity_store.connect() as connection:
            row = connection.execute(
                self._event_select() + " WHERE event.public_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            raise AgentNotFoundError("Agent event was not found.")
        return _event_response(row)

    def list_events(
        self,
        run_id: str,
        owner_user_id: str,
        *,
        after_sequence: int = 0,
    ) -> list[AgentEventResponse]:
        self.get_run(run_id, owner_user_id)
        with identity_store.connect() as connection:
            rows = connection.execute(
                self._event_select()
                + """ WHERE run.public_id = ? AND event.sequence > ?
                      ORDER BY event.sequence""",
                (run_id, max(0, after_sequence)),
            ).fetchall()
        return [_event_response(row) for row in rows]

    def approval_queue(self) -> list[AgentApprovalQueueItem]:
        identity_store.expire_approvals()
        with identity_store.connect() as connection:
            rows = connection.execute(
                """SELECT approval.public_id AS approval_public_id,
                          run.public_id AS run_public_id,
                          step.public_id AS step_public_id,
                          owner.public_id AS owner_public_id,
                          run.agent_type, step.tool_name, step.description,
                          step.risk_level, approval.expires_at
                   FROM agent_steps step
                   JOIN agent_runs run ON run.id = step.run_id
                   JOIN users owner ON owner.id = run.owner_user_id
                    JOIN approvals approval ON approval.id = step.approval_id
                    WHERE step.status = 'awaiting_approval'
                      AND approval.status = 'pending'
                      AND run.status IN ('awaiting_approval', 'paused')
                    ORDER BY approval.requested_at""",
            ).fetchall()
        return [
            AgentApprovalQueueItem(
                approval_id=row["approval_public_id"],
                run_id=row["run_public_id"],
                step_id=row["step_public_id"],
                requesting_user_id=row["owner_public_id"],
                agent_type=row["agent_type"],
                tool_name=row["tool_name"],
                description=row["description"],
                risk_level=row["risk_level"],
                expires_at=row["expires_at"],
            )
            for row in rows
        ]

    def active_run_count(self, owner_user_id: str | None = None) -> int:
        self.initialize()
        placeholders = ",".join("?" for _ in _ACTIVE_RUN_STATUSES)
        query = f"SELECT COUNT(*) FROM agent_runs WHERE status IN ({placeholders})"
        params: list[Any] = list(_ACTIVE_RUN_STATUSES)
        if owner_user_id:
            query += " AND owner_user_id = (SELECT id FROM users WHERE public_id = ?)"
            params.append(owner_user_id)
        with identity_store.connect() as connection:
            return int(connection.execute(query, tuple(params)).fetchone()[0])

    def status_counts(self) -> dict[str, int]:
        self.initialize()
        self._expire_runs()
        with identity_store.connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM agent_runs GROUP BY status"
            ).fetchall()
        counts = {str(row["status"]): int(row["count"]) for row in rows}
        return {
            "active": sum(counts.get(status, 0) for status in _ACTIVE_RUN_STATUSES),
            "awaiting_approval": counts.get("awaiting_approval", 0),
            "failed": counts.get("failed", 0),
        }

    def _expire_runs(self) -> None:
        with identity_store.connect() as connection:
            self._expire_runs_in_connection(connection)

    @staticmethod
    def _expire_runs_in_connection(connection: sqlite3.Connection) -> None:
        now = _now()
        placeholders = ",".join("?" for _ in _TERMINAL_RUN_STATUSES)
        terminal_statuses = tuple(sorted(_TERMINAL_RUN_STATUSES))
        connection.execute(
            f"""UPDATE approvals SET status = 'expired', decided_at = ?
                WHERE status = 'pending' AND id IN (
                    SELECT step.approval_id
                    FROM agent_steps step
                    JOIN agent_runs run ON run.id = step.run_id
                    WHERE step.approval_id IS NOT NULL
                      AND run.status NOT IN ({placeholders})
                      AND run.expires_at <= ?
                )""",
            (now, *terminal_statuses, now),
        )
        connection.execute(
            f"""UPDATE agent_steps SET status = 'cancelled', completed_at = ?
                WHERE status NOT IN ('completed', 'failed', 'skipped', 'cancelled')
                  AND run_id IN (
                      SELECT id FROM agent_runs
                      WHERE status NOT IN ({placeholders})
                        AND expires_at <= ?
                  )""",
            (now, *terminal_statuses, now),
        )
        connection.execute(
            f"""UPDATE agent_runs SET status = 'expired', completed_at = ?
                WHERE status NOT IN ({placeholders})
                  AND expires_at <= ?""",
            (now, *terminal_statuses, now),
        )

    @staticmethod
    def _internal_run_id(
        connection: sqlite3.Connection,
        run_id: str,
        owner_user_id: str | None = None,
    ) -> int:
        query = "SELECT id FROM agent_runs WHERE public_id = ?"
        params: list[Any] = [run_id]
        if owner_user_id:
            query += " AND owner_user_id = (SELECT id FROM users WHERE public_id = ?)"
            params.append(owner_user_id)
        row = connection.execute(query, tuple(params)).fetchone()
        if row is None:
            raise AgentNotFoundError("Agent run was not found.")
        return int(row["id"])

    @staticmethod
    def _run_select() -> str:
        return """SELECT run.*, owner.public_id AS owner_public_id,
                         device.public_id AS device_public_id
                  FROM agent_runs run
                  JOIN users owner ON owner.id = run.owner_user_id
                  LEFT JOIN trusted_devices device
                    ON device.id = run.created_by_device_id"""

    @staticmethod
    def _step_select() -> str:
        return """SELECT step.*, run.public_id AS run_public_id,
                         approval.public_id AS approval_public_id,
                         approval.status AS approval_status
                  FROM agent_steps step
                  JOIN agent_runs run ON run.id = step.run_id
                  LEFT JOIN approvals approval ON approval.id = step.approval_id"""

    @staticmethod
    def _event_select() -> str:
        return """SELECT event.*, run.public_id AS run_public_id,
                         step.public_id AS step_public_id
                  FROM agent_events event
                  JOIN agent_runs run ON run.id = event.run_id
                  LEFT JOIN agent_steps step ON step.id = event.step_id"""


def _run_response(row: sqlite3.Row) -> AgentRunResponse:
    return AgentRunResponse(
        public_id=row["public_id"],
        owner_user_id=row["owner_public_id"],
        created_by_device_id=row["device_public_id"],
        agent_type=row["agent_type"],
        goal=row["goal"],
        status=row["status"],
        risk_level=row["risk_level"],
        current_step=int(row["current_step"]),
        total_steps=int(row["total_steps"]),
        max_steps=int(row["max_steps"]),
        provider=row["provider"],
        model=row["model"],
        assumptions=json.loads(row["assumptions_json"] or "[]"),
        expected_outcome=row["expected_outcome"],
        stop_conditions=json.loads(row["stop_conditions_json"] or "[]"),
        clarification_prompt=row["clarification_prompt"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        paused_at=row["paused_at"],
        cancelled_at=row["cancelled_at"],
        expires_at=row["expires_at"],
        final_result=row["final_result"],
        error_summary=row["error_summary"],
        correlation_id=row["correlation_id"],
    )


def _step_response(row: sqlite3.Row) -> AgentStepResponse:
    return AgentStepResponse(
        public_id=row["public_id"],
        run_id=row["run_public_id"],
        step_number=int(row["step_number"]),
        description=row["description"],
        tool_name=row["tool_name"],
        arguments=json.loads(row["arguments_json"] or "{}"),
        status=row["status"],
        risk_level=row["risk_level"],
        approval_required=bool(row["approval_required"]),
        approval_id=row["approval_public_id"],
        approval_status=row["approval_status"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        retry_count=int(row["retry_count"]),
        output_summary=row["output_summary"],
        error_summary=row["error_summary"],
    )


def _event_response(row: sqlite3.Row) -> AgentEventResponse:
    return AgentEventResponse(
        public_id=row["public_id"],
        run_id=row["run_public_id"],
        step_id=row["step_public_id"],
        sequence=int(row["sequence"]),
        event_type=row["event_type"],
        message=row["message"],
        created_at=row["created_at"],
    )


def _maximum_risk(levels: Any) -> str:
    order = {"read_only": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    return max(levels, default="read_only", key=lambda level: order[level])


def _safe_text(value: str, limit: int) -> str:
    return " ".join(value.split())[:limit]


def _now() -> str:
    return datetime.now(UTC).isoformat()


agent_store = AgentStore()
