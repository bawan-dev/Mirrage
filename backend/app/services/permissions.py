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

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": PERMISSION_REGISTRY,
    "family": frozenset(
        {
            *_PUBLIC,
            *_PERSONAL,
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
            Permission.MEDIA_READ.value,
            Permission.SMART_HOME_READ.value,
        }
    ),
    "guest": frozenset({*_PUBLIC, *_PERSONAL}),
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
