"""Deterministic, backend-owned authorization and safety policy engine."""

from __future__ import annotations

from backend.app.services.identity_models import (
    AuthenticatedPrincipal,
    AuthorizationDecision,
    AuthorizationRequest,
    IdentityUserResponse,
    TrustedDeviceResponse,
)
from backend.app.services.identity_store import identity_store
from backend.app.services.permissions import (
    PERMISSION_REGISTRY,
    Permission,
    permissions_for_role,
)
from backend.app.services.smart_home_models import BLOCKED_HIGH_RISK_DOMAINS


def effective_permissions(user: IdentityUserResponse) -> frozenset[str]:
    """Resolve role policy plus explicit grants and denies."""

    permissions = set(permissions_for_role(user.role))
    overrides = identity_store.permission_overrides(user.public_id)
    for permission, effect in overrides.items():
        if effect == "grant":
            permissions.add(permission)
    for permission, effect in overrides.items():
        if effect == "deny":
            permissions.discard(permission)
    return frozenset(permissions)


def principal_for_device(
    user: IdentityUserResponse,
    device: TrustedDeviceResponse,
    *,
    correlation_id: str,
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=user.public_id,
        display_name=user.display_name,
        role=user.role,
        device_id=device.public_id,
        authentication_method="trusted_device",
        assurance_level="trusted_device",
        effective_permissions=effective_permissions(user),
        correlation_id=correlation_id,
        device_trust_level=device.trust_level,
        device_type=device.device_type,
    )


class AuthorizationService:
    """Returns explainable decisions; callers remain responsible for actions."""

    def decide(
        self,
        principal: AuthenticatedPrincipal,
        request: AuthorizationRequest,
        *,
        audit: bool = True,
    ) -> AuthorizationDecision:
        decision = self._decide(principal, request)
        if audit:
            identity_store.append_audit_event(
                event_type="authorization_decision",
                principal=principal,
                action=request.permission,
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                authorization_decision=decision.decision,
                risk_level=request.risk_level,
                reason=decision.policy_id,
                result=decision.decision,
            )
        return decision

    def _decide(
        self,
        principal: AuthenticatedPrincipal,
        request: AuthorizationRequest,
    ) -> AuthorizationDecision:
        if request.permission not in PERMISSION_REGISTRY:
            return _decision(
                request,
                "denied",
                "Permission is not registered.",
                "permission.unknown.default_deny",
            )

        if not principal.authenticated:
            return _decision(
                request,
                "denied",
                "Authentication is required.",
                "identity.anonymous.default_deny",
            )

        domain = str(request.context.get("smart_home_domain") or "")
        if (
            request.resource_type == "smart_home"
            and domain in BLOCKED_HIGH_RISK_DOMAINS
        ):
            return _decision(
                request,
                "denied",
                "This smart-home domain is globally blocked.",
                "smart_home.high_risk.global_block",
            )

        if request.risk_level == "critical":
            return _decision(
                request,
                "denied",
                "Critical actions are not enabled in this phase.",
                "risk.critical.global_block",
            )

        if request.permission not in principal.effective_permissions:
            return _decision(
                request,
                "denied",
                "The authenticated principal does not have this permission.",
                "permission.effective.default_deny",
            )

        if request.risk_level in {"medium", "high"}:
            if (
                Permission.SMART_HOME_REQUEST_APPROVAL.value
                in principal.effective_permissions
                or Permission.APPROVALS_MANAGE.value in principal.effective_permissions
            ):
                return _decision(
                    request,
                    "approval_required",
                    "This risk level requires a separate approval decision.",
                    "risk.approval.required",
                )
            return _decision(
                request,
                "denied",
                "The principal cannot request approval for this action.",
                "risk.approval.permission_missing",
            )

        return _decision(
            request,
            "allowed",
            "The effective permission and safety policy allow this action.",
            "permission.effective.allow",
        )


def required_assistant_permission(message: str) -> str | None:
    """Classify deterministic assistant paths before they access private data."""

    normalized = "".join(
        character if character.isalnum() or character.isspace() else " "
        for character in message.casefold()
    ).split()
    text = " ".join(normalized)

    write_markers = ("remember ", "update my ", "change my ", "forget ")
    read_markers = (
        "what do you remember",
        "what are my goals",
        "what goals am i",
        "my preferences",
        "my routines",
    )
    context_markers = (
        "good morning",
        "brief me",
        "daily briefing",
        "what is my day like",
        "what does my day look like",
        "what should i focus on",
        "what do i have today",
        "show my context",
        "any reminders",
        "what needs my attention",
    )

    if any(marker in text for marker in read_markers):
        return Permission.MEMORY_READ_PRIVATE.value
    if any(marker in text for marker in write_markers):
        return Permission.MEMORY_WRITE_PRIVATE.value
    if any(marker in text for marker in context_markers):
        return Permission.CONTEXT_READ_PRIVATE.value
    if "smart home" in text or "sensor" in text:
        return Permission.SMART_HOME_READ.value
    return None


def _decision(
    request: AuthorizationRequest,
    result: str,
    reason: str,
    policy_id: str,
) -> AuthorizationDecision:
    return AuthorizationDecision(
        decision=result,
        reason=reason,
        permission=request.permission,
        policy_id=policy_id,
        risk_level=request.risk_level,
    )


authorization_service = AuthorizationService()
