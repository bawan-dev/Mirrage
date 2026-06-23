# Proactive Assistant

The proactive assistant is a small local layer that decides whether Mirrage
should quietly surface something on the mirror home screen.

It is not a model provider. It does not call OpenAI, Ollama, Spotify, Google, or
any external AI service. It reads the backend daily context object and returns a
simple structured nudge.

## Endpoint

```text
GET /api/proactive/summary
```

Response shape:

```json
{
  "status": "ready",
  "generated_at": "2026-06-23T09:00:00+00:00",
  "priority": "medium",
  "headline": "Weather may affect plans",
  "message": "14 C and rain in London.",
  "suggestions": ["Open Weather", "Plan around the forecast"],
  "sources": ["context", "weather", "calendar", "memory"],
  "should_interrupt": false
}
```

## How It Decides

The first version uses simple rules:

- `high`: a calendar event starts within about 30 minutes
- `medium`: the day is busy, weather needs attention, or a saved goal exists
- `low`: there is a light useful nudge, such as a clear day for focused work
- `none`: nothing needs attention or context could not be loaded

`should_interrupt` is only true for the near-calendar-event case. Mirror Mode can
use that later for a more visible prompt, but the current UI keeps it subtle.

## Assistant Prompts

These prompts are answered locally by the proactive service before model
provider routing:

- `Good morning`
- `Brief me`
- `Give me my daily briefing`
- `What should I know today?`
- `What should I focus on?`
- `Any reminders?`
- `What needs my attention?`

The assistant response uses:

```json
{
  "provider": "proactive",
  "context_action": "proactive"
}
```

## Frontend Use

Mirror Mode reads `/api/proactive/summary` on load. The home screen shows the
headline and message as a lower-right nudge. The Context focus view also shows
the latest proactive briefing above the normal daily context panels.

If the endpoint is unavailable, the frontend falls back to the existing context
summary text.

## Privacy Boundary

The proactive layer reads already-normalized backend context. It does not send
calendar events, memories, routines, goals, or preferences to an external model.

If AI-enhanced proactive summaries are added later, they should be opt-in and
document exactly which sources can be included.

## Current Limits

- The scoring is simple and rule-based.
- There is no notification history yet.
- The UI does not yet let the user tune what counts as important.
- Spotify playback is not part of proactive context yet.
- Wake word and always-listening behavior are not built.
