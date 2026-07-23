# Approvals

The approval store establishes a generic workflow for future medium- and
high-risk actions. It does not make locks, alarms, garage doors, cameras, covers,
vacuums, or arbitrary Home Assistant calls available.

```text
pending -> approved
        -> denied
        -> cancelled by requester
        -> expired after TTL
```

Requests record the authenticated requester, trusted device when available,
action, resource, risk, reason, expiry, and correlation ID. Decisions record the
authorized reviewer and decision reason.

Rules:

- an authenticated principal can create a request
- `approvals.manage` is required to approve or deny
- only the requester can cancel
- only pending, unexpired requests can be decided
- approval does not grant a permission the requester lacks
- approval does not override a global safety block
- each lifecycle change is audited

The default TTL is 120 seconds through `MIRRAGE_APPROVAL_TTL_SECONDS`.

## Agent Steps

Every agent side effect creates an approval with
`resource_type=agent_step`. Agent approvals use the separate
`MIRRAGE_AGENT_APPROVAL_TTL_SECONDS` setting, default 300 seconds.

The requester cannot approve their own agent step. A second authenticated user
with `agents.approve` must decide it. Expired approvals cannot execute, denied
approvals fail the run, and cancelling a run cancels its pending approvals.

Approvers receive a safe description, tool name, risk, run and step IDs, and
expiry. The approval queue does not expose the other user's complete goal or
tool arguments. See [agent-approvals.md](agent-approvals.md).

## Relationship Consent Is Separate

Relationship proposals do not use the approval engine. The named counterpart
must accept or reject directly, and either participant may later archive the
relationship. An owner cannot approve a relationship on another user's behalf.

This separation matters because an approval is authorization for an action,
while a relationship is mutual personal context. Neither mechanism grants a
role permission by itself.

See [API](api.md) for endpoint details and [Security model](security-model.md)
for the authorization boundary.
