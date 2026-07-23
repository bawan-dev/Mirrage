# Agent Framework

Mirrage can run small, persistent tasks made from registered backend tools. The
framework is deliberately bounded: it does not provide a shell, Python
execution, filesystem access, unrestricted HTTP requests, or an open-ended
background worker.

## Request Flow

```text
Authenticated goal
  -> persistent user-owned run
  -> structured plan proposal
  -> backend tool and argument validation
  -> permission decision for every step
  -> separate approval for every side effect
  -> one registered tool at a time
  -> safe result and event history
  -> completed, paused, failed, cancelled, or expired
```

The AI Runtime may propose JSON plan steps and summarize safe results. It cannot
authorize a tool, approve an action, or call a tool. If the configured provider
does not return valid JSON, Mirrage uses a narrow deterministic planner.

## Modules

| Module | Responsibility |
| --- | --- |
| `models.py` | Typed run, step, tool, event, and approval schemas |
| `registry.py` | Central allow-list and tool metadata |
| `planner.py` | AI proposal and deterministic fallback planning |
| `policy.py` | Tool, argument, agent-type, and permission validation |
| `executor.py` | Time-limited sequential execution and retries |
| `tools.py` | Calls existing Calendar, memory, profile, and smart-home services |
| `store.py` | SQLite persistence and owner-scoped reads |
| `events.py` | Persistent safe events and bounded SSE delivery |
| `service.py` | Run lifecycle, approvals, audit, pause, resume, and cancellation |

The framework reuses the Identity and Safety Engine. There is no separate agent
authentication or authorization system.

## Persistent State

Identity schema version 3 adds:

- `agent_runs`
- `agent_steps`
- `agent_events`

Runs retain the user goal and final result in the local identity database.
Steps retain typed arguments because approved work must survive a restart.
Descriptions are replaced with the registered tool's backend-owned description
before persistence, so model- or client-supplied prose is not exposed to an
approver.
The research organizer stores a fixed `run_goal` source reference rather than
copying the full supplied text into a step argument.
Agent API reads are owner-scoped. Events and audit records contain safe progress
descriptions rather than raw arguments, Calendar details, memory values, or
prompts.

The identity backup contains all three tables and restore validation checks that
they are present.

## Agent Types

- **Planning** combines safe internal reads into a bounded result.
- **Memory** searches owner-private memory and can request approval for one
  permanent memory or private shared-context write.
- **Calendar** reads today or upcoming events. It cannot edit Calendar data.
- **Smart home** reads supported entities and can request approval for an
  existing low-risk light, switch, or scene action.
- **Research** organizes user-supplied text. It has no live web tool.

## Limits

Each run has a maximum step count and an expiry. Execution checks the configured
runtime limit, per-tool timeout, retry policy, cancellation state, current
permissions, and approval state. Side-effect tools are not retried.
When a run expires, its unfinished steps are cancelled and attached pending
approvals are expired in the same local database cleanup.

Mirrage does not run an infinite queue. Starting or resuming a run performs one
bounded execution request. Planning and execution use atomic database claims so
two requests cannot plan or start the same run concurrently. Event sequence
numbers and active-run admission are serialized in SQLite.

A run can stop between steps when another request pauses or cancels it. An
already-running service call cannot be forcibly terminated; cancellation keeps
the run terminal and prevents later steps or final completion from replacing
that state.

## Clarification

The planner returns `awaiting_user_input` when an important target is missing.
For example, a smart-home write without an exact entity ID is not guessed. The
current API preserves the clarification prompt; a dedicated answer-and-replan
endpoint is planned.

## Current Status

Mirrage supports bounded, permission-controlled agent runs with structured
planning, registered tools, approval gates, resource limits, cancellation,
persistence, and audit logs.

Open-ended autonomy, unrestricted web research, arbitrary computer control,
purchases, messaging, bookings, and security-critical actions remain disabled.
