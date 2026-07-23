"""Authenticated API routes for bounded, user-owned agent runs."""

# FastAPI dependencies are intentionally declared in parameter defaults.
# ruff: noqa: B008

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.app.services.agents.events import agent_events
from backend.app.services.agents.models import (
    AgentApprovalDecisionRequest,
    AgentApprovalDecisionResponse,
    AgentApprovalQueueResponse,
    AgentEventListResponse,
    AgentPlanRequest,
    AgentRunCreateRequest,
    AgentRunDetailResponse,
    AgentRunListResponse,
    AgentStatusResponse,
    AgentStepListResponse,
    AgentToolListResponse,
    AgentTypeListResponse,
)
from backend.app.services.agents.service import agent_service
from backend.app.services.agents.store import (
    AgentConflictError,
    AgentNotFoundError,
    AgentStoreError,
    AgentValidationError,
    agent_store,
)
from backend.app.services.authentication import require_permission
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.identity_store import (
    IdentityConflictError,
    IdentityNotFoundError,
    IdentityValidationError,
)
from backend.app.services.permissions import Permission

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/status", response_model=AgentStatusResponse)
def read_agent_status(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.AGENTS_USE.value, resource_type="agent")
    ),
) -> AgentStatusResponse:
    return agent_service.status()


@router.get("/types", response_model=AgentTypeListResponse)
def read_agent_types(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.AGENTS_USE.value, resource_type="agent")
    ),
) -> AgentTypeListResponse:
    return agent_service.types()


@router.get("/tools", response_model=AgentToolListResponse)
def read_agent_tools(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.AGENTS_USE.value, resource_type="agent")
    ),
) -> AgentToolListResponse:
    return agent_service.tools()


@router.post("/runs", response_model=AgentRunDetailResponse, status_code=201)
def create_agent_run(
    request: AgentRunCreateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_USE.value,
            resource_type="agent_run",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> AgentRunDetailResponse:
    return _call(agent_service.create_run, principal, request)


@router.get("/runs", response_model=AgentRunListResponse)
def read_agent_runs(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_READ_OWN.value,
            resource_type="agent_run",
            human_session_required=True,
        )
    ),
) -> AgentRunListResponse:
    return _call(agent_service.list_runs, principal)


@router.get("/runs/{run_id}", response_model=AgentRunDetailResponse)
def read_agent_run(
    run_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_READ_OWN.value,
            resource_type="agent_run",
            human_session_required=True,
        )
    ),
) -> AgentRunDetailResponse:
    return _call(agent_service.get_run, principal, run_id)


@router.post("/runs/{run_id}/plan", response_model=AgentRunDetailResponse)
def plan_agent_run(
    run_id: str,
    request: AgentPlanRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_PLAN.value,
            resource_type="agent_run",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> AgentRunDetailResponse:
    return _call(agent_service.plan, principal, run_id, request)


@router.post("/runs/{run_id}/start", response_model=AgentRunDetailResponse)
def start_agent_run(
    run_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_EXECUTE_READ_ONLY.value,
            resource_type="agent_run",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> AgentRunDetailResponse:
    return _call(agent_service.start, principal, run_id)


@router.post("/runs/{run_id}/pause", response_model=AgentRunDetailResponse)
def pause_agent_run(
    run_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_PAUSE_OWN.value,
            resource_type="agent_run",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> AgentRunDetailResponse:
    return _call(agent_service.pause, principal, run_id)


@router.post("/runs/{run_id}/resume", response_model=AgentRunDetailResponse)
def resume_agent_run(
    run_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_RESUME_OWN.value,
            resource_type="agent_run",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> AgentRunDetailResponse:
    return _call(agent_service.resume, principal, run_id)


@router.post("/runs/{run_id}/cancel", response_model=AgentRunDetailResponse)
def cancel_agent_run(
    run_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_CANCEL_OWN.value,
            resource_type="agent_run",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> AgentRunDetailResponse:
    return _call(agent_service.cancel, principal, run_id)


@router.get("/runs/{run_id}/steps", response_model=AgentStepListResponse)
def read_agent_steps(
    run_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_READ_OWN.value,
            resource_type="agent_run",
            human_session_required=True,
        )
    ),
) -> AgentStepListResponse:
    return _call(agent_service.steps, principal, run_id)


@router.get("/runs/{run_id}/events", response_model=AgentEventListResponse)
def read_agent_events(
    run_id: str,
    after: int = Query(default=0, ge=0),
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_READ_OWN.value,
            resource_type="agent_run",
            human_session_required=True,
        )
    ),
) -> AgentEventListResponse:
    user_id = principal.user_id or ""
    items = _call(agent_store.list_events, run_id, user_id, after_sequence=after)
    return AgentEventListResponse(items=items, count=len(items))


@router.get("/runs/{run_id}/events/stream")
def stream_agent_events(
    run_id: str,
    after: int = Query(default=0, ge=0),
    follow: bool = False,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_READ_OWN.value,
            resource_type="agent_run",
            human_session_required=True,
        )
    ),
) -> StreamingResponse:
    user_id = principal.user_id or ""
    _call(agent_store.get_run, run_id, user_id)
    return StreamingResponse(
        agent_events.stream(run_id, user_id, after_sequence=after, follow=follow),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/approvals", response_model=AgentApprovalQueueResponse)
def read_agent_approval_queue(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_APPROVE.value,
            resource_type="agent_approval",
            human_session_required=True,
        )
    ),
) -> AgentApprovalQueueResponse:
    return _call(agent_service.approval_queue)


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=AgentApprovalDecisionResponse,
)
def approve_agent_step(
    approval_id: str,
    request: AgentApprovalDecisionRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_APPROVE.value,
            resource_type="agent_approval",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> AgentApprovalDecisionResponse:
    return _call(
        agent_service.decide_approval,
        principal,
        approval_id,
        approved=True,
        reason=request.reason,
    )


@router.post(
    "/approvals/{approval_id}/deny",
    response_model=AgentApprovalDecisionResponse,
)
def deny_agent_step(
    approval_id: str,
    request: AgentApprovalDecisionRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.AGENTS_APPROVE.value,
            resource_type="agent_approval",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> AgentApprovalDecisionResponse:
    return _call(
        agent_service.decide_approval,
        principal,
        approval_id,
        approved=False,
        reason=request.reason,
    )


def _call(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except (AgentNotFoundError, IdentityNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (AgentConflictError, IdentityConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (AgentValidationError, IdentityValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AgentStoreError as exc:
        raise HTTPException(
            status_code=500, detail="Agent operation failed safely."
        ) from exc
