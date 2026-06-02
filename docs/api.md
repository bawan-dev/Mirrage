# API

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
  "status": "planned",
  "listening": false,
  "wake_word": "not_configured",
  "speech_to_text": "not_configured",
  "text_to_speech": "not_configured"
}
```

### Notes

The first version should not try to access the microphone. It only needs to show where voice support will connect later.

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
  "model": null
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
  "model": null
}
```

### Notes

This routes the message through the AI service layer. With the default `stub`
provider it returns a fixed response; with a real provider it returns a model reply.

The active provider is selected with `MIRRAGE_AI_PROVIDER`:

- `stub` — fixed response, no network (default; used in development and CI)
- `ollama` — local, private model via an Ollama server
- `openai` — hosted, OpenAI-compatible model (set `MIRRAGE_AI_API_KEY`)

The response shape is identical for every provider, so the dashboard never changes.
If a provider fails, the endpoint still returns `200` with a short fallback reply so
the dashboard stays usable.

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
memory and redirects back to the frontend.

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
