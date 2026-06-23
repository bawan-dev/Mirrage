# Personal Context System

Mirrage now has a backend-owned context layer. It gathers the pieces that matter
for a daily briefing and returns one structured response.

This phase is deliberately provider-independent. Context answers are generated
by deterministic backend logic, not by OpenAI, Ollama, or another model provider.
The proactive assistant layer also reads this context, but it still stays local.

## What Context Uses

The daily context service reads from existing backend services:

| Source | Used for |
| --- | --- |
| Weather | Current local condition and temperature |
| Calendar | Today's events and a small upcoming-event window |
| Memory | Preferences, goals, routines, and fact count |

Current endpoint:

```text
GET /api/context/daily
```

The assistant route also handles daily-context prompts locally:

```text
POST /api/assistant/message
```

Examples:

- `What is my day like?`
- `What goals am I working on?`

Some attention-style prompts, such as `Good morning`, `Brief me`, and
`What should I focus on today?`, now go through the proactive assistant layer
first. They still use the same backend context sources.

## Fallback Behavior

Each source has its own status. One failure should not break the whole context
response.

Examples:

- If weather is unavailable, context still returns calendar and memory.
- If Calendar is not configured, context says so instead of failing.
- If local memory is empty, context returns an empty memory state.
- If local memory cannot be loaded, context returns `memory.status: unavailable`.

The top-level context status is:

| Status | Meaning |
| --- | --- |
| `ready` | Core sources loaded cleanly |
| `partial` | Some sources loaded, some fell back |
| `unavailable` | All context sources failed |

## Privacy Boundary

Context is assembled in the backend.

```text
assistant message
  -> context command check
  -> daily context service
  -> deterministic text response
```

For this phase, Mirrage does not send the full context bundle or local memories
to a model provider. If AI-enhanced briefings are added later, that should be a
separate feature with clear settings and documentation.

## Frontend

The frontend has a `context` focus view. It shows:

- today's overview
- weather status
- calendar summary
- local goals
- routines and preferences
- suggested focus items
- the latest proactive briefing when available

The view reads from `/api/context/daily`. It does not call Google Calendar,
Open-Meteo, or the local memory database directly.

## Current Limits

- Context text is simple and rule-based.
- The context view does not edit memory yet.
- Spotify is not part of daily context yet.
- Calendar token persistence is still separate future work.
- AI-enhanced context summaries are intentionally not enabled yet.

See [proactive-assistant.md](proactive-assistant.md) for the small nudge layer
that sits on top of daily context.
