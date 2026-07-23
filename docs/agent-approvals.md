# Agent Approvals

Agent side effects use the existing identity approval table. An agent does not
have a private approval mechanism.

## Flow

```text
validated side-effect step
  -> approval row with resource_type=agent_step
  -> run waits
  -> separately authorized user reviews safe description
  -> approved / denied / expired
  -> executor checks the decision again
```

The approval stores the run-linked step ID, registered tool name, risk level,
safe description, requester, device, correlation ID, and expiry. It does not
store raw arguments. The safe description comes from the backend tool registry,
not AI- or client-supplied plan prose.

Approval decisions use an atomic database transition. If two approvers act at
the same time, one decision succeeds and the other receives a conflict; a later
request cannot replace the first decision.

## Separation Of Duties

`agents.approve` is not granted to guests. The requester cannot decide an
approval whose resource type is `agent_step`, even if that requester otherwise
has approval permissions. A second authorized person is required.

This means a household with one owner cannot execute agent side effects by
default. The owner can still use read-only agents or perform the existing
direct application action under its normal policy. Do not weaken the
self-approval rule to avoid this constraint.

## Expiry And Cancellation

Agent approval TTL is configured separately through
`MIRRAGE_AGENT_APPROVAL_TTL_SECONDS`, defaulting to 300 seconds. The executor
rejects expired or missing decisions. Cancelling a run cancels its pending
approval records. A decision that races with cancellation cannot make the
cancelled run executable. A denied decision fails the run, cancels the other
pending approval records, and prevents later steps from executing. Run expiry
also expires attached pending approvals and cancels unfinished steps.

## API

Authorized approvers use:

- `GET /api/agents/approvals`
- `POST /api/agents/approvals/{approval_id}/approve`
- `POST /api/agents/approvals/{approval_id}/deny`

The decision response contains only approval, run, and step IDs plus the
decision. It does not return the other user's goal, plan arguments, or result.
