# Voice And Presence

Voice is now split into two layers:

- the backend-owned presence engine
- browser-based speech recognition and speech synthesis

The presence engine tracks the assistant lifecycle even when the browser is the
piece handling microphone capture.

## Current State

What exists now:

- `GET /api/voice/status` reports voice and wake-word readiness
- `GET /api/presence/status` returns the current assistant lifecycle state
- `GET /api/presence/events` streams lifecycle changes with Server-Sent Events
- `PATCH /api/presence/settings` updates wake/presence configuration in memory
- `POST /api/wake-word/detect` accepts detection events from a local wake engine
- the frontend subscribes to presence events instead of polling
- wake detection moves the UI into Conversation Mode
- listening, processing, speaking, returning, idle, and sleeping states are shown
- push-to-talk still works as a fallback

## Important Limitation

Mirrage does not ship a trained wake-word model file yet.

The backend is ready for a local engine such as OpenWakeWord or Porcupine to call
`POST /api/wake-word/detect` after it hears the configured phrase. Until a local
engine/model is installed, wake detection can be tested by calling that endpoint
manually.

There is also an optional browser wake listener behind:

```text
VITE_EXPERIMENTAL_BROWSER_WAKE_WORD=true
```

Leave it off by default. Browser speech recognition may use browser or operating
system services, so it is not the privacy-first production path.

## Presence States

```text
sleeping
idle
wake_detected
listening
processing
speaking
returning_to_idle
```

The frontend treats the backend presence snapshot as the primary state source.
Local browser voice state is only a fallback if the backend is unavailable.

## Wake Word Flow

Production path:

```text
local wake engine
  -> hears "Hey Mirrage"
  -> POST /api/wake-word/detect
  -> backend emits wake_detected
  -> frontend receives SSE event
  -> browser starts speech recognition
  -> transcript goes to assistant route
  -> assistant response is spoken
  -> backend returns to idle
```

Wake audio should stay inside the local wake engine. Mirrage receives only the
detection event.

## Configuration

Backend:

```text
MIRRAGE_WAKE_WORD_ENABLED=true
MIRRAGE_WAKE_PHRASE="Hey Mirrage"
MIRRAGE_WAKE_WORD_ENGINE=adapter
MIRRAGE_WAKE_WORD_SENSITIVITY=0.55
MIRRAGE_VOICE_MICROPHONE_DEVICE=
MIRRAGE_PRESENCE_INACTIVITY_TIMEOUT_SECONDS=25
MIRRAGE_PRESENCE_AUTOMATIC_SLEEP=true
```

Frontend:

```text
VITE_EXPERIMENTAL_BROWSER_WAKE_WORD=false
```

## Manual Test

Start backend and frontend, then run:

```powershell
$body = @{ phrase = "Hey Mirrage"; engine = "manual-test"; confidence = 0.9 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/wake-word/detect" -Method Post -ContentType "application/json" -Body $body
```

Expected result:

- backend returns `state: wake_detected`
- frontend receives the presence event
- Assistant focus opens
- browser asks for microphone permission if needed
- transcript is sent through the existing assistant endpoint

## Supported Wake Engines

Planned local engines:

| Engine | Notes |
| --- | --- |
| OpenWakeWord | Local, open source, good candidate for Linux mini PC/Raspberry Pi testing |
| Porcupine | Local engine, strong performance, usually needs generated keyword assets |
| Custom adapter | Any local process can call `/api/wake-word/detect` after local detection |

No external audio streaming should happen before wake detection.
