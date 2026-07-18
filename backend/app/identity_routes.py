"""Identity, trusted-device, approval, and audit API routes."""

# FastAPI dependencies are intentionally declared in parameter defaults.
# ruff: noqa: B008

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.services.approvals import (
    cancel_approval,
    create_approval,
    decide_approval,
)
from backend.app.services.audit import search_audit_events
from backend.app.services.authentication import (
    get_required_principal,
    require_owner_permission,
    require_permission,
)
from backend.app.services.identity import (
    create_user,
    disable_user,
    enroll_device,
    identity_status,
    principal_response,
    revoke_device,
    set_permission_override,
    update_user,
)
from backend.app.services.identity_models import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalResponse,
    AuditEventListResponse,
    AuthenticatedPrincipal,
    IdentityPrincipalResponse,
    IdentityStatusResponse,
    IdentityUserCreateRequest,
    IdentityUserResponse,
    IdentityUserUpdateRequest,
    PermissionOverrideRequest,
    PermissionOverrideResponse,
    PermissionRegistryResponse,
    RolePermissionsResponse,
    TrustedDeviceCreateRequest,
    TrustedDeviceEnrollmentResponse,
    TrustedDeviceResponse,
)
from backend.app.services.identity_store import (
    IdentityConflictError,
    IdentityNotFoundError,
    IdentityStoreError,
    IdentityValidationError,
    identity_store,
)
from backend.app.services.permissions import (
    PERMISSION_REGISTRY,
    ROLE_PERMISSIONS,
    Permission,
)

router = APIRouter(prefix="/api", tags=["identity and safety"])


@router.get("/identity/status")
def read_identity_status() -> IdentityStatusResponse:
    return identity_status()


@router.get("/identity/me")
def read_identity_me(
    principal: AuthenticatedPrincipal = Depends(get_required_principal),
) -> IdentityPrincipalResponse:
    return principal_response(principal)


@router.get("/identity/roles")
def read_identity_roles(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.IDENTITY_ROLES_READ.value)
    ),
) -> list[RolePermissionsResponse]:
    return [
        RolePermissionsResponse(role=role, permissions=sorted(permissions))
        for role, permissions in ROLE_PERMISSIONS.items()
    ]


@router.get("/identity/permissions")
def read_identity_permissions(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.IDENTITY_PERMISSIONS_READ.value)
    ),
) -> PermissionRegistryResponse:
    return PermissionRegistryResponse(permissions=sorted(PERMISSION_REGISTRY))


@router.get("/identity/users")
def read_identity_users(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.IDENTITY_USERS_READ.value)
    ),
) -> list[IdentityUserResponse]:
    return identity_store.list_users()


@router.post("/identity/users", status_code=201)
def create_identity_user(
    request: IdentityUserCreateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_owner_permission(Permission.IDENTITY_USERS_MANAGE.value)
    ),
) -> IdentityUserResponse:
    return _identity_call(create_user, request, principal)


@router.get("/identity/users/{user_id}")
def read_identity_user(
    user_id: str,
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.IDENTITY_USERS_READ.value)
    ),
) -> IdentityUserResponse:
    return _identity_call(identity_store.get_user, user_id)


@router.patch("/identity/users/{user_id}")
def update_identity_user(
    user_id: str,
    request: IdentityUserUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_owner_permission(Permission.IDENTITY_USERS_MANAGE.value)
    ),
) -> IdentityUserResponse:
    return _identity_call(update_user, user_id, request, principal)


@router.post("/identity/users/{user_id}/disable")
def disable_identity_user(
    user_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_owner_permission(Permission.IDENTITY_USERS_MANAGE.value)
    ),
) -> IdentityUserResponse:
    return _identity_call(disable_user, user_id, principal)


@router.put("/identity/users/{user_id}/permissions")
def update_identity_permission_override(
    user_id: str,
    request: PermissionOverrideRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_owner_permission(Permission.IDENTITY_USERS_MANAGE.value)
    ),
) -> PermissionOverrideResponse:
    return _identity_call(set_permission_override, user_id, request, principal)


@router.get("/identity/devices")
def read_identity_devices(
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.IDENTITY_DEVICES_READ.value)
    ),
) -> list[TrustedDeviceResponse]:
    return identity_store.list_devices()


@router.post("/identity/devices", status_code=201)
def create_identity_device(
    request: TrustedDeviceCreateRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_owner_permission(Permission.IDENTITY_DEVICES_MANAGE.value)
    ),
) -> TrustedDeviceEnrollmentResponse:
    return _identity_call(enroll_device, request, principal)


@router.get("/identity/devices/{device_id}")
def read_identity_device(
    device_id: str,
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.IDENTITY_DEVICES_READ.value)
    ),
) -> TrustedDeviceResponse:
    return _identity_call(identity_store.get_device, device_id)


@router.post("/identity/devices/{device_id}/revoke")
def revoke_identity_device(
    device_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_owner_permission(Permission.IDENTITY_DEVICES_MANAGE.value)
    ),
) -> TrustedDeviceResponse:
    return _identity_call(revoke_device, device_id, principal)


@router.get("/approvals")
def read_approvals(
    status: str | None = None,
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.APPROVALS_READ.value)
    ),
) -> ApprovalListResponse:
    items = identity_store.list_approvals(status=status)
    return ApprovalListResponse(items=items, count=len(items))


@router.get("/approvals/{approval_id}")
def read_approval(
    approval_id: str,
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.APPROVALS_READ.value)
    ),
) -> ApprovalResponse:
    return _identity_call(identity_store.get_approval, approval_id)


@router.post("/approvals", status_code=201)
def create_approval_request(
    request: ApprovalCreateRequest,
    principal: AuthenticatedPrincipal = Depends(get_required_principal),
) -> ApprovalResponse:
    return _identity_call(create_approval, request, principal)


@router.post("/approvals/{approval_id}/approve")
def approve_request(
    approval_id: str,
    request: ApprovalDecisionRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.APPROVALS_MANAGE.value, risk_level="low")
    ),
) -> ApprovalResponse:
    return _identity_call(
        decide_approval,
        approval_id,
        request,
        principal,
        decision="approved",
    )


@router.post("/approvals/{approval_id}/deny")
def deny_request(
    approval_id: str,
    request: ApprovalDecisionRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.APPROVALS_MANAGE.value, risk_level="low")
    ),
) -> ApprovalResponse:
    return _identity_call(
        decide_approval,
        approval_id,
        request,
        principal,
        decision="denied",
    )


@router.post("/approvals/{approval_id}/cancel")
def cancel_request(
    approval_id: str,
    request: ApprovalDecisionRequest,
    principal: AuthenticatedPrincipal = Depends(get_required_principal),
) -> ApprovalResponse:
    return _identity_call(cancel_approval, approval_id, request, principal)


@router.get("/audit/events")
def read_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = None,
    user_id: str | None = None,
    decision: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    _principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.AUDIT_READ.value)
    ),
) -> AuditEventListResponse:
    return search_audit_events(
        limit=limit,
        offset=offset,
        event_type=event_type,
        user_id=user_id,
        decision=decision,
        date_from=date_from,
        date_to=date_to,
    )


def _identity_call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except IdentityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IdentityConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IdentityValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IdentityStoreError as exc:
        raise HTTPException(
            status_code=500, detail="Identity operation failed."
        ) from exc
