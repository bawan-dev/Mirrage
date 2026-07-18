"""Audit service boundary kept separate from operational logging."""

from backend.app.services.identity_models import (
    AuditEventListResponse,
    AuthenticatedPrincipal,
)
from backend.app.services.identity_store import identity_store


def record_sensitive_access(
    principal: AuthenticatedPrincipal,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    result: str = "success",
) -> None:
    identity_store.append_audit_event(
        event_type="sensitive_data_access",
        principal=principal,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        authorization_decision="allowed",
        risk_level="read_only",
        result=result,
    )


def search_audit_events(
    *,
    limit: int,
    offset: int,
    event_type: str | None,
    user_id: str | None,
    decision: str | None,
    date_from: str | None,
    date_to: str | None,
) -> AuditEventListResponse:
    items, count = identity_store.list_audit_events(
        limit=limit,
        offset=offset,
        event_type=event_type,
        user_id=user_id,
        decision=decision,
        date_from=date_from,
        date_to=date_to,
    )
    return AuditEventListResponse(
        items=items,
        count=count,
        limit=max(1, min(limit, 200)),
        offset=max(0, offset),
    )
