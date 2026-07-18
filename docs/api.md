# API

## Authentication

Public endpoints do not require a token. Protected endpoints require a trusted
device bearer token:

```http
Authorization: Bearer <DEVICE_TOKEN>
```

The backend resolves the token to an active user and device, creates an
authenticated principal, then checks a central permission and risk policy. A
frontend-supplied name, role, or user ID is never accepted as authentication.

Common responses:

- `401`: no valid authenticated principal
- `403`: authenticated but denied by permission or safety policy
- `409`: the policy requires approval or the requested identity state conflicts
- `422`: invalid request or identity policy input

## Identity And Safety Endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/identity/status` | Public, safe summary | Identity store mode and counts |
| `GET` | `/api/identity/me` | Authenticated | Current principal, assurance, effective permissions |
| `GET` | `/api/identity/roles` | `identity.roles.read` | Built-in role policy |
| `GET` | `/api/identity/permissions` | `identity.permissions.read` | Registered permission keys |
| `GET` | `/api/identity/users` | `identity.users.read` | Safe household user list |
| `POST` | `/api/identity/users` | Owner | Create user |
| `GET` | `/api/identity/users/{id}` | `identity.users.read` | Safe user detail |
| `PATCH` | `/api/identity/users/{id}` | Owner | Update name, role, or household flag |
| `POST` | `/api/identity/users/{id}/disable` | Owner | Disable user and revoke devices |
| `PUT` | `/api/identity/users/{id}/permissions` | Owner | Set explicit grant or deny |
| `GET` | `/api/identity/devices` | `identity.devices.read` | Safe device list, no token material |
| `POST` | `/api/identity/devices` | Owner | Enroll device; raw token returned once |
| `GET` | `/api/identity/devices/{id}` | `identity.devices.read` | Safe device detail |
| `POST` | `/api/identity/devices/{id}/revoke` | Owner | Revoke device token |
| `GET` | `/api/approvals` | `approvals.read` | List/filter approvals |
| `POST` | `/api/approvals` | Authenticated | Create expiring request |
| `POST` | `/api/approvals/{id}/approve` | `approvals.manage` | Approve pending request |
| `POST` | `/api/approvals/{id}/deny` | `approvals.manage` | Deny pending request |
| `POST` | `/api/approvals/{id}/cancel` | Requester | Cancel pending request |
| `GET` | `/api/audit/events` | `audit.read` | Paginated, filtered audit events |

Token hashes and prefixes are internal storage fields and are not API response
fields.

## Protected Existing Routes

- `health.full.read`: `/api/health/full`
- `assistant.use`: assistant message and stream routes
- `context.read_private`: daily context and proactive summaries
- `memory.read_private` / `memory.write_private`: all memory routes
- `calendar.read_private`: Calendar status and event reads
- `media.read` / `media.control`: Spotify state and player controls
- `smart_home.read`: status, entities, and sensors
- `smart_home.control_low_risk`: lights, switches, and scenes
- `system.admin`: presence settings and wake engine start/stop

OAuth callbacks remain public protocol endpoints. They do not return private
Calendar or Spotify payloads.

Mirrage will start with a small backend API. The first endpoints should support the dashboard without pulling in AI, voice, or hardware complexity too early.

Base URL for local development:

```text
http://localhost:8000
```

## Response Style

Responses should be JSON.

Status fields should use short lowercase values where possible, for example:

- `online`
- `planned`
- `not_configured`
- `error`

The first backend version can return static data. Live data can replace it later without changing the dashboard shape.

## Frontend Display Modes

The API does not change between normal dashboard mode and Mirror Mode. Mirror
Mode is enabled in the frontend with `VITE_MIRROR_MODE=true` and still reads the
same backend routes for health, weather, voice, Calendar, Spotify, smart home,
memory, and daily context.

Mirror Mode should not require a new backend endpoint unless a future hardware
brightness or display-control service is added.

## `GET /health`

Checks whether the backend is running.

### Example Response

```json
{
  "status": "online",
  "service": "mirrage-api"
}
```

### Notes

This endpoint should stay simple. It is for quick checks from the browser, terminal, Docker, or future monitoring.

## `GET /api/health`

Production quick health endpoint. It returns the same simple backend status as
`/health` and is safe for Docker health checks.

### Example Response

```json
{
  "service": "mirrage-api",
  "status": "online"
}
```

## `GET /api/health/full`

Returns subsystem health for operations and troubleshooting.

### Example Response

```json
{
  "service": "mirrage-api",
  "status": "degraded",
  "generated_at": "2026-07-01T12:00:00+00:00",
  "checks": [
    {
      "name": "backend",
      "status": "ok",
      "message": "Backend process is running.",
      "details": null
    },
    {
      "name": "memory",
      "status": "ok",
      "message": "Memory database is healthy.",
      "details": {
        "database_path": "data/mirrage-memory.sqlite3",
        "record_count": 0
      }
    }
  ]
}
```

### Notes

Full health includes backend, environment, memory, AI runtime, providers,
presence, wake engine, weather, Calendar, Spotify, and smart home. Optional integration
issues return `warning` and make the top-level status `degraded`; they do not
mean the backend is down.

The response does not expose API keys, OAuth tokens, Home Assistant tokens, or
memory values.

## `GET /api/system/status`

Returns the current high-level system state.

### Example Response

```json
{
  "status": "online",
  "frontend": "planned",
  "backend": "online",
  "ai": "planned",
  "voice": "planned",
  "hardware": "planned"
}
```

### Notes

This endpoint will feed the system status card in the dashboard. Early values can be static. Later, this can include real service checks.

## `GET /api/voice/status`

Returns the current voice layer state.

### Example Response

```json
{
  "status": "ready",
  "listening": false,
  "wake_word": "enabled",
  "wake_phrase": "Hey Mirrage",
  "wake_word_engine": "adapter",
  "wake_word_mode": "local_adapter",
  "local_wake_engine": "disabled",
  "local_wake_engine_provider": "openwakeword",
  "sensitivity": 0.55,
  "microphone_device": null,
  "presence_state": "idle",
  "speech_to_text": "browser_after_wake",
  "text_to_speech": "browser_synthesis"
}
```

### Notes

The backend owns voice presence state. The browser still handles speech
recognition and speech synthesis until a local speech engine is added.

## `GET /api/presence/status`

Returns the current assistant lifecycle snapshot.

### Example Response

```json
{
  "state": "idle",
  "previous_state": null,
  "event": "startup",
  "sequence": 0,
  "wake_phrase": "Hey Mirrage",
  "wake_word_enabled": true,
  "wake_word_engine": "adapter",
  "transcript": null,
  "interim_transcript": null,
  "assistant_reply": null,
  "source": "presence_service",
  "message": "Assistant presence is idle.",
  "updated_at": "2026-06-29T10:00:00+00:00"
}
```

## `GET /api/presence/events`

Streams presence snapshots with Server-Sent Events.

Frontend uses this endpoint to subscribe to `sleeping`, `idle`,
`wake_detected`, `listening`, `processing`, `speaking`, and
`returning_to_idle` without polling.

## `GET /api/presence/settings`

Returns wake and presence configuration.

## `PATCH /api/presence/settings`

Updates in-process wake and presence settings.

### Example Request

```json
{
  "wake_phrase": "Hey Mirrage",
  "sensitivity": 0.65,
  "automatic_sleep": true
}
```

## `POST /api/presence/transition`

Allows the frontend voice pipeline to report lifecycle stages such as
`listening`, `speaking`, and `returning_to_idle`.

## `POST /api/wake-word/detect`

Wake-word adapter endpoint for a local engine.

### Example Request

```json
{
  "phrase": "Hey Mirrage",
  "engine": "openwakeword",
  "confidence": 0.9
}
```

### Notes

Raw wake-word audio should stay inside the local wake engine. Mirrage receives
only the detection event.

Repeated detections inside the configured cooldown window can return `429` so a
local model cannot spam presence events.

## `GET /api/wake-word/status`

Returns safe local wake engine state.

### Example Response

```json
{
  "enabled": false,
  "configured": false,
  "provider": "openwakeword",
  "phrase": "Hey Mirrage",
  "sensitivity": 0.5,
  "microphone_device": null,
  "microphone_configured": false,
  "model_configured": false,
  "running": false,
  "status": "disabled",
  "sample_rate": 16000,
  "frame_ms": 80,
  "cooldown_seconds": 3.0,
  "last_detection_time": null,
  "last_detection_latency_ms": null,
  "error_message": null,
  "message": "Local wake engine is disabled. Push-to-talk and adapter detection still work."
}
```

The response does not expose raw audio, secrets, or the model file path.

## `POST /api/wake-word/start`

Starts the local wake engine when enabled and configured.

If the engine is disabled, missing a model file, or missing optional audio
packages, the backend stays online and returns a clear status instead of
crashing.

## `POST /api/wake-word/stop`

Stops the local wake engine background worker.

More detail: [wake-engine.md](wake-engine.md) and
[openwakeword.md](openwakeword.md).

## `GET /api/info/weather`

Returns current local weather from Open-Meteo (no API key required).

### Example Response

```json
{
  "status": "online",
  "location": "Auckland",
  "temperature_c": 16.9,
  "condition": "Overcast",
  "updated": "2026-05-31T08:00"
}
```

### Notes

The location is configured with `MIRRAGE_WEATHER_LATITUDE`,
`MIRRAGE_WEATHER_LONGITUDE`, and `MIRRAGE_WEATHER_LOCATION`. Responses are cached for
a few minutes. If the upstream service is unavailable, the endpoint serves the last
good value, or returns `status: "unavailable"` with a null temperature, so the
dashboard never breaks.

## `POST /api/assistant/message`

Sends a message to the assistant layer.

### Example Request

```json
{
  "message": "What is on my schedule today?"
}
```

### Example Response

```json
{
  "reply": "Assistant routing is ready, but no model is connected yet.",
  "provider": "stub",
  "model": null,
  "memory_action": null,
  "context_action": null
}
```

### Manual Test

```powershell
$body = @{ message = "hello" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected response:

```json
{
  "reply": "Assistant routing is ready, but no model is connected yet.",
  "provider": "stub",
  "model": null,
  "memory_action": null,
  "context_action": null
}
```

### Notes

This routes unknown messages through the AI runtime. With the default `stub`
provider it returns a fixed response; with a real provider it returns a model
reply.

Local memory commands are handled before the AI provider is called. For example,
`remember my favorite drink is coffee` stores a local memory and returns
`provider: "memory"`.

Daily context commands are also handled before the AI provider is called. For
example, `What is my day like?` returns `provider: "context"` and uses the
backend context service.

Proactive briefing commands are handled locally before the AI provider is
called. For example, `Good morning`, `Brief me`, and `What needs my attention?`
return `provider: "proactive"` and use the backend proactive service.

Smart home awareness commands are handled locally before the AI provider is
called. For example, `show my smart home devices` and `show sensors` return
`provider: "smart_home"` from the backend. The frontend command router can open
the Smart Home focus view for the same phrases.

The active provider is selected with `MIRRAGE_AI_PROVIDER`:

- `stub` — fixed response, no network (default; used in development and CI)
- `ollama` — local, private model via an Ollama server
- `openai` — hosted, OpenAI-compatible model (set `MIRRAGE_AI_API_KEY`)

The response shape is identical for every provider, so the dashboard never changes.
If a provider fails, the endpoint still returns `200` with a short fallback reply so
the dashboard stays usable.

Unknown messages now pass through the AI runtime. The runtime builds a small
privacy-aware context, chooses a provider, selects a task model when configured,
and falls back if the selected provider fails. Direct memory, context, and
proactive commands still run through deterministic local handlers before the
runtime.

## AI Runtime

### `GET /api/ai/runtime/status`

Returns safe runtime settings. It does not expose API keys.

Example response:

```json
{
  "runtime_mode": "standard",
  "configured_provider": "stub",
  "fallback_provider": "stub",
  "local_first": false,
  "local_only": false,
  "streaming_enabled": true,
  "privacy_mode": "limited_cloud_context",
  "available_providers": ["ollama", "openai", "stub"],
  "default_task_model": null,
  "summary_model": null,
  "planning_model": null
}
```

Manual test:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/ai/runtime/status
```

### `GET /api/ai/providers`

Returns provider capabilities without secrets.

Example response:

```json
{
  "providers": [
    {
      "name": "stub",
      "kind": "local",
      "configured": true,
      "supports_streaming": false,
      "default_model": null
    }
  ]
}
```

Manual test:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/ai/providers
```

### `POST /api/assistant/stream`

Returns assistant output as Server-Sent Events. Providers do not expose true
token streaming yet, so the route currently emits one response chunk while
keeping the streaming API shape ready.

Manual test:

```powershell
$body = @{ message = "hello" } | ConvertTo-Json
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/assistant/stream" -Method Post -ContentType "application/json" -Body $body
```

Expected response text includes:

```text
event: status
event: chunk
event: done
```

More detail: [ai-runtime.md](ai-runtime.md).

## Context

The context API returns a provider-independent daily briefing object assembled by
the backend.

### `GET /api/context/daily`

Combines:

- current weather
- today's calendar events
- upcoming calendar events
- local memory preferences
- local memory goals
- local memory routines
- suggested focus items

Example response:

```json
{
  "status": "partial",
  "date": "2026-06-22",
  "generated_at": "2026-06-22T09:00:00+00:00",
  "weather": {
    "status": "online",
    "location": "London",
    "temperature_c": 18.2,
    "condition": "Partly cloudy",
    "summary": "18 C and partly cloudy in London.",
    "updated": "2026-06-22T09:00:00+01:00",
    "message": "Weather loaded."
  },
  "calendar": {
    "status": "not_authenticated",
    "authenticated": false,
    "today_event_count": 0,
    "upcoming_event_count": 0,
    "today_events": [],
    "upcoming_events": [],
    "message": "Calendar is configured but not connected."
  },
  "memory": {
    "status": "empty",
    "preferences": [],
    "goals": [],
    "routines": [],
    "facts_count": 0,
    "message": "No local memories are stored yet."
  },
  "suggested_focus": [
    {
      "title": "Keep the day light",
      "reason": "No calendar items or local goals are available yet.",
      "source": "context",
      "priority": "low"
    }
  ],
  "message": "Daily context loaded with one or more fallback states."
}
```

Status values:

| Field | Values |
| --- | --- |
| top-level `status` | `ready`, `partial`, `unavailable` |
| `weather.status` | `online`, `unavailable`, or provider status |
| `calendar.status` | `ready`, `not_configured`, `not_authenticated`, `unavailable` |
| `memory.status` | `ready`, `empty`, `unavailable` |

### Assistant Context Test

```powershell
$body = @{ message = "What is my day like?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected response includes:

```json
{
  "provider": "context",
  "context_action": "daily"
}
```

More detail: [context.md](context.md).

## Proactive Assistant

The proactive API returns a small daily nudge assembled from the backend context
service. It is deterministic local logic, not a model response.

### `GET /api/proactive/summary`

Example response:

```json
{
  "status": "ready",
  "generated_at": "2026-06-23T09:00:00+00:00",
  "priority": "medium",
  "headline": "Finish mirror prototype",
  "message": "Finish the wall-mounted prototype.",
  "suggestions": ["Ask what should I focus on", "Open Context"],
  "sources": ["context", "weather", "calendar", "memory"],
  "should_interrupt": false
}
```

Priority values currently used:

| Priority | Meaning |
| --- | --- |
| `high` | A calendar event starts soon and the UI may interrupt gently |
| `medium` | Something is worth noticing, such as weather, a busy day, or a goal |
| `low` | A useful calm nudge is available |
| `none` | Nothing needs attention or context could not be loaded |

If context fails unexpectedly, the route still returns `200` with
`status: "unavailable"` and a clear fallback message.

### Assistant Proactive Test

```powershell
$body = @{ message = "Good morning" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected response includes:

```json
{
  "provider": "proactive",
  "context_action": "proactive"
}
```

More detail: [proactive-assistant.md](proactive-assistant.md).

## Smart Home

Smart home integration is isolated behind backend endpoints. The frontend does
not call Home Assistant directly.

Supported domains for this phase:

- `light`
- `switch`
- `scene`
- `sensor`

Home Assistant `binary_sensor` entities are normalized as read-only sensors.
High-risk or future domains such as `lock`, `cover`, `climate`,
`media_player`, `camera`, `alarm_control_panel`, `vacuum`, and `garage_door`
are blocked.

### `GET /api/smart-home/status`

Returns whether smart home support is enabled, configured, reachable, and how
many supported entities were discovered.

Example disabled response:

```json
{
  "enabled": false,
  "configured": false,
  "provider": "home_assistant",
  "connection_status": "disabled",
  "entity_count": 0,
  "supported_domains": ["light", "switch", "scene", "sensor"],
  "last_successful_sync": null,
  "message": "Smart home control is disabled."
}
```

### `GET /api/smart-home/entities`

Discovers and returns normalized safe entities.

Example response:

```json
{
  "status": "ready",
  "provider": "home_assistant",
  "items": [
    {
      "entity_id": "light.kitchen",
      "name": "Kitchen Light",
      "domain": "light",
      "device_type": "light",
      "state": "off",
      "available": true,
      "room": "Kitchen",
      "friendly_name": "Kitchen Light",
      "supported_actions": ["turn_on", "turn_off"],
      "last_updated": "2026-07-02T09:00:00+00:00"
    }
  ],
  "count": 1,
  "message": "1 smart home entities loaded."
}
```

### `GET /api/smart-home/entities/{entity_id}`

Returns one normalized entity if it is in a supported domain.

### `GET /api/smart-home/sensors`

Returns read-only sensors. This includes normalized `sensor` and
`binary_sensor` entities.

### Control Endpoints

| Method | Endpoint | Allowed domains |
| --- | --- | --- |
| `POST` | `/api/smart-home/entities/{entity_id}/turn-on` | `light`, `switch` |
| `POST` | `/api/smart-home/entities/{entity_id}/turn-off` | `light`, `switch` |
| `POST` | `/api/smart-home/scenes/{entity_id}/activate` | `scene` |

Example:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/smart-home/entities/light.kitchen/turn-on" -Method Post
```

Expected response:

```json
{
  "status": "ok",
  "message": "Kitchen Light turn on.",
  "entity": {
    "entity_id": "light.kitchen",
    "name": "Kitchen Light",
    "domain": "light",
    "device_type": "light",
    "state": "on",
    "available": true,
    "room": "Kitchen",
    "friendly_name": "Kitchen Light",
    "supported_actions": ["turn_on", "turn_off"],
    "last_updated": "2026-07-02T09:00:00+00:00"
  }
}
```

Sensors are read-only. Unsupported and high-risk domains return a safe error
instead of reaching Home Assistant.

### Blocked Arbitrary Services

The backend intentionally rejects arbitrary Home Assistant service calls:

```text
POST /api/smart-home/services/{domain}/{service}
```

This endpoint exists only as a guardrail and returns `403`.

More detail: [smart-home.md](smart-home.md) and
[home-assistant.md](home-assistant.md).

## Memory

Memory is stored locally in SQLite. The backend owns the database and the
assistant memory commands.

Default database path:

```text
data/mirrage-memory.sqlite3
```

### `GET /api/memory`

Lists local memories.

Optional query parameters:

| Parameter | Example | Purpose |
| --- | --- | --- |
| `kind` | `preference` | Filter by `preference`, `fact`, `goal`, or `routine` |
| `q` | `coffee` | Search memory keys and values |
| `status` | `active` | Filter by `active`, `archived`, or `done` |

Example response:

```json
{
  "items": [
    {
      "id": 1,
      "kind": "preference",
      "key": "favorite drink",
      "value": "coffee",
      "status": "active",
      "source": "assistant",
      "created_at": "2026-06-21T20:00:00+00:00",
      "updated_at": "2026-06-21T20:00:00+00:00"
    }
  ],
  "count": 1
}
```

### `GET /api/memory/summary`

Returns memories grouped by type.

### `POST /api/memory`

Creates or updates a memory with the same `kind` and `key`.

Example request:

```json
{
  "kind": "preference",
  "key": "temperature unit",
  "value": "celsius"
}
```

### `PATCH /api/memory/{memory_id}`

Updates an existing memory.

Example request:

```json
{
  "value": "fahrenheit",
  "status": "active"
}
```

### Assistant Memory Test

```powershell
$body = @{ message = "remember my favorite drink is coffee" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected response includes:

```json
{
  "provider": "memory",
  "memory_action": "stored"
}
```

Then check recall:

```powershell
$body = @{ message = "what do you remember about me?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected response includes `favorite drink: coffee`.

More detail: [memory.md](memory.md).

## Calendar Integration

Google Calendar is isolated behind backend endpoints. The frontend does not call
Google directly.

### `GET /api/integrations/calendar/status`

Returns whether Google Calendar credentials are configured and whether the
backend has an active OAuth token.

### `GET /api/integrations/calendar/login`

Starts Google OAuth by redirecting the browser to Google.

### `GET /api/integrations/calendar/callback`

Receives Google's OAuth callback. On success, the backend stores the token in
process memory and redirects back to the frontend.

### `GET /api/integrations/calendar/events/today`

Returns today's schedule for the configured calendar.

Example response:

```json
{
  "status": "ready",
  "authenticated": true,
  "date": "2026-06-02",
  "time_zone": "Europe/London",
  "events": [
    {
      "id": "event-1",
      "title": "Design review",
      "start": "2026-06-02T09:30:00+01:00",
      "end": "2026-06-02T10:00:00+01:00",
      "is_all_day": false,
      "location": "Studio",
      "calendar": "Mirrage",
      "html_link": "https://calendar.google.com/event?eid=1"
    }
  ],
  "updated": "2026-06-02T12:00:00+00:00",
  "message": "1 event found."
}
```

### `GET /api/integrations/calendar/events/upcoming`

Returns upcoming events. The optional `days` query parameter defaults to `7` and
is capped by the backend.

Google Calendar uses a read-only events scope for this phase. See
[calendar.md](calendar.md) for setup.

## Spotify Integration

Spotify is isolated behind backend endpoints. The frontend does not call Spotify
directly.

### `GET /api/integrations/spotify/status`

Returns whether Spotify credentials are configured and whether the backend has an
active OAuth token.

### `GET /api/integrations/spotify/login`

Starts Spotify OAuth by redirecting the browser to Spotify.

### `GET /api/integrations/spotify/callback`

Receives Spotify's OAuth callback. On success, the backend stores the token in
process memory and redirects back to the frontend.

### `GET /api/integrations/spotify/player/currently-playing`

Returns the current playback state.

Example response:

```json
{
  "status": "playing",
  "authenticated": true,
  "is_playing": true,
  "title": "Night Drive",
  "artist": "Mirrage Test",
  "album": "Mirror Sessions",
  "artwork_url": "https://example.com/cover.jpg",
  "progress_ms": 42000,
  "duration_ms": 180000,
  "device_name": "Office speaker",
  "device_type": "Computer",
  "spotify_url": "https://open.spotify.com/track/1",
  "updated": "2026-06-02T12:00:00+00:00",
  "message": "Spotify playback loaded."
}
```

### Player Control Endpoints

| Method | Endpoint |
| --- | --- |
| `POST` | `/api/integrations/spotify/player/play` |
| `POST` | `/api/integrations/spotify/player/pause` |
| `POST` | `/api/integrations/spotify/player/next` |
| `POST` | `/api/integrations/spotify/player/previous` |

Playback controls require Spotify authorization, an active Spotify device, and a
Spotify account that can use player controls. See [spotify.md](spotify.md) for
setup.

## First Backend Target

The first backend version should be able to:

- start locally with FastAPI
- return JSON from the core endpoints
- keep route code separate from service logic
- avoid real AI, voice, and hardware dependencies until their layers are ready
