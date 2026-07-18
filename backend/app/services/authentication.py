"""FastAPI authentication dependencies for trusted devices and dev mode."""

# FastAPI dependencies are intentionally declared in parameter defaults.
# ruff: noqa: B008

from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.services.authorization import (
    authorization_service,
    effective_permissions,
    principal_for_device,
)
from backend.app.services.identity_models import (
    AuthenticatedPrincipal,
    AuthorizationRequest,
)
from backend.app.services.identity_store import identity_store
from backend.app.services.permissions import permissions_for_role
from backend.app.services.relationship_store import relationship_store
from backend.app.settings import settings

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


def get_optional_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> AuthenticatedPrincipal:
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())

    if credentials is not None:
        if credentials.scheme.casefold() != "bearer":
            _audit_authentication_failure(correlation_id, "unsupported_scheme")
            raise _authentication_error("Unsupported authentication scheme.")
        authenticated = identity_store.authenticate_device_token(
            credentials.credentials
        )
        if authenticated is None:
            _audit_authentication_failure(correlation_id, "invalid_device_token")
            raise _authentication_error("Trusted-device token is invalid or revoked.")
        user, device = authenticated
        principal = principal_for_device(user, device, correlation_id=correlation_id)
        session_token = request.headers.get("X-Mirrage-Human-Session")
        if session_token:
            session = relationship_store.authenticate_human_session(
                session_token, user.public_id, device.public_id
            )
            if session is None:
                identity_store.append_audit_event(
                    event_type="human_session_authentication_failed",
                    principal=principal,
                    action="human_session.authenticate",
                    resource_type="interaction_session",
                    result="denied",
                    reason="invalid_expired_or_mismatched_session",
                )
                raise _authentication_error(
                    "Human interaction session is invalid or expired."
                )
            principal = principal.model_copy(
                update={
                    "human_session_active": True,
                    "human_session_id": session.public_id,
                }
            )
        identity_store.append_audit_event(
            event_type="authentication_succeeded",
            principal=principal,
            action="authenticate",
            resource_type="trusted_device",
            resource_id=device.public_id,
            result="success",
        )
        logger.info(
            "Trusted-device authentication succeeded.",
            extra={"event": "authentication_succeeded", "subsystem": "identity"},
        )
        return principal

    if _development_bypass_allowed():
        principal = _development_principal(correlation_id)
        identity_store.append_audit_event(
            event_type="development_authentication",
            principal=principal,
            action="authenticate",
            resource_type="development_bypass",
            result="success",
        )
        return principal

    return AuthenticatedPrincipal(
        user_id=None,
        display_name="Guest",
        role="anonymous",
        device_id=None,
        authentication_method="anonymous",
        assurance_level="anonymous",
        effective_permissions=frozenset(),
        correlation_id=correlation_id,
    )


def get_required_principal(
    principal: AuthenticatedPrincipal = Depends(get_optional_principal),
) -> AuthenticatedPrincipal:
    if not principal.authenticated:
        identity_store.append_audit_event(
            event_type="authentication_required",
            principal=principal,
            action="authenticate",
            result="denied",
            reason="missing_credentials",
        )
        raise _authentication_error("Authentication is required.")
    return principal


def require_permission(
    permission: str,
    *,
    resource_type: str = "api",
    risk_level: str = "read_only",
    human_session_required: bool = False,
) -> Callable[..., AuthenticatedPrincipal]:
    def dependency(
        request: Request,
        principal: AuthenticatedPrincipal = Depends(get_required_principal),
    ) -> AuthenticatedPrincipal:
        decision = authorization_service.decide(
            principal,
            AuthorizationRequest(
                permission=permission,
                resource_type=resource_type,
                resource_id=request.url.path,
                risk_level=risk_level,
            ),
        )
        if (
            decision.decision == "allowed"
            and human_session_required
            and principal.device_type == "mirror"
            and not principal.human_session_active
        ):
            identity_store.append_audit_event(
                event_type="authorization_decision",
                principal=principal,
                action=permission,
                resource_type=resource_type,
                resource_id=request.url.path,
                authorization_decision="denied",
                risk_level=risk_level,
                reason="human_session.required_for_mirror",
                result="denied",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "decision": "denied",
                    "reason": (
                        "A current human interaction session is required on a mirror."
                    ),
                    "permission": permission,
                    "policy_id": "human_session.required_for_mirror",
                },
            )
        if decision.decision != "allowed":
            status_code = (
                status.HTTP_409_CONFLICT
                if decision.decision == "approval_required"
                else status.HTTP_403_FORBIDDEN
            )
            raise HTTPException(
                status_code=status_code,
                detail={
                    "decision": decision.decision,
                    "reason": decision.reason,
                    "permission": decision.permission,
                    "policy_id": decision.policy_id,
                },
            )
        return principal

    return dependency


def require_owner(
    principal: AuthenticatedPrincipal = Depends(get_required_principal),
) -> AuthenticatedPrincipal:
    if principal.role != "owner":
        identity_store.append_audit_event(
            event_type="authorization_decision",
            principal=principal,
            action="identity.owner_required",
            authorization_decision="denied",
            risk_level="high",
            reason="identity.owner_only",
            result="denied",
        )
        raise HTTPException(status_code=403, detail="Owner access is required.")
    return principal


def require_owner_permission(
    permission: str,
    *,
    resource_type: str = "identity_admin",
) -> Callable[..., AuthenticatedPrincipal]:
    permission_dependency = require_permission(
        permission,
        resource_type=resource_type,
        risk_level="low",
    )

    def dependency(
        principal: AuthenticatedPrincipal = Depends(permission_dependency),
    ) -> AuthenticatedPrincipal:
        if principal.role != "owner":
            identity_store.append_audit_event(
                event_type="authorization_decision",
                principal=principal,
                action=permission,
                resource_type=resource_type,
                authorization_decision="denied",
                risk_level="low",
                reason="identity.owner_only",
                result="denied",
            )
            raise HTTPException(status_code=403, detail="Owner access is required.")
        return principal

    return dependency


def _development_bypass_allowed() -> bool:
    return (
        settings.identity_enabled
        and settings.identity_dev_bypass
        and settings.identity_mode == "development"
        and settings.app_env != "production"
    )


def _development_principal(correlation_id: str) -> AuthenticatedPrincipal:
    owners = [
        user
        for user in identity_store.list_users()
        if user.role == "owner" and user.status == "active"
    ]
    if owners:
        user = owners[0]
        user_id = user.public_id
        display_name = user.display_name
        permissions = effective_permissions(user)
    else:
        user_id = "development-principal"
        display_name = "Local developer"
        permissions = permissions_for_role("owner")

    logger.warning(
        "Explicit identity development bypass is active.",
        extra={"event": "identity_dev_bypass", "subsystem": "identity"},
    )
    return AuthenticatedPrincipal(
        user_id=user_id,
        display_name=display_name,
        role="owner",
        device_id="development-device",
        authentication_method="development",
        assurance_level="low",
        effective_permissions=permissions,
        correlation_id=correlation_id,
        device_trust_level="limited",
        device_type="other",
        human_session_active=True,
    )


def _audit_authentication_failure(correlation_id: str, reason: str) -> None:
    identity_store.append_audit_event(
        event_type="authentication_failed",
        action="authenticate",
        result="denied",
        reason=reason,
        correlation_id=correlation_id,
    )
    logger.warning(
        "Trusted-device authentication failed.",
        extra={"event": "authentication_failed", "subsystem": "identity"},
    )


def _authentication_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )
