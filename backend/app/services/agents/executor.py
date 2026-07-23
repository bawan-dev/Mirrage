"""Bounded step executor for validated agent plans."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from ai.runtime import assistant_runtime
from backend.app.services.agents.events import agent_events
from backend.app.services.agents.policy import agent_policy
from backend.app.services.agents.registry import agent_tool_registry
from backend.app.services.agents.store import (
    AgentConflictError,
    AgentValidationError,
    agent_store,
)
from backend.app.services.agents.tools import execute_registered_tool
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.identity_store import identity_store
from backend.app.settings import settings

logger = logging.getLogger(__name__)


class AgentExecutor:
    def execute(
        self,
        run_id: str,
        principal: AuthenticatedPrincipal,
    ):
        if not settings.agents_enabled:
            raise AgentValidationError("Agent execution is disabled.")
        if not principal.user_id:
            raise AgentValidationError("An authenticated user is required.")
        run = agent_store.get_run(run_id, principal.user_id)
        steps = agent_store.list_steps(run_id, principal.user_id)
        if run.status == "awaiting_approval":
            invalid = next(
                (
                    step
                    for step in steps
                    if step.approval_required
                    and step.approval_status in {None, "cancelled", "denied", "expired"}
                ),
                None,
            )
            if invalid is not None:
                return self._reject_invalid_approval(
                    run_id, principal, invalid.public_id
                )
        if run.status != "ready":
            raise AgentConflictError("This run is not ready to start.")

        pending = [
            step
            for step in steps
            if step.approval_required and step.approval_status == "pending"
        ]
        if pending:
            agent_store.update_run_status(
                run_id,
                principal.user_id,
                "awaiting_approval",
                expected_statuses={"ready"},
            )
            agent_events.emit(
                run_id,
                "awaiting_approval",
                f"{len(pending)} step(s) are waiting for separate approval.",
            )
            return agent_store.get_detail(run_id, principal.user_id)

        run = agent_store.claim_run_for_execution(run_id, principal.user_id)
        agent_events.emit(run_id, "running", "Bounded execution started.")
        identity_store.append_audit_event(
            event_type="agent_execution_started",
            principal=principal,
            action="agents.start",
            resource_type="agent_run",
            resource_id=run_id,
            result="started",
        )
        started = time.monotonic()
        result_lines: list[str] = []

        for step in steps:
            current = agent_store.get_run(run_id, principal.user_id)
            if current.status in {"paused", "cancelled"}:
                return agent_store.get_detail(run_id, principal.user_id)
            if time.monotonic() - started > settings.agent_max_runtime_seconds:
                return self._fail(
                    run_id, principal, step.public_id, "Agent runtime limit reached."
                )
            if step.status in {"completed", "skipped", "cancelled"}:
                continue
            if step.approval_required:
                approval = (
                    identity_store.get_approval(step.approval_id)
                    if step.approval_id
                    else None
                )
                if (
                    approval is None
                    or approval.status != "approved"
                    or approval.decided_by_user_id == principal.user_id
                ):
                    return self._fail(
                        run_id,
                        principal,
                        step.public_id,
                        "Required separate approval is absent, expired, or invalid.",
                    )

            try:
                agent_policy.authorize_tool(principal, step.tool_name, audit=True)
                agent_tool_registry.validate_arguments(step.tool_name, step.arguments)
            except Exception as exc:
                return self._fail(
                    run_id,
                    principal,
                    step.public_id,
                    f"Execution policy denied the step: {exc}",
                )

            tool = agent_tool_registry.get(step.tool_name)
            try:
                agent_store.update_run_status(
                    run_id,
                    principal.user_id,
                    "running",
                    current_step=step.step_number,
                    expected_statuses={"running"},
                )
            except AgentConflictError:
                return agent_store.get_detail(run_id, principal.user_id)
            try:
                agent_store.update_step(
                    step.public_id,
                    "running",
                    expected_statuses={"ready"},
                )
            except AgentConflictError:
                return agent_store.get_detail(run_id, principal.user_id)
            latest = agent_store.get_run(run_id, principal.user_id)
            if latest.status == "paused":
                agent_store.update_step(
                    step.public_id,
                    "ready",
                    expected_statuses={"running"},
                )
                return agent_store.get_detail(run_id, principal.user_id)
            if latest.status == "cancelled":
                agent_store.update_step(
                    step.public_id,
                    "cancelled",
                    expected_statuses={"running"},
                )
                return agent_store.get_detail(run_id, principal.user_id)
            agent_events.emit(
                run_id,
                "running_step",
                f"Running step {step.step_number} of {run.total_steps}.",
                step_id=step.public_id,
            )
            identity_store.append_audit_event(
                event_type="agent_tool_execution",
                principal=principal,
                action=step.tool_name,
                resource_type="agent_step",
                resource_id=step.public_id,
                authorization_decision="allowed",
                risk_level=step.risk_level,
                result="started",
                metadata={"run_id": run_id, "step_number": step.step_number},
            )

            retries = min(tool.max_retries, settings.agent_max_retries)
            output = None
            error: Exception | None = None
            for attempt in range(retries + 1):
                try:
                    output = self._execute_with_timeout(
                        step.tool_name,
                        step.arguments,
                        principal,
                        run.goal,
                        tool.timeout_seconds,
                    )
                    error = None
                    if attempt:
                        agent_store.update_step(
                            step.public_id,
                            "running",
                            retry_count=attempt,
                            expected_statuses={"running"},
                        )
                    break
                except Exception as exc:
                    error = exc
                    if attempt >= retries or not tool.idempotent:
                        break
            if error is not None or output is None:
                return self._fail(
                    run_id,
                    principal,
                    step.public_id,
                    "Registered tool failed safely.",
                )
            if time.monotonic() - started > settings.agent_max_runtime_seconds:
                return self._fail(
                    run_id,
                    principal,
                    step.public_id,
                    "Agent runtime limit reached.",
                )

            try:
                agent_store.update_step(
                    step.public_id,
                    "completed",
                    output_summary=output.safe_summary,
                    expected_statuses={"running"},
                )
            except AgentConflictError:
                return agent_store.get_detail(run_id, principal.user_id)
            result_lines.append(output.result_text)
            agent_events.emit(
                run_id,
                "step_completed",
                f"Step {step.step_number} completed.",
                step_id=step.public_id,
            )
            identity_store.append_audit_event(
                event_type="agent_tool_succeeded",
                principal=principal,
                action=step.tool_name,
                resource_type="agent_step",
                resource_id=step.public_id,
                risk_level=step.risk_level,
                result="success",
                metadata={"run_id": run_id, "step_number": step.step_number},
            )

        current = agent_store.get_run(run_id, principal.user_id)
        if current.status in {"paused", "cancelled"}:
            return agent_store.get_detail(run_id, principal.user_id)
        final_result = self._summarize(result_lines, principal)
        try:
            completed = agent_store.update_run_status(
                run_id,
                principal.user_id,
                "completed",
                final_result=final_result,
                current_step=run.total_steps,
                expected_statuses={"running"},
            )
        except AgentConflictError:
            return agent_store.get_detail(run_id, principal.user_id)
        agent_events.emit(run_id, "completed", "Task completed.")
        identity_store.append_audit_event(
            event_type="agent_run_completed",
            principal=principal,
            action="agents.complete",
            resource_type="agent_run",
            resource_id=run_id,
            result="success",
            metadata={"step_count": run.total_steps},
        )
        return agent_store.get_detail(completed.public_id, principal.user_id)

    @staticmethod
    def _reject_invalid_approval(
        run_id: str,
        principal: AuthenticatedPrincipal,
        step_id: str,
    ):
        user_id = principal.user_id or ""
        error_summary = "Required separate approval is absent, expired, or invalid."
        try:
            agent_store.update_step(
                step_id,
                "failed",
                error_summary=error_summary,
                expected_statuses={"awaiting_approval"},
            )
            agent_store.cancel_pending_steps(run_id)
            agent_store.update_run_status(
                run_id,
                user_id,
                "failed",
                error_summary=error_summary,
                expected_statuses={"awaiting_approval"},
            )
        except AgentConflictError:
            return agent_store.get_detail(run_id, user_id)
        agent_events.emit(
            run_id,
            "failed",
            "A required approval was unavailable or expired.",
            step_id=step_id,
        )
        identity_store.append_audit_event(
            event_type="agent_approval_invalid",
            principal=principal,
            action="agents.start",
            resource_type="agent_step",
            resource_id=step_id,
            authorization_decision="denied",
            risk_level="low",
            result="failed",
            reason="Required separate approval was unavailable or expired.",
            metadata={"run_id": run_id},
        )
        return agent_store.get_detail(run_id, user_id)

    @staticmethod
    def _execute_with_timeout(
        tool_name: str,
        arguments: dict[str, object],
        principal: AuthenticatedPrincipal,
        run_goal: str,
        timeout_seconds: float,
    ):
        pool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="mirrage-agent-tool"
        )
        future = pool.submit(
            execute_registered_tool,
            tool_name,
            arguments,
            principal,
            run_goal,
        )
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeout as exc:
            future.cancel()
            raise TimeoutError("Registered tool timed out.") from exc
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _summarize(
        result_lines: list[str],
        principal: AuthenticatedPrincipal,
    ) -> str:
        if not result_lines:
            return "The bounded task completed without a result."
        deterministic = "\n".join(result_lines)[:4000]
        runtime = assistant_runtime.run_assistant_request(
            "Summarize these safe agent results concisely:\n" + deterministic,
            task_type="agent_result_summary",
            principal=principal,
        )
        if runtime.provider != "stub" and runtime.reply.strip():
            return runtime.reply.strip()[:4000]
        return deterministic

    @staticmethod
    def _fail(
        run_id: str,
        principal: AuthenticatedPrincipal,
        step_id: str,
        message: str,
    ):
        safe_message = " ".join(message.split())[:500]
        try:
            agent_store.update_step(
                step_id,
                "failed",
                error_summary=safe_message,
                expected_statuses={"ready", "running"},
            )
        except AgentConflictError:
            return agent_store.get_detail(run_id, principal.user_id or "")
        try:
            agent_store.update_run_status(
                run_id,
                principal.user_id or "",
                "failed",
                error_summary=safe_message,
                expected_statuses={"running", "paused"},
            )
        except AgentConflictError:
            return agent_store.get_detail(run_id, principal.user_id or "")
        agent_events.emit(
            run_id,
            "step_failed",
            "A step failed safely and execution stopped.",
            step_id=step_id,
        )
        identity_store.append_audit_event(
            event_type="agent_tool_failed",
            principal=principal,
            action="agents.execute",
            resource_type="agent_step",
            resource_id=step_id,
            result="failed",
            reason=safe_message,
            metadata={"run_id": run_id},
        )
        logger.warning(
            "Agent step failed safely.",
            extra={"event": "agent_step_failed", "subsystem": "agents"},
        )
        return agent_store.get_detail(run_id, principal.user_id or "")


agent_executor = AgentExecutor()
