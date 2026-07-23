"""Central permission registry and conservative default role policy."""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    ASSISTANT_USE = "assistant.use"
    WEATHER_READ = "weather.read"
    SYSTEM_STATUS_READ = "system.status.read"
    HEALTH_FULL_READ = "health.full.read"
    MEDIA_READ = "media.read"
    MEDIA_CONTROL = "media.control"
    CALENDAR_READ_PRIVATE = "calendar.read_private"
    CONTEXT_READ_PRIVATE = "context.read_private"
    MEMORY_READ_PRIVATE = "memory.read_private"
    MEMORY_WRITE_PRIVATE = "memory.write_private"
    SMART_HOME_READ = "smart_home.read"
    SMART_HOME_CONTROL_LOW_RISK = "smart_home.control_low_risk"
    SMART_HOME_REQUEST_APPROVAL = "smart_home.request_approval"
    IDENTITY_USERS_READ = "identity.users.read"
    IDENTITY_USERS_MANAGE = "identity.users.manage"
    IDENTITY_DEVICES_READ = "identity.devices.read"
    IDENTITY_DEVICES_MANAGE = "identity.devices.manage"
    IDENTITY_ROLES_READ = "identity.roles.read"
    IDENTITY_PERMISSIONS_READ = "identity.permissions.read"
    APPROVALS_READ = "approvals.read"
    APPROVALS_MANAGE = "approvals.manage"
    AUDIT_READ = "audit.read"
    SYSTEM_ADMIN = "system.admin"
    PROFILE_READ_SELF = "profile.read_self"
    PROFILE_UPDATE_SELF = "profile.update_self"
    PROFILE_DIRECTORY_READ = "profile.directory.read"
    RELATIONSHIPS_READ = "relationships.read"
    RELATIONSHIPS_MANAGE = "relationships.manage"
    SHARED_CONTEXT_READ = "shared_context.read"
    SHARED_CONTEXT_MANAGE = "shared_context.manage"
    HUMAN_SESSION_MANAGE = "human_session.manage"
    AGENTS_USE = "agents.use"
    AGENTS_PLAN = "agents.plan"
    AGENTS_EXECUTE_READ_ONLY = "agents.execute_read_only"
    AGENTS_EXECUTE_LOW_RISK = "agents.execute_low_risk"
    AGENTS_READ_OWN = "agents.read_own"
    AGENTS_CANCEL_OWN = "agents.cancel_own"
    AGENTS_PAUSE_OWN = "agents.pause_own"
    AGENTS_RESUME_OWN = "agents.resume_own"
    AGENTS_APPROVE = "agents.approve"
    AGENTS_READ_HOUSEHOLD = "agents.read_household"
    AGENTS_ADMIN = "agents.admin"


PERMISSION_REGISTRY = frozenset(permission.value for permission in Permission)

_PUBLIC = {
    Permission.ASSISTANT_USE.value,
    Permission.WEATHER_READ.value,
    Permission.SYSTEM_STATUS_READ.value,
}

_PERSONAL = {
    Permission.PROFILE_READ_SELF.value,
    Permission.PROFILE_UPDATE_SELF.value,
    Permission.PROFILE_DIRECTORY_READ.value,
    Permission.RELATIONSHIPS_READ.value,
    Permission.RELATIONSHIPS_MANAGE.value,
    Permission.SHARED_CONTEXT_READ.value,
    Permission.SHARED_CONTEXT_MANAGE.value,
    Permission.HUMAN_SESSION_MANAGE.value,
}

_AGENT_SELF_SERVICE = {
    Permission.AGENTS_USE.value,
    Permission.AGENTS_PLAN.value,
    Permission.AGENTS_READ_OWN.value,
    Permission.AGENTS_CANCEL_OWN.value,
    Permission.AGENTS_PAUSE_OWN.value,
    Permission.AGENTS_RESUME_OWN.value,
}

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": PERMISSION_REGISTRY,
    "family": frozenset(
        {
            *_PUBLIC,
            *_PERSONAL,
            *_AGENT_SELF_SERVICE,
            Permission.AGENTS_EXECUTE_READ_ONLY.value,
            Permission.AGENTS_EXECUTE_LOW_RISK.value,
            Permission.MEDIA_READ.value,
            Permission.MEDIA_CONTROL.value,
            Permission.SMART_HOME_READ.value,
            Permission.SMART_HOME_CONTROL_LOW_RISK.value,
            Permission.SMART_HOME_REQUEST_APPROVAL.value,
        }
    ),
    "trusted_guest": frozenset(
        {
            *_PUBLIC,
            *_PERSONAL,
            *_AGENT_SELF_SERVICE,
            Permission.MEDIA_READ.value,
            Permission.SMART_HOME_READ.value,
        }
    ),
    "guest": frozenset({*_PUBLIC, *_PERSONAL, *_AGENT_SELF_SERVICE}),
    "service": frozenset(
        {
            Permission.SYSTEM_STATUS_READ.value,
        }
    ),
}


def permissions_for_role(role: str) -> frozenset[str]:
    """Return the immutable built-in permission set for a role."""

    return ROLE_PERMISSIONS.get(role, frozenset())


def is_registered_permission(permission: str) -> bool:
    return permission in PERMISSION_REGISTRY
