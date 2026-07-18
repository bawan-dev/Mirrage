"""Profile, relationship, shared-context, and human-session API routes."""

# FastAPI dependencies are intentionally declared in parameter defaults.
# ruff: noqa: B008

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.app.services.authentication import (
    get_optional_principal,
    require_permission,
)
from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.identity_store import (
    IdentityConflictError,
    IdentityNotFoundError,
    IdentityStoreError,
    IdentityValidationError,
    identity_store,
)
from backend.app.services.permissions import Permission
from backend.app.services.personalization import (
    greeting_for,
    profile_directory,
    visible_profile,
)
from backend.app.services.relationship_models import (
    PROFILE_FIELDS,
    GreetingResponse,
    HumanSessionCreateRequest,
    HumanSessionEnrollmentResponse,
    HumanSessionResponse,
    PersonalizationProfileResponse,
    PersonalizationProfileUpdate,
    RelationshipCreateRequest,
    RelationshipListResponse,
    RelationshipResponse,
    SharedContextCreateRequest,
    SharedContextListResponse,
    SharedContextResponse,
    SharedContextShareRequest,
    SharedContextUpdateRequest,
    VisibleProfileResponse,
)
from backend.app.services.relationship_store import relationship_store

router = APIRouter(prefix="/api", tags=["relationships and personalization"])


@router.get("/profile/me")
def read_my_profile(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.PROFILE_READ_SELF.value,
            resource_type="profile",
            human_session_required=True,
        )
    ),
) -> PersonalizationProfileResponse:
    return _call(relationship_store.get_profile, _user_id(principal))


@router.patch("/profile/me")
def update_my_profile(
    request: PersonalizationProfileUpdate,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.PROFILE_UPDATE_SELF.value,
            resource_type="profile",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> PersonalizationProfileResponse:
    result = _call(relationship_store.update_profile, _user_id(principal), request)
    fields = sorted(request.model_dump(exclude_unset=True))
    identity_store.append_audit_event(
        event_type="profile_updated",
        principal=principal,
        action="profile.update_self",
        resource_type="personalization_profile",
        resource_id=_user_id(principal),
        result="success",
        metadata={"fields": fields, "privacy_changed": "visibility" in fields},
    )
    return result


@router.get("/profiles/directory")
def read_profile_directory(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.PROFILE_DIRECTORY_READ.value,
            resource_type="profile",
            human_session_required=True,
        )
    ),
) -> list[VisibleProfileResponse]:
    return _call(profile_directory, _user_id(principal))


@router.get("/profiles/{user_id}")
def read_visible_profile(
    user_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.PROFILE_DIRECTORY_READ.value,
            resource_type="profile",
            human_session_required=True,
        )
    ),
) -> VisibleProfileResponse:
    result = _call(visible_profile, _user_id(principal), user_id)
    if user_id != principal.user_id and len(result.visible_fields) < len(
        PROFILE_FIELDS
    ):
        identity_store.append_audit_event(
            event_type="cross_user_profile_access_filtered",
            principal=principal,
            action="profile.read_visible",
            resource_type="personalization_profile",
            resource_id=user_id,
            authorization_decision="denied",
            result="filtered",
            reason="profile.field_visibility",
            metadata={
                "visible_field_count": len(result.visible_fields),
                "filtered_field_count": len(PROFILE_FIELDS)
                - len(result.visible_fields),
            },
        )
    return result


@router.get("/greeting")
def read_greeting(
    principal: AuthenticatedPrincipal = Depends(get_optional_principal),
) -> GreetingResponse:
    return greeting_for(principal)


@router.get("/relationships")
def read_relationships(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.RELATIONSHIPS_READ.value,
            resource_type="relationship",
            human_session_required=True,
        )
    ),
) -> RelationshipListResponse:
    items = _call(relationship_store.list_relationships, _user_id(principal))
    return RelationshipListResponse(items=items, count=len(items))


@router.post("/relationships", status_code=201)
def create_relationship(
    request: RelationshipCreateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.RELATIONSHIPS_MANAGE.value,
            resource_type="relationship",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> RelationshipResponse:
    result = _call(
        relationship_store.propose_relationship, _user_id(principal), request
    )
    _audit_relationship("relationship_proposed", result, principal)
    return result


@router.get("/relationships/{relationship_id}")
def read_relationship(
    relationship_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.RELATIONSHIPS_READ.value,
            resource_type="relationship",
            human_session_required=True,
        )
    ),
) -> RelationshipResponse:
    return _call(
        relationship_store.get_relationship, relationship_id, _user_id(principal)
    )


@router.post("/relationships/{relationship_id}/accept")
def accept_relationship(
    relationship_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.RELATIONSHIPS_MANAGE.value,
            resource_type="relationship",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> RelationshipResponse:
    result = _call(
        relationship_store.respond_relationship,
        relationship_id,
        _user_id(principal),
        "active",
    )
    _audit_relationship("relationship_accepted", result, principal)
    return result


@router.post("/relationships/{relationship_id}/reject")
def reject_relationship(
    relationship_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.RELATIONSHIPS_MANAGE.value,
            resource_type="relationship",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> RelationshipResponse:
    result = _call(
        relationship_store.respond_relationship,
        relationship_id,
        _user_id(principal),
        "rejected",
    )
    _audit_relationship("relationship_rejected", result, principal)
    return result


@router.post("/relationships/{relationship_id}/archive")
def archive_relationship(
    relationship_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.RELATIONSHIPS_MANAGE.value,
            resource_type="relationship",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> RelationshipResponse:
    result = _call(
        relationship_store.archive_relationship,
        relationship_id,
        _user_id(principal),
    )
    _audit_relationship("relationship_archived", result, principal)
    return result


@router.get("/shared-context")
def read_shared_context(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SHARED_CONTEXT_READ.value,
            resource_type="shared_context",
            human_session_required=True,
        )
    ),
) -> SharedContextListResponse:
    items = _call(relationship_store.list_shared_context, _user_id(principal))
    return SharedContextListResponse(items=items, count=len(items))


@router.post("/shared-context", status_code=201)
def create_shared_context(
    request: SharedContextCreateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SHARED_CONTEXT_MANAGE.value,
            resource_type="shared_context",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> SharedContextResponse:
    result = _call(
        relationship_store.create_shared_context, _user_id(principal), request
    )
    _audit_shared("shared_context_created", result, principal)
    return result


@router.get("/shared-context/{context_id}")
def read_shared_context_item(
    context_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SHARED_CONTEXT_READ.value,
            resource_type="shared_context",
            human_session_required=True,
        )
    ),
) -> SharedContextResponse:
    return _call(relationship_store.get_shared_context, context_id, _user_id(principal))


@router.patch("/shared-context/{context_id}")
def update_shared_context(
    context_id: str,
    request: SharedContextUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SHARED_CONTEXT_MANAGE.value,
            resource_type="shared_context",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> SharedContextResponse:
    result = _call(
        relationship_store.update_shared_context,
        context_id,
        _user_id(principal),
        request,
    )
    _audit_shared("shared_context_updated", result, principal)
    return result


@router.post("/shared-context/{context_id}/share")
def share_context(
    context_id: str,
    request: SharedContextShareRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SHARED_CONTEXT_MANAGE.value,
            resource_type="shared_context",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> SharedContextResponse:
    result = _call(
        relationship_store.share_context,
        context_id,
        _user_id(principal),
        request.user_id,
    )
    _audit_shared("shared_context_shared", result, principal, target=request.user_id)
    return result


@router.post("/shared-context/{context_id}/revoke")
def revoke_context(
    context_id: str,
    request: SharedContextShareRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SHARED_CONTEXT_MANAGE.value,
            resource_type="shared_context",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> SharedContextResponse:
    result = _call(
        relationship_store.revoke_context,
        context_id,
        _user_id(principal),
        request.user_id,
    )
    _audit_shared("shared_context_revoked", result, principal, target=request.user_id)
    return result


@router.post("/shared-context/{context_id}/archive")
def archive_context(
    context_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.SHARED_CONTEXT_MANAGE.value,
            resource_type="shared_context",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> SharedContextResponse:
    result = _call(relationship_store.archive_context, context_id, _user_id(principal))
    _audit_shared("shared_context_archived", result, principal)
    return result


@router.post("/sessions", status_code=201)
def create_human_session(
    request: HumanSessionCreateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.HUMAN_SESSION_MANAGE.value,
            resource_type="interaction_session",
            risk_level="low",
        )
    ),
) -> HumanSessionEnrollmentResponse:
    if not principal.device_id or principal.authentication_method != "trusted_device":
        raise HTTPException(
            status_code=409,
            detail="Human sessions are created from an enrolled trusted device.",
        )
    result = _call(
        relationship_store.create_human_session,
        _user_id(principal),
        principal.device_id,
        request.duration_seconds,
    )
    identity_store.append_audit_event(
        event_type="human_session_started",
        principal=principal,
        action="human_session.start",
        resource_type="interaction_session",
        resource_id=result.session.public_id,
        result="success",
    )
    return result


@router.post("/sessions/current/end")
def end_human_session(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.HUMAN_SESSION_MANAGE.value,
            resource_type="interaction_session",
            risk_level="low",
            human_session_required=True,
        )
    ),
) -> HumanSessionResponse:
    if not principal.human_session_id:
        raise HTTPException(status_code=409, detail="No human session is active.")
    result = _call(
        relationship_store.end_human_session,
        principal.human_session_id,
        _user_id(principal),
    )
    identity_store.append_audit_event(
        event_type="human_session_ended",
        principal=principal,
        action="human_session.end",
        resource_type="interaction_session",
        resource_id=result.public_id,
        result="success",
    )
    return result


def _audit_relationship(
    event: str, relationship: RelationshipResponse, principal: AuthenticatedPrincipal
) -> None:
    identity_store.append_audit_event(
        event_type=event,
        principal=principal,
        action=event.replace("_", "."),
        resource_type="relationship",
        resource_id=relationship.public_id,
        result="success",
        metadata={
            "status": relationship.status,
            "relationship_type": relationship.relationship_type,
        },
    )


def _audit_shared(
    event: str,
    item: SharedContextResponse,
    principal: AuthenticatedPrincipal,
    *,
    target: str | None = None,
) -> None:
    metadata: dict[str, Any] = {
        "context_type": item.context_type,
        "visibility": item.visibility,
    }
    if target:
        metadata["target_user_id"] = target
    identity_store.append_audit_event(
        event_type=event,
        principal=principal,
        action=event.replace("_", "."),
        resource_type="shared_context",
        resource_id=item.public_id,
        result="success",
        metadata=metadata,
    )


def _user_id(principal: AuthenticatedPrincipal) -> str:
    if not principal.user_id:
        raise HTTPException(status_code=401, detail="Authentication is required.")
    return principal.user_id


def _call(function: Callable[..., Any], *args: Any) -> Any:
    try:
        return function(*args)
    except IdentityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IdentityConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IdentityValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IdentityStoreError as exc:
        raise HTTPException(
            status_code=500, detail="Relationship operation failed."
        ) from exc
