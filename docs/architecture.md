# Architecture

This document explains how Mirrage is planned to fit together.

## System Overview

Mirrage is split into layers instead of one large app. That keeps the dashboard, API, AI logic, voice work, and hardware planning separate enough to build safely over time.

![Mirrage architecture](../assets/diagrams/architecture.svg)

```text
User
  |
  v
Mirror Dashboard
  |
  v
Backend API
  |
  +-- AI Runtime
  |     +-- Context Builder
  |     +-- Provider Router
  |     +-- Local / Cloud Providers
  |
  +-- Local Memory Store
  |
  +-- Personal Context Layer
  |
  +-- Proactive Assistant Layer
  |
  +-- Calendar Integration
  |
  +-- Spotify Integration
  |
  +-- Smart Home Layer
  |
  +-- Local Wake Engine
  |
  +-- Voice Service
  |
  +-- Health, Logging, Backup, Startup Validation
  |
  +-- Hardware Status Layer
```

The frontend should ask for data. The backend should decide where that data comes
from. The AI runtime, context, memory, voice, and hardware layers should stay
behind backend boundaries so they can be replaced or upgraded later.

Production deployment is a separate operational layer. systemd and Docker keep
the services running, while the backend continues to own application behavior.

There is one current frontend-local exception: simple command routing. Mirrage
can recognize a small set of screen-navigation commands before calling the
assistant endpoint. Those commands turn into UI actions, such as opening the
weather, media, calendar, smart home, or assistant focus view. Normal assistant
messages still go to the backend.

## Folder Responsibilities

### `frontend/`

The frontend will hold the React + Vite smart mirror dashboard.

Its job:

- show the mirror interface
- display time, date, weather, assistant, voice, system, and hardware status
- provide optional Mirror Mode for a wall-mounted/kiosk display
- call backend endpoints when real data is available
- route simple screen-navigation commands into UI actions
- stay focused on presentation and user interaction

The frontend should not directly talk to AI providers or hardware devices.
Browser voice input/output and simple UI command routing are currently local
because they depend on browser APIs and screen state.

## Mirror Mode Boundary

Mirror Mode is a frontend display mode, enabled with `VITE_MIRROR_MODE=true`.
It does not add a new backend service or a new AI provider.

```text
same React app
  -> normal home state for desktop development
  -> Mirror Mode home state for wall display use
  -> shared focus views
```

Mirror Mode owns:

- ambient home layout
- startup service check overlay
- inactivity dimming and return-to-home behavior
- small burn-in movement for static UI elements
- assistant orb presentation states

The backend still owns health, weather, Calendar, Spotify, memory, and context
data. Mirror Mode only changes how that state is presented.

The current dimming behavior is a visual overlay. It does not control monitor
brightness or operating system power settings.

## Production Deployment Boundary

Production deployment is intentionally separate from product features.

```text
systemd
  -> docker compose -f docker-compose.prod.yml
  -> backend container
  -> frontend container
  -> persistent data, backups, logs
```

The production layer owns:

- startup on boot
- container restart policy
- service health checks
- persistent SQLite memory volume
- local backup volume
- backend log volume
- safe update and rollback workflow

The backend still owns service behavior. Docker and systemd only keep the
existing services running.

## Startup And Environment Boundary

The backend validates key settings during startup:

- log level
- memory database path
- backup directory
- weather coordinates
- wake-word sensitivity
- wake engine provider, sensitivity, model path, sample rate, frame size, and
  cooldown
- presence timeout
- AI provider names
- production CORS wildcard usage

Hard errors stop startup. Warnings are logged without stopping the service. This
keeps broken production configuration visible early instead of failing later in
the mirror UI.

### `backend/`

The backend will hold the FastAPI service.

Its job:

- expose API endpoints for the dashboard
- return health and system status
- receive assistant messages
- report voice status
- own the local wake engine lifecycle and wake detection cooldowns
- handle Google Calendar OAuth and Calendar API calls
- handle Spotify OAuth and Spotify Web API calls
- handle Home Assistant discovery and safe smart home actions
- aggregate daily context from weather, calendar, and memory
- generate local proactive summaries from the daily context layer
- store local memory for preferences, facts, goals, and routines
- provide clean boundaries for AI, context, memory, smart home, voice, and hardware features

The backend is the main coordination layer.

### `ai/`

The AI layer holds runtime, provider routing, and model-related code.

Its job:

- define a common interface for assistant responses
- build a small context bundle for normal model requests
- classify request types for conversation, summary, planning, memory, context, and future agent tasks
- select a provider and task-specific model
- route to `stub`, Ollama, OpenAI-compatible APIs, or future local models
- fall back safely when a provider is unavailable
- keep provider details away from the frontend

This lets Mirrage switch model providers without rewriting the dashboard.

## Calendar Boundary

Google Calendar is a backend integration. The frontend only calls Mirrage
endpoints.

```text
Calendar focus view
  -> Mirrage backend Calendar route
  -> Calendar service
  -> Google Calendar API
  -> normalized schedule response
  -> Calendar focus view
```

The backend owns:

- OAuth login and callback handling
- access token refresh
- today's schedule requests
- upcoming event requests
- translating Google event responses into dashboard-friendly JSON

The current token store is in process memory. That is enough for local,
single-user development, but a persistent encrypted token store should be added
before production deployment.

## Spotify Boundary

Spotify is a backend integration. The frontend only calls Mirrage endpoints.

```text
Media focus view
  -> Mirrage backend Spotify route
  -> Spotify service
  -> Spotify Web API
  -> normalized playback response
  -> Media focus view
```

The backend owns:

- OAuth login and callback handling
- access token refresh
- current playback requests
- play, pause, next, and previous actions
- translating Spotify responses into dashboard-friendly JSON

The current token store is in process memory. That is enough for local,
single-user development, but a persistent encrypted token store should be added
before production deployment.

## Smart Home Boundary

Smart home integration is backend-owned. The frontend only calls Mirrage
endpoints and never talks to Home Assistant directly.

```text
Smart Home focus view
  -> Mirrage backend smart home route
  -> SmartHomeService safety boundary
  -> HomeAssistantClient
  -> Home Assistant local API
  -> normalized Mirrage entity response
  -> Smart Home focus view
```

The current service supports only these phase-34 categories:

- low risk: `light`, `switch`, `scene`
- read only: `sensor`, plus Home Assistant `binary_sensor` normalized as sensor

High-risk and future categories such as `lock`, `cover`, `climate`,
`media_player`, `camera`, `alarm_control_panel`, `vacuum`, and `garage_door`
are blocked. The frontend cannot call arbitrary Home Assistant services by
name.

The assistant can be aware of smart home capability and the frontend can open
the Smart Home focus view, but free-form AI-driven device control is not enabled
yet. Any future device action should stay deterministic, permissioned, and
routed through the same service boundary.

More detail is in [smart-home.md](smart-home.md) and
[home-assistant.md](home-assistant.md).

### `docs/`

The docs folder explains the project.

Its job:

- describe architecture decisions
- track the roadmap
- document API behavior
- keep project decisions recorded

### `hardware/`

The hardware folder is for the physical mirror build.

Its job:

- document planned parts
- track display, frame, mirror, microphone, and sensor decisions
- keep hardware research separate from software implementation

### `assets/`

The assets folder is for project visuals.

Its job:

- store screenshots
- store diagrams
- store visual material used in docs or the README

## Planned Data Flow

The first real version should follow this path:

```text
React dashboard
  -> FastAPI endpoint
  -> backend service
  -> static or real data source
  -> JSON response
  -> dashboard card
```

Example:

```text
Dashboard voice card
  -> GET /api/voice/status
  -> voice service
  -> returns listening=false, status=planned
  -> frontend displays voice state
```

This keeps the dashboard simple. It asks for state and renders it. The backend owns the details.

## API Boundary

The backend API stays small and service-focused.

Core endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check that the backend is running |
| `GET` | `/api/health` | Production quick backend health |
| `GET` | `/api/health/full` | Full subsystem health for operations |
| `GET` | `/api/system/status` | Return basic system status |
| `GET` | `/api/voice/status` | Return voice service status |
| `POST` | `/api/assistant/message` | Send a message to the assistant layer |
| `GET` | `/api/context/daily` | Return provider-independent daily context |
| `GET` | `/api/proactive/summary` | Return a local proactive daily nudge |
| `GET` | `/api/smart-home/status` | Return smart home provider status |
| `GET` | `/api/smart-home/entities` | Return normalized safe smart home entities |
| `GET` | `/api/smart-home/sensors` | Return read-only smart home sensors |
| `POST` | `/api/smart-home/entities/{entity_id}/turn-on` | Turn on a supported light or switch |
| `POST` | `/api/smart-home/entities/{entity_id}/turn-off` | Turn off a supported light or switch |
| `POST` | `/api/smart-home/scenes/{entity_id}/activate` | Activate a supported scene |
| `GET` | `/api/memory/summary` | Return local memory grouped by type |
| `POST` | `/api/memory` | Create or update a local memory |
| `GET` | `/api/integrations/calendar/events/today` | Return today's schedule |

More endpoints can be added later, but each one should stay behind a clear
service boundary.

## AI Boundary

The AI runtime exposes one simple idea to the backend:

```text
input message -> context builder -> provider router -> assistant response
```

The backend should not care if the response comes from:

- a provider stub
- Ollama
- OpenAI
- another local model runtime

That detail belongs inside `ai/`.

Provider selection is controlled by `MIRRAGE_AI_PROVIDER`. Supported providers are
`stub` (default, no network), `ollama` (local and private), and `openai`
(hosted, OpenAI-compatible). All sit behind the same backend route, and a provider
failure degrades to a short fallback reply rather than an error page. See
[../ai/README.md](../ai/README.md) for details.

The runtime now adds a privacy-aware context builder:

```text
assistant request
  -> memory/context/proactive deterministic handlers first
  -> AI runtime for unknown model-backed requests
  -> local prompt or reduced cloud prompt
  -> selected provider
  -> fallback provider when needed
```

Local prompts can include selected memory details. Cloud prompts withhold raw
memory values and only pass reduced context. Private task types, such as memory,
planning, and future agent work, prefer local providers. `MIRRAGE_AI_LOCAL_ONLY`
prevents cloud provider selection.

Runtime status and provider capability endpoints are documented in
[api.md](api.md), and the runtime design is documented in
[ai-runtime.md](ai-runtime.md).

## Memory Boundary

Memory is a backend-owned local storage layer. It uses SQLite so the first
version can run privately on the user's machine without a hosted database.

```text
assistant memory command
  -> backend assistant route
  -> memory command parser
  -> SQLite memory store
  -> assistant response
```

The current memory types are:

| Type | Purpose |
| --- | --- |
| `preference` | User choices the assistant should remember |
| `fact` | Stable personal context |
| `goal` | Things the user is working toward |
| `routine` | Repeated habits or schedule patterns |

Memory commands are handled before a message reaches the AI provider. That is
intentional: storing and recalling personal context should stay local unless a
future feature clearly asks for model access.

The default database path is `data/mirrage-memory.sqlite3`. The database file is
ignored by Git, and Docker Compose mounts `./data` into the backend container so
memory can survive container restarts.

The first parser handles direct commands such as:

- `remember my favorite drink is coffee`
- `what do you remember about me?`
- `update my favorite drink to tea`

The memory API is documented in [api.md](api.md), and the design notes are in
[memory.md](memory.md).

## Context Boundary

The personal context layer is a backend service that aggregates existing sources
into one daily object.

```text
context focus view or assistant context prompt
  -> Mirrage backend context route
  -> weather service
  -> calendar service
  -> local memory service
  -> normalized daily context response
```

The context service currently uses:

- current weather summary
- today's Calendar events
- upcoming Calendar events
- local memory preferences
- local memory goals
- local memory routines

Each source has a fallback state. Weather can be unavailable, Calendar can be
unconfigured, and memory can be empty without breaking the whole response.

Context assistant replies are provider-independent. The backend generates a
short deterministic briefing locally before model provider routing. It does not
send the full context bundle or local memories to OpenAI, Ollama, or any other
provider in this phase.

More detail is in [context.md](context.md).

## Proactive Assistant Boundary

The proactive assistant layer sits on top of daily context. It does not call a
model provider.

```text
Mirror Mode home or proactive assistant prompt
  -> Mirrage backend proactive route
  -> daily context service
  -> deterministic priority, headline, message, and suggestions
```

The current proactive service looks for simple signals:

- a calendar event starting soon
- a busier-than-normal calendar day
- weather conditions that may affect plans
- the first active local goal
- otherwise the top daily context suggestion

The result is intentionally small: `priority`, `headline`, `message`,
`suggestions`, `sources`, and `should_interrupt`. Mirror Mode uses it as a quiet
home-screen nudge, and the assistant can answer prompts such as `Good morning`,
`Brief me`, or `What needs my attention?` with `provider: proactive`.

This is still privacy-first local logic. It does not send Calendar events or
memory records to OpenAI, Ollama, or another model provider. AI-enhanced
proactive summaries are future work and should stay behind an explicit opt-in.

More detail is in [proactive-assistant.md](proactive-assistant.md).

## Command Routing Boundary

The current command router lives in the frontend and handles only local UI
navigation. It takes assistant input, checks it against a small set of known
phrases, and returns an action object.

```text
assistant input
  -> intent router
  -> UI action
  -> focus view changes
```

Examples:

| Command | UI action |
| --- | --- |
| `What is the weather?` | Open Weather focus view |
| `Show my music` | Open Media focus view |
| `What is on my calendar today?` | Open Calendar focus view and summarize today's events |
| `daily briefing` | Open Context focus view and request a proactive backend briefing |
| `Good morning` | Open Context focus view and request a proactive backend briefing |
| `show my smart home devices` | Open Smart Home focus view |
| `show sensors` | Open Smart Home focus view |
| `Open assistant` | Open Assistant focus view |

If the router does not recognize a command, the message follows the normal
assistant path through `POST /api/assistant/message`.

This is documented in [command-routing.md](command-routing.md).

## Wake Word And Presence Boundary

Voice is split into a backend-owned lifecycle, a backend-owned local wake engine
boundary, and browser-owned speech capture.

The backend now owns:

- global assistant lifecycle state
- presence settings
- wake-word detection adapter endpoint
- local wake engine status, start/stop lifecycle, model path validation, and
  cooldown suppression
- Server-Sent Events for frontend subscriptions
- voice pipeline stage transitions

The frontend now listens to presence events instead of polling for assistant
state. When the backend emits `wake_detected`, the frontend opens Conversation
Mode and starts the existing browser speech-recognition path.

Current production-shaped flow:

```text
microphone
  -> local wake engine
  -> local model file
  -> WakeEngineService
  -> WakeWordService / cooldown check
  -> AssistantStateManager
  -> GET /api/presence/events stream
  -> frontend Conversation Mode
  -> browser speech recognition
  -> POST /api/assistant/message
  -> browser speech synthesis
  -> returning_to_idle
```

OpenWakeWord is the first implemented provider boundary. Porcupine remains a
possible future provider behind the same interface.

The repo does not include a trained or hardware-tested `Hey Mirrage` wake-word
model asset yet. A real model, microphone device, and false activation test
still need to be completed on the target machine.

The current voice plan is tracked in [voice.md](voice.md) and
[wake-word-presence.md](wake-word-presence.md). Wake engine setup is documented
in [wake-engine.md](wake-engine.md) and [openwakeword.md](openwakeword.md).

## Hardware Boundary

Hardware integration should also start as status only.

Early hardware state can include:

- display status
- microphone status
- sensor status
- mirror build status

The physical build should be documented before code depends on it.

## Operations Boundary

Operations features should not require the frontend to know about deployment.

```text
operator or Docker health check
  -> /api/health or /api/health/full
  -> backend health service
  -> subsystem checks
```

The full health check reports backend, environment, memory, AI runtime,
providers, presence, wake engine, weather, Calendar, Spotify, and smart home. It does not
expose secrets, OAuth tokens, Home Assistant tokens, transcripts, assistant
replies, or memory values.

Logging is structured JSON by default. Logs include safe operational fields such
as subsystem, event, state, provider, model, and integration name. Logs should
never include API keys, OAuth tokens, raw memory values, transcripts, or replies.

Backups are local-only. The backup utility uses SQLite's backup API for the
memory database and writes files under `backups/`. Cloud sync is future work and
should require explicit privacy design.

## What We Are Avoiding For Now

To keep the project clean, the first stages should avoid:

- direct frontend calls to AI providers
- hardware code before hardware decisions are documented
- external wake-word or speech providers before the local privacy boundary is clear
- large abstractions before the project needs them
- treating planned features as finished features

## First Implementation Target

The first working system should be simple:

1. React dashboard loads in the browser.
2. FastAPI backend runs locally.
3. Dashboard calls backend status endpoints.
4. Backend returns initial status data.
5. README and docs clearly explain what is real and what is planned.

That gives Mirrage a real full-stack foundation without pretending the advanced features are finished.
