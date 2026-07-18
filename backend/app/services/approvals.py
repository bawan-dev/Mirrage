"""Approval workflow service; approvals never override global safety blocks."""

from backend.app.services.identity_models import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ApprovalResponse,
    AuthenticatedPrincipal,
)
from backend.app.services.identity_store import identity_store


def create_approval(
    request: ApprovalCreateRequest, principal: AuthenticatedPrincipal
) -> ApprovalResponse:
    approval = identity_store.create_approval(
        requester=principal,
        action=request.action,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        risk_level=request.risk_level,
        reason=request.reason,
    )
    identity_store.append_audit_event(
        event_type="approval_requested",
        principal=principal,
        action=approval.action,
        resource_type=approval.resource_type,
        resource_id=approval.resource_id,
        risk_level=approval.risk_level,
        result="pending",
        metadata={"approval_id": approval.public_id},
    )
    return approval


def decide_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    principal: AuthenticatedPrincipal,
    *,
    decision: str,
) -> ApprovalResponse:
    approval = identity_store.decide_approval(
        approval_id,
        status=decision,
        decider_user_id=principal.user_id or "",
        reason=request.reason,
    )
    identity_store.append_audit_event(
        event_type="approval_decided",
        principal=principal,
        action=approval.action,
        resource_type=approval.resource_type,
        resource_id=approval.resource_id,
        authorization_decision=decision,
        risk_level=approval.risk_level,
        result=decision,
        metadata={"approval_id": approval.public_id},
    )
    return approval


def cancel_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    principal: AuthenticatedPrincipal,
) -> ApprovalResponse:
    approval = identity_store.cancel_approval(
        approval_id,
        requester_user_id=principal.user_id or "",
        reason=request.reason,
    )
    identity_store.append_audit_event(
        event_type="approval_cancelled",
        principal=principal,
        action=approval.action,
        resource_type=approval.resource_type,
        resource_id=approval.resource_id,
        risk_level=approval.risk_level,
        result="cancelled",
        metadata={"approval_id": approval.public_id},
    )
    return approval
