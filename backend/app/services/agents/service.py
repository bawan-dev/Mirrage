"""Application service coordinating agent planning, approvals, and execution."""

from __future__ import annotations

from backend.app.services.agents.events import agent_events
from backend.app.services.agents.executor import agent_executor
from backend.app.services.agents.models import (
    AgentApprovalDecisionResponse,
    AgentApprovalQueueResponse,
    AgentPlanRequest,
    AgentRunCreateRequest,
    AgentRunDetailResponse,
    AgentRunListResponse,
    AgentStatusResponse,
    AgentStepListResponse,
    AgentToolListResponse,
    AgentTypeListResponse,
    AgentTypeResponse,
)
from backend.app.services.agents.planner import agent_planner
from backend.app.services.agents.policy import agent_policy
from backend.app.services.agents.registry import agent_tool_registry
from backend.app.services.agents.store import (
    AgentConflictError,
    AgentNotFoundError,
    AgentValidationError,
    agent_store,
)
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.identity_store import IdentityConflictError, identity_store
from backend.app.settings import settings

_AGENT_TYPES = (
    AgentTypeResponse(
        name="planning",
        description="Build and execute a bounded plan from safe internal sources.",
        side_effects_allowed=False,
    ),
    AgentTypeResponse(
        name="memory",
        description="Search private memory and propose approval-gated additions.",
        side_effects_allowed=True,
    ),
    AgentTypeResponse(
        name="calendar",
        description="Read and summarize today's or upcoming calendar.",
        side_effects_allowed=False,
    ),
    AgentTypeResponse(
        name="smart_home",
        description="Read safe state or request approved low-risk controls.",
        side_effects_allowed=True,
    ),
    AgentTypeResponse(
        name="research",
        description=(
            "Organize supplied material without live web access or arbitrary fetching."
        ),
        side_effects_allowed=False,
    ),
)


class AgentService:
    def status(self) -> AgentStatusResponse:
        try:
            counts = agent_store.status_counts()
            database_status = "ready"
        except Exception:
            counts = {"active": 0, "awaiting_approval": 0, "failed": 0}
            database_status = "unavailable"
        enabled = settings.agents_enabled
        return AgentStatusResponse(
            enabled=enabled,
            database_status=database_status,
            active_run_count=counts["active"],
            awaiting_approval_count=counts["awaiting_approval"],
            failed_run_count=counts["failed"],
            queue_status=(
                "ready" if enabled and database_status == "ready" else "stopped"
            ),
            concurrency_limit=settings.agent_max_concurrent_runs,
            max_steps=settings.agent_max_steps,
            max_runtime_seconds=settings.agent_max_runtime_seconds,
            message=(
                "Bounded agents are ready."
                if enabled and database_status == "ready"
                else "Bounded agents are disabled or unavailable."
            ),
        )

    @staticmethod
    def types() -> AgentTypeListResponse:
        return AgentTypeListResponse(items=list(_AGENT_TYPES))

    @staticmethod
    def tools() -> AgentToolListResponse:
        return AgentToolListResponse(items=agent_tool_registry.descriptors())

    def create_run(
        self,
        principal: AuthenticatedPrincipal,
        request: AgentRunCreateRequest,
    ) -> AgentRunDetailResponse:
        self._require_enabled()
        run = agent_store.create_run(principal, request)
        agent_events.emit(run.public_id, "run_created", "Agent run created.")
        self._audit(
            "agent_run_created",
            principal,
            run.public_id,
            "created",
            {"agent_type": run.agent_type, "max_steps": run.max_steps},
        )
        return agent_store.get_detail(run.public_id, self._user_id(principal))

    def list_runs(self, principal: AuthenticatedPrincipal) -> AgentRunListResponse:
        items = agent_store.list_runs(self._user_id(principal))
        return AgentRunListResponse(items=items, count=len(items))

    def get_run(
        self, principal: AuthenticatedPrincipal, run_id: str
    ) -> AgentRunDetailResponse:
        try:
            return agent_store.get_detail(run_id, self._user_id(principal))
        except AgentNotFoundError:
            try:
                existing = agent_store.get_run_for_approver(run_id)
            except AgentNotFoundError:
                raise
            if existing.owner_user_id != principal.user_id:
                identity_store.append_audit_event(
                    event_type="agent_cross_user_access_denied",
                    principal=principal,
                    action="agents.read",
                    resource_type="agent_run",
                    resource_id=run_id,
                    authorization_decision="denied",
                    risk_level="read_only",
                    reason="agent.owner_scope.default_deny",
                    result="denied",
                )
            raise

    def plan(
        self,
        principal: AuthenticatedPrincipal,
        run_id: str,
        request: AgentPlanRequest,
    ) -> AgentRunDetailResponse:
        self._require_enabled()
        user_id = self._user_id(principal)
        run = agent_store.claim_run_for_planning(run_id, user_id)
        agent_events.emit(run_id, "planning", "Structured planning started.")
        self._audit("agent_planning_started", principal, run_id, "started")
        try:
            plan = agent_planner.propose(
                goal=run.goal,
                agent_type=run.agent_type,
                principal=principal,
                explicit_steps=request.steps,
            )
            if plan.clarification_prompt:
                plan = plan.model_copy(update={"steps": []})
            elif not plan.steps:
                raise AgentValidationError(
                    "A plan needs at least one validated step or a clarification."
                )
            validated = agent_policy.validate_plan(
                principal,
                run.agent_type,
                plan.steps,
                max_steps=run.max_steps,
            )
            detail = agent_store.save_plan(run_id, user_id, plan, validated)
            for step in detail.steps:
                if not step.approval_required:
                    continue
                approval = identity_store.create_approval(
                    requester=principal,
                    action=step.tool_name,
                    resource_type="agent_step",
                    resource_id=step.public_id,
                    risk_level=step.risk_level,
                    reason=step.description,
                    ttl_seconds=settings.agent_approval_ttl_seconds,
                )
                agent_store.attach_approval(step.public_id, approval.public_id)
                agent_events.emit(
                    run_id,
                    "awaiting_approval",
                    f"Step {step.step_number} requires separate approval.",
                    step_id=step.public_id,
                )
                self._audit(
                    "agent_approval_requested",
                    principal,
                    run_id,
                    "pending",
                    {"step_id": step.public_id, "tool": step.tool_name},
                )
            detail = agent_store.get_detail(run_id, user_id)
            event = (
                "awaiting_user_input"
                if detail.run.status == "awaiting_user_input"
                else "plan_ready"
            )
            agent_events.emit(
                run_id,
                event,
                (
                    "The plan needs clarification."
                    if event == "awaiting_user_input"
                    else f"Validated {detail.run.total_steps} planned step(s)."
                ),
            )
            self._audit(
                "agent_plan_validated",
                principal,
                run_id,
                detail.run.status,
                {"step_count": detail.run.total_steps},
            )
            return detail
        except Exception:
            try:
                agent_store.update_run_status(
                    run_id,
                    user_id,
                    "failed",
                    error_summary="Plan validation failed safely.",
                    expected_statuses={
                        "planning",
                        "ready",
                        "awaiting_approval",
                        "awaiting_user_input",
                    },
                )
            except AgentConflictError:
                return agent_store.get_detail(run_id, user_id)
            for step in agent_store.list_steps(run_id, user_id):
                if not step.approval_id or step.approval_status != "pending":
                    continue
                try:
                    identity_store.cancel_approval(
                        step.approval_id,
                        requester_user_id=user_id,
                        reason="Agent plan failed before execution.",
                    )
                except IdentityConflictError:
                    pass
            agent_store.cancel_pending_steps(run_id)
            agent_events.emit(run_id, "failed", "Plan validation failed safely.")
            self._audit(
                "agent_plan_rejected",
                principal,
                run_id,
                "failed",
                reason="Plan validation failed safely.",
            )
            raise

    def start(
        self, principal: AuthenticatedPrincipal, run_id: str
    ) -> AgentRunDetailResponse:
        self._require_enabled()
        return agent_executor.execute(run_id, principal)

    def pause(
        self, principal: AuthenticatedPrincipal, run_id: str
    ) -> AgentRunDetailResponse:
        user_id = self._user_id(principal)
        run = agent_store.get_run(run_id, user_id)
        if run.status not in {"ready", "running", "awaiting_approval"}:
            raise AgentConflictError("Only an active run can be paused.")
        agent_store.update_run_status(
            run_id,
            user_id,
            "paused",
            expected_statuses={"ready", "running", "awaiting_approval"},
        )
        agent_events.emit(run_id, "paused", "Agent run paused by its owner.")
        self._audit("agent_run_paused", principal, run_id, "paused")
        return agent_store.get_detail(run_id, user_id)

    def resume(
        self, principal: AuthenticatedPrincipal, run_id: str
    ) -> AgentRunDetailResponse:
        self._require_enabled()
        user_id = self._user_id(principal)
        run = agent_store.get_run(run_id, user_id)
        if run.status != "paused":
            raise AgentConflictError("Only a paused run can be resumed.")
        steps = agent_store.list_steps(run_id, user_id)
        pending = any(
            step.approval_required and step.approval_status == "pending"
            for step in steps
        )
        next_status = "awaiting_approval" if pending else "ready"
        agent_store.update_run_status(
            run_id,
            user_id,
            next_status,
            expected_statuses={"paused"},
        )
        agent_events.emit(run_id, "resumed", "Agent run resumed by its owner.")
        self._audit("agent_run_resumed", principal, run_id, next_status)
        if pending:
            return agent_store.get_detail(run_id, user_id)
        return agent_executor.execute(run_id, principal)

    def cancel(
        self, principal: AuthenticatedPrincipal, run_id: str
    ) -> AgentRunDetailResponse:
        user_id = self._user_id(principal)
        run = agent_store.get_run(run_id, user_id)
        if run.status in {"completed", "failed", "cancelled", "expired"}:
            raise AgentConflictError("A terminal run cannot be cancelled.")
        agent_store.update_run_status(
            run_id,
            user_id,
            "cancelled",
            expected_statuses={
                "draft",
                "planning",
                "awaiting_approval",
                "awaiting_user_input",
                "ready",
                "running",
                "paused",
            },
        )
        for step in agent_store.list_steps(run_id, user_id):
            if step.approval_id and step.approval_status == "pending":
                try:
                    identity_store.cancel_approval(
                        step.approval_id,
                        requester_user_id=user_id,
                        reason="Agent run cancelled by its owner.",
                    )
                except IdentityConflictError:
                    # A concurrent decision cannot make a cancelled run executable.
                    pass
        agent_store.cancel_pending_steps(run_id)
        agent_events.emit(run_id, "cancelled", "Agent run cancelled by its owner.")
        self._audit("agent_run_cancelled", principal, run_id, "cancelled")
        return agent_store.get_detail(run_id, user_id)

    def steps(
        self, principal: AuthenticatedPrincipal, run_id: str
    ) -> AgentStepListResponse:
        items = agent_store.list_steps(run_id, self._user_id(principal))
        return AgentStepListResponse(items=items, count=len(items))

    @staticmethod
    def approval_queue() -> AgentApprovalQueueResponse:
        items = agent_store.approval_queue()
        return AgentApprovalQueueResponse(items=items, count=len(items))

    def decide_approval(
        self,
        principal: AuthenticatedPrincipal,
        approval_id: str,
        *,
        approved: bool,
        reason: str,
    ) -> AgentApprovalDecisionResponse:
        decider_id = self._user_id(principal)
        queue_item = next(
            (
                item
                for item in agent_store.approval_queue()
                if item.approval_id == approval_id
            ),
            None,
        )
        if queue_item is None:
            raise AgentConflictError("Pending agent approval was not found.")
        decision = identity_store.decide_approval(
            approval_id,
            status="approved" if approved else "denied",
            decider_user_id=decider_id,
            reason=reason,
        )
        run = agent_store.get_run_for_approver(queue_item.run_id)
        if approved:
            if run.status in {"awaiting_approval", "paused"}:
                try:
                    agent_store.update_step(
                        queue_item.step_id,
                        "ready",
                        expected_statuses={"awaiting_approval"},
                    )
                except AgentConflictError:
                    pass
                else:
                    steps = agent_store.list_steps(
                        queue_item.run_id, queue_item.requesting_user_id
                    )
                    pending = any(
                        step.approval_required and step.approval_status == "pending"
                        for step in steps
                    )
                    if run.status == "awaiting_approval":
                        try:
                            agent_store.update_run_status(
                                queue_item.run_id,
                                queue_item.requesting_user_id,
                                "awaiting_approval" if pending else "ready",
                                expected_statuses={"awaiting_approval"},
                            )
                        except AgentConflictError:
                            pass
        else:
            if run.status in {"awaiting_approval", "paused"}:
                try:
                    agent_store.update_step(
                        queue_item.step_id,
                        "cancelled",
                        error_summary="The requested action was denied.",
                        expected_statuses={"awaiting_approval"},
                    )
                except AgentConflictError:
                    pass
                else:
                    for step in agent_store.list_steps(
                        queue_item.run_id, queue_item.requesting_user_id
                    ):
                        if not step.approval_id or step.approval_status != "pending":
                            continue
                        try:
                            identity_store.cancel_approval(
                                step.approval_id,
                                requester_user_id=queue_item.requesting_user_id,
                                reason="Another required agent action was denied.",
                            )
                        except IdentityConflictError:
                            pass
                    agent_store.cancel_pending_steps(queue_item.run_id)
                    try:
                        agent_store.update_run_status(
                            queue_item.run_id,
                            queue_item.requesting_user_id,
                            "failed",
                            error_summary="A required action was denied.",
                            expected_statuses={"awaiting_approval", "paused"},
                        )
                    except AgentConflictError:
                        pass
        event = "approval_granted" if approved else "approval_denied"
        agent_events.emit(
            queue_item.run_id,
            event,
            (
                "A separate approver approved the step."
                if approved
                else "A separate approver denied the step."
            ),
            step_id=queue_item.step_id,
        )
        identity_store.append_audit_event(
            event_type="agent_approval_decided",
            principal=principal,
            action="agents.approve" if approved else "agents.deny",
            resource_type="agent_step",
            resource_id=queue_item.step_id,
            authorization_decision="allowed",
            risk_level=queue_item.risk_level,
            result=decision.status,
            metadata={"run_id": queue_item.run_id},
        )
        return AgentApprovalDecisionResponse(
            approval_id=approval_id,
            run_id=queue_item.run_id,
            step_id=queue_item.step_id,
            status="approved" if approved else "denied",
        )

    @staticmethod
    def _user_id(principal: AuthenticatedPrincipal) -> str:
        if not principal.user_id:
            raise AgentValidationError("An authenticated user is required.")
        return principal.user_id

    @staticmethod
    def _require_enabled() -> None:
        if not settings.agents_enabled:
            raise AgentValidationError("Bounded agents are disabled.")

    @staticmethod
    def _audit(
        event_type: str,
        principal: AuthenticatedPrincipal,
        run_id: str,
        result: str,
        metadata: dict[str, object] | None = None,
        *,
        reason: str | None = None,
    ) -> None:
        identity_store.append_audit_event(
            event_type=event_type,
            principal=principal,
            action=event_type.replace("_", "."),
            resource_type="agent_run",
            resource_id=run_id,
            result=result,
            reason=reason,
            metadata=metadata,
        )


agent_service = AgentService()
