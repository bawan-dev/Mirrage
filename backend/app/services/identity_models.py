"""Typed models shared by Mirrage identity and safety services."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

IdentityRole = Literal["owner", "family", "trusted_guest", "guest", "service"]
IdentityStatus = Literal["active", "disabled"]
DeviceType = Literal[
    "mirror",
    "phone",
    "desktop",
    "tablet",
    "vehicle",
    "wearable",
    "room_node",
    "other",
]
DeviceStatus = Literal["active", "revoked", "pending"]
DeviceTrustLevel = Literal["limited", "trusted", "privileged"]
AuthenticationMethod = Literal[
    "anonymous",
    "development",
    "trusted_device",
    "future_multi_factor",
]
AssuranceLevel = Literal["anonymous", "low", "trusted_device", "strong"]
AuthorizationResult = Literal["allowed", "denied", "approval_required"]
RiskLevel = Literal["public", "read_only", "low", "medium", "high", "critical"]
ApprovalStatus = Literal["pending", "approved", "denied", "expired", "cancelled"]
PermissionEffect = Literal["grant", "deny"]


class IdentityUserCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=120)
    role: IdentityRole
    household_member: bool = True


class IdentityUserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: IdentityRole | None = None
    household_member: bool | None = None


class IdentityUserResponse(BaseModel):
    public_id: str
    display_name: str
    role: IdentityRole
    status: IdentityStatus
    household_member: bool
    created_at: str
    updated_at: str
    disabled_at: str | None


class PermissionOverrideRequest(BaseModel):
    permission: str = Field(..., min_length=1, max_length=120)
    effect: PermissionEffect


class PermissionOverrideResponse(BaseModel):
    user_id: str
    permission: str
    effect: PermissionEffect
    created_at: str
    updated_at: str


class TrustedDeviceCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=120)
    device_type: DeviceType = "other"
    trust_level: DeviceTrustLevel = "trusted"
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class TrustedDeviceResponse(BaseModel):
    public_id: str
    user_id: str
    display_name: str
    device_type: DeviceType
    trust_level: DeviceTrustLevel
    status: DeviceStatus
    created_at: str
    last_seen_at: str | None
    revoked_at: str | None
    metadata: dict[str, Any]


class TrustedDeviceEnrollmentResponse(BaseModel):
    device: TrustedDeviceResponse
    token: str
    message: str = "Store this token securely. Mirrage will not return it again."


class AuthenticatedPrincipal(BaseModel):
    user_id: str | None
    display_name: str
    role: IdentityRole | Literal["anonymous"]
    device_id: str | None
    authentication_method: AuthenticationMethod
    assurance_level: AssuranceLevel
    effective_permissions: frozenset[str] = Field(default_factory=frozenset)
    correlation_id: str
    device_trust_level: DeviceTrustLevel | None = None
    device_type: DeviceType | None = None
    human_session_id: str | None = None
    human_session_active: bool = False

    @property
    def authenticated(self) -> bool:
        return self.authentication_method != "anonymous" and self.user_id is not None


class IdentityPrincipalResponse(BaseModel):
    authenticated: bool
    user_id: str | None
    display_name: str
    role: str
    device_id: str | None
    authentication_method: AuthenticationMethod
    assurance_level: AssuranceLevel
    permissions: list[str]
    correlation_id: str
    device_type: DeviceType | None
    human_session_active: bool
    human_session_id: str | None


class IdentityStatusResponse(BaseModel):
    enabled: bool
    mode: str
    database_status: str
    active_user_count: int
    owner_present: bool
    active_device_count: int
    pending_approval_count: int
    audit_status: str
    message: str


class RolePermissionsResponse(BaseModel):
    role: IdentityRole
    permissions: list[str]


class PermissionRegistryResponse(BaseModel):
    permissions: list[str]


class AuthorizationRequest(BaseModel):
    permission: str
    resource_type: str = "api"
    resource_id: str | None = None
    risk_level: RiskLevel = "read_only"
    context: dict[str, Any] = Field(default_factory=dict)


class AuthorizationDecision(BaseModel):
    decision: AuthorizationResult
    reason: str
    permission: str
    policy_id: str
    risk_level: RiskLevel
    approval_id: str | None = None


class ApprovalCreateRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=160)
    resource_type: str = Field(..., min_length=1, max_length=120)
    resource_id: str | None = Field(default=None, max_length=200)
    risk_level: RiskLevel
    reason: str = Field(..., min_length=1, max_length=500)


class ApprovalDecisionRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class ApprovalResponse(BaseModel):
    public_id: str
    requester_user_id: str
    requester_device_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    risk_level: RiskLevel
    status: ApprovalStatus
    reason: str
    requested_at: str
    expires_at: str
    decided_at: str | None
    decided_by_user_id: str | None
    decision_reason: str | None
    correlation_id: str


class ApprovalListResponse(BaseModel):
    items: list[ApprovalResponse]
    count: int


class AuditEventResponse(BaseModel):
    public_id: str
    timestamp: str
    event_type: str
    actor_user_id: str | None
    actor_role: str | None
    device_id: str | None
    authentication_method: str | None
    action: str | None
    resource_type: str | None
    resource_id: str | None
    authorization_decision: str | None
    risk_level: str | None
    reason: str | None
    result: str | None
    correlation_id: str | None
    metadata: dict[str, Any]


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    count: int
    limit: int
    offset: int
