# Roles And Permissions

Roles provide a conservative baseline. Per-user overrides can grant or deny a
registered permission, but an explicit deny always wins. Overrides cannot unlock
globally blocked smart-home domains.

## Built-In Policy

| Capability | Owner | Family | Trusted guest | Guest | Service |
| --- | --- | --- | --- | --- | --- |
| Basic assistant, weather, system status | Yes | Yes | Yes | Yes | System status only |
| Media read | Yes | Yes | Yes | No | No |
| Media control | Yes | Yes | No | No | No |
| Smart-home read | Yes | Yes | Yes | No | No |
| Low-risk light/switch/scene control | Yes | Yes | No | No | No |
| Private Calendar, context, memory | Yes | No | No | No | No |
| Own profile and relationships | Yes | Yes | Yes | Yes | No |
| Shared-context read and management | Yes | Yes | Yes | Yes | No |
| Start/end own mirror interaction session | Yes | Yes | Yes | Yes | No |
| User/device management | Yes | No | No | No | No |
| Approval decisions and audit read | Yes | No | No | No | No |

Family and guest privacy is conservative by default. A future household policy
editor can make intentional grants without changing the central registry.

## Registered Keys

```text
assistant.use
weather.read
system.status.read
health.full.read
media.read
media.control
calendar.read_private
context.read_private
memory.read_private
memory.write_private
profile.read_self
profile.update_self
profile.directory.read
relationships.read
relationships.manage
shared_context.read
shared_context.manage
human_session.manage
smart_home.read
smart_home.control_low_risk
smart_home.request_approval
identity.users.read
identity.users.manage
identity.devices.read
identity.devices.manage
identity.roles.read
identity.permissions.read
approvals.read
approvals.manage
audit.read
system.admin
```

Permission strings live in `backend/app/services/permissions.py`; route code does
not invent new keys. Unknown permissions are denied.

These keys authorize API operations, not data visibility. For example,
`profile.directory.read` permits a directory request, but the relationship and
privacy layer still removes every field the requester is not allowed to see.
The `owner` role does not override that filter.

## Overrides

Owners can set an explicit grant or deny through:

```text
PUT /api/identity/users/{user_id}/permissions
```

The request body is:

```json
{
  "permission": "media.control",
  "effect": "deny"
}
```

Override changes are audited. Granting a permission to the same authenticated
actor is rejected as self-escalation. The final active owner cannot be demoted or
disabled.
