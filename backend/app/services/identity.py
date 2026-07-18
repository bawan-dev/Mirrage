"""Identity management service with audit boundaries."""

from __future__ import annotations

from backend.app.services.identity_models import (
    AuthenticatedPrincipal,
    IdentityPrincipalResponse,
    IdentityStatusResponse,
    IdentityUserCreateRequest,
    IdentityUserResponse,
    IdentityUserUpdateRequest,
    PermissionOverrideRequest,
    PermissionOverrideResponse,
    TrustedDeviceCreateRequest,
    TrustedDeviceEnrollmentResponse,
    TrustedDeviceResponse,
)
from backend.app.services.identity_store import identity_store
from backend.app.settings import settings


def identity_status() -> IdentityStatusResponse:
    if not settings.identity_enabled:
        return IdentityStatusResponse(
            enabled=False,
            mode=settings.identity_mode,
            database_status="disabled",
            active_user_count=0,
            owner_present=False,
            active_device_count=0,
            pending_approval_count=0,
            audit_status="disabled",
            message="Identity enforcement is disabled.",
        )
    status = identity_store.status()
    return IdentityStatusResponse(
        enabled=True,
        mode=settings.identity_mode,
        **status,
        message="Identity and safety store is available.",
    )


def principal_response(principal: AuthenticatedPrincipal) -> IdentityPrincipalResponse:
    return IdentityPrincipalResponse(
        authenticated=principal.authenticated,
        user_id=principal.user_id,
        display_name=principal.display_name,
        role=principal.role,
        device_id=principal.device_id,
        authentication_method=principal.authentication_method,
        assurance_level=principal.assurance_level,
        permissions=sorted(principal.effective_permissions),
        correlation_id=principal.correlation_id,
    )


def create_user(
    request: IdentityUserCreateRequest, actor: AuthenticatedPrincipal
) -> IdentityUserResponse:
    user = identity_store.create_user(
        display_name=request.display_name,
        role=request.role,
        household_member=request.household_member,
    )
    identity_store.append_audit_event(
        event_type="user_created",
        principal=actor,
        action="identity.users.create",
        resource_type="identity_user",
        resource_id=user.public_id,
        result="success",
        metadata={"role": user.role},
    )
    return user


def update_user(
    user_id: str,
    request: IdentityUserUpdateRequest,
    actor: AuthenticatedPrincipal,
) -> IdentityUserResponse:
    before = identity_store.get_user(user_id)
    user = identity_store.update_user(
        user_id,
        display_name=request.display_name,
        role=request.role,
        household_member=request.household_member,
    )
    event_type = "user_role_changed" if before.role != user.role else "user_updated"
    identity_store.append_audit_event(
        event_type=event_type,
        principal=actor,
        action="identity.users.update",
        resource_type="identity_user",
        resource_id=user.public_id,
        result="success",
        metadata={"previous_role": before.role, "role": user.role},
    )
    return user


def disable_user(user_id: str, actor: AuthenticatedPrincipal) -> IdentityUserResponse:
    user = identity_store.disable_user(user_id)
    identity_store.append_audit_event(
        event_type="user_disabled",
        principal=actor,
        action="identity.users.disable",
        resource_type="identity_user",
        resource_id=user.public_id,
        result="success",
    )
    return user


def set_permission_override(
    user_id: str,
    request: PermissionOverrideRequest,
    actor: AuthenticatedPrincipal,
) -> PermissionOverrideResponse:
    result = identity_store.set_permission_override(
        user_public_id=user_id,
        permission=request.permission,
        effect=request.effect,
        actor_user_id=actor.user_id,
    )
    identity_store.append_audit_event(
        event_type="permission_override_changed",
        principal=actor,
        action="identity.permissions.override",
        resource_type="identity_user",
        resource_id=user_id,
        result="success",
        metadata={"permission": request.permission, "effect": request.effect},
    )
    return result


def enroll_device(
    request: TrustedDeviceCreateRequest, actor: AuthenticatedPrincipal
) -> TrustedDeviceEnrollmentResponse:
    enrollment = identity_store.enroll_device(
        user_public_id=request.user_id,
        display_name=request.display_name,
        device_type=request.device_type,
        trust_level=request.trust_level,
        metadata=request.metadata,
    )
    identity_store.append_audit_event(
        event_type="device_enrolled",
        principal=actor,
        action="identity.devices.enroll",
        resource_type="trusted_device",
        resource_id=enrollment.device.public_id,
        result="success",
        metadata={
            "device_type": enrollment.device.device_type,
            "trust_level": enrollment.device.trust_level,
        },
    )
    return enrollment


def revoke_device(
    device_id: str, actor: AuthenticatedPrincipal
) -> TrustedDeviceResponse:
    device = identity_store.revoke_device(device_id)
    identity_store.append_audit_event(
        event_type="device_revoked",
        principal=actor,
        action="identity.devices.revoke",
        resource_type="trusted_device",
        resource_id=device.public_id,
        result="success",
    )
    return device
