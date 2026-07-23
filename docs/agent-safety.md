# Agent Safety

The agent framework is an orchestration layer behind the existing Mirrage trust
boundary. It is not a privileged AI process.

## Invariants

1. Every API request has an authenticated principal.
2. Every run belongs to its creator.
3. Every proposed tool must exist in the central registry.
4. Pydantic validates arguments before a plan is saved and again before a tool
   runs. Unknown fields are rejected rather than ignored.
5. Step descriptions are replaced with registry-owned safe descriptions before
   persistence or approval display.
6. Authorization is recalculated before every step. A later explicit deny wins.
7. Every side effect requires a pending approval to be decided by another user
   with `agents.approve`.
8. Expired, denied, cancelled, absent, or self-decided approvals cannot run.
9. Relationships and profile labels do not add permissions.
10. Smart-home tools still pass through the existing entity and domain safety
   checks.
11. Cancellation and runtime limits stop later steps.
12. Atomic run claims prevent duplicate planning and execution.
13. Approval decisions and event sequence allocation are serialized; only one
    concurrent approval decision can win.

## Capabilities Not Exposed

The registry contains no tool for:

- shell or Python execution
- arbitrary file reads or writes
- arbitrary URL fetches or live web browsing
- email, messaging, purchases, payments, bookings, or account changes
- identity, role, permission, trusted-device, profile, relationship, or privacy
  administration
- locks, alarms, cameras, garage doors, or raw Home Assistant services
- self-modification of code, prompts, policy, permissions, or tools

Unknown tool names are rejected before persistence or execution.

## Privacy

Agent planning and summaries are private AI Runtime task types and therefore
prefer local providers. Automatic daily context, memory summaries, proactive
context, and shared-context values are not added to agent planning prompts. The
planner receives the goal and safe tool descriptors.

Run goals, final results, and step arguments remain in the local identity
database and are visible through owner-scoped endpoints. Approvers see a safe
description, tool name, risk level, and expiry, not the full run or arguments.

Audit events record IDs, decisions, step numbers, tool names, and safe error
summaries. They omit tokens, raw prompts, tool arguments, memory values, and
Calendar content.

## Failure Behavior

- Invalid plans fail closed.
- Unknown tools and malformed arguments produce a validation error.
- Public plan failures use a generic safe error instead of storing validator or
  provider exception text.
- A failed tool stops the run.
- A timeout marks the current step and run failed.
- A denied approval fails the run and cancels remaining pending steps.
- Cancelling a run also cancels its pending approval records.
- Disabled agents leave all other Mirrage features available.

Thread-based timeout enforcement cannot forcibly terminate a provider call that
ignores its own timeout. Current registered network services already carry
their own request timeouts; side effects are never retried. Cancellation also
cannot undo a side effect that completed while its call was already in flight.
A process-isolated worker would be needed before adding less predictable tools.

## Operational Review

Before enabling agents:

1. Enforce identity mode.
2. Enrol separate trusted devices for requesters and approvers.
3. Review role defaults and explicit overrides.
4. Keep `MIRRAGE_AGENTS_ENABLED=false` until this setup is complete.
5. Start with read-only tasks.
6. Inspect `/api/health/full` and the agent event history.
7. Back up the identity database.
