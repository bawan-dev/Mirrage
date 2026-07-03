# Mirror Mode

Mirror Mode is the kiosk-style display mode for Mirrage. It is meant for a wall
mounted screen where the interface is viewed from a few feet away, not for daily
desktop development.

Normal development mode is still the default.

## Enable It

Create or edit `frontend/.env`:

```text
VITE_MIRROR_MODE=true
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Then start the frontend:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

With Docker:

```powershell
$env:VITE_MIRROR_MODE="true"
docker compose up --build
```

## What Changes

Mirror Mode replaces the normal development home screen with an ambient home
state:

- large time and date in the top-left
- weather summary in the top-right
- assistant presence line in the center/lower area
- lower-right proactive nudge from the backend context layer
- quiet word controls for Assistant, Weather, Context, Calendar, and Media

The existing focus views still work:

- Weather
- Assistant
- Media
- Calendar
- Context

Press `Close` or `Esc` to return home.

For demos and screenshots, a focus view can also be opened directly:

```text
http://127.0.0.1:5173/?view=weather
http://127.0.0.1:5173/?view=assistant
http://127.0.0.1:5173/?view=calendar
http://127.0.0.1:5173/?view=context
http://127.0.0.1:5173/?view=media
```

## Assistant Presence States

The center presence reflects the current assistant state:

| State | Meaning |
| --- | --- |
| `Idle` | assistant is ready |
| `Listening` | browser speech recognition is listening |
| `Thinking` | an assistant request is being handled |
| `Speaking` | browser text-to-speech is speaking |
| `Error` | backend, voice, or assistant error is visible |

This is still browser-based speech recognition and speech output after wake. The
backend wake engine boundary exists, but a real local model and microphone still
need hardware testing.

## Inactivity

Mirror Mode tracks simple activity:

- mouse movement
- click or tap
- keyboard press
- wheel/scroll
- voice button actions

The display dims after the first timeout and returns to the ambient home state
after the second timeout.

Default values:

```text
VITE_MIRROR_DIM_TIMEOUT_SECONDS=60
VITE_MIRROR_SLEEP_TIMEOUT_SECONDS=120
```

The dimming is visual only. It does not turn off the monitor.

## Phase 30A Visual Direction

The current Mirror Mode UI intentionally avoids dashboard cards, panel grids,
and admin-style widgets. Most information is placed directly on the mirror
surface with typography, spacing, and subtle motion.

The goal is for the display to stay mostly empty until a focus view is needed.

## Burn-In Protection

Static elements gently shift by a few pixels over time in Mirror Mode:

- clock/date
- weather block
- assistant presence
- status text

Default:

```text
VITE_MIRROR_BURN_IN_SHIFT_SECONDS=45
```

This is a first software-level guard. A real installation should also use normal
display settings, brightness control, and panel-specific burn-in precautions.

## Startup Sequence

On load, Mirror Mode briefly shows a startup screen with service checks for:

- backend
- weather
- voice
- calendar
- smart home
- context
- proactive summary

The startup sequence does not block forever. It fades out after the configured
time even if a service is still checking or unavailable.

Default:

```text
VITE_MIRROR_STARTUP_SECONDS=3
```

## Current Limitations

- Local wake engine support is prepared, but no trained and hardware-tested
  `Hey Mirrage` model is included.
- Smart home controls are limited to backend-approved lights, switches, scenes,
  and read-only sensors.
- No computer vision.
- No new AI model is added by Mirror Mode.
- Proactive nudges are rule-based local summaries, not model-generated advice.
- Dimming is an overlay, not hardware brightness control.
- Burn-in protection is light UI movement, not a guarantee for every display.
