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

For now, this returns a fixed response through the AI service layer. The provider is named `stub` because no local or remote model is connected yet.

## First Backend Target

The first backend version should be able to:

- start locally with FastAPI
- return JSON from all four endpoints
- keep route code separate from service logic
- avoid real AI, voice, and hardware dependencies until their layers are ready
