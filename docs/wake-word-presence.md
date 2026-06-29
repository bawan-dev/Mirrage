# Wake Word And Presence Engine

Phase 31 adds a backend-owned assistant lifecycle and a wake-word adapter.

## What This Adds

- `AssistantStateManager` owns the global lifecycle state.
- `PresenceService` exposes snapshots, settings, and Server-Sent Events.
- `WakeWordService` validates wake detections against the configured phrase.
- `VoicePipeline` emits listening, processing, speaking, returning, idle, and
  sleeping transitions.
- The frontend subscribes with `EventSource` instead of polling.

## Privacy Model

Raw microphone audio should not be sent to Mirrage or any external provider
before the wake phrase is detected.

The intended production setup is:

```text
microphone audio
  -> local wake engine only
  -> detection event
  -> Mirrage backend
```

After wake detection, browser speech recognition currently handles the spoken
request. That part is still browser-dependent. A local speech-to-text service can
replace it later without changing the presence API.

## API Boundary

```text
GET    /api/presence/status
GET    /api/presence/events
GET    /api/presence/settings
PATCH  /api/presence/settings
POST   /api/presence/transition
POST   /api/wake-word/detect
```

The local wake engine should call:

```text
POST /api/wake-word/detect
```

with:

```json
{
  "phrase": "Hey Mirrage",
  "engine": "openwakeword",
  "confidence": 0.9
}
```

## Lifecycle

```text
sleeping
  -> idle
  -> wake_detected
  -> listening
  -> processing
  -> speaking
  -> returning_to_idle
  -> idle
```

The frontend should render these states. It should not invent its own primary
assistant lifecycle.

## Local Engine Notes

OpenWakeWord and Porcupine are the main candidates to test. Both should be run
as local processes. The first integration can be a small process that listens to
the microphone and calls the wake adapter endpoint.

Do not add a cloud wake-word provider as the default path.

## Current Limitation

This phase does not include a trained `Hey Mirrage` model asset. The adapter and
presence system are production-shaped, but a real local wake engine/model still
has to be installed and tested on the target machine.
