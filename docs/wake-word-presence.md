# Wake Word And Presence Engine

Phase 31 added a backend-owned assistant lifecycle and a wake-word adapter.
Phase 35 adds the local wake engine boundary that can feed that same lifecycle.

## What This Adds

- `AssistantStateManager` owns the global lifecycle state.
- `PresenceService` exposes snapshots, settings, and Server-Sent Events.
- `WakeWordService` validates wake detections against the configured phrase.
- `WakeEngineService` owns local engine status, start/stop lifecycle, cooldowns,
  model path validation, and detection handoff.
- `OpenWakeWordEngine` is the first provider boundary.
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
GET    /api/wake-word/status
POST   /api/wake-word/start
POST   /api/wake-word/stop
POST   /api/wake-word/detect
```

An external local adapter can still call:

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

OpenWakeWord is the first local provider boundary prepared inside Mirrage. The
backend imports OpenWakeWord only when the engine is enabled and started, so CI
and normal local development do not need audio packages.

Porcupine remains a possible future provider behind the same service interface.

Do not add a cloud wake-word provider as the default path.

## Current Limitation

This phase does not include a trained or hardware-tested `Hey Mirrage` model
asset. The service boundary is production-shaped, but a real model and
microphone still have to be installed and tested on the target machine.

Setup notes are in [wake-engine.md](wake-engine.md) and
[openwakeword.md](openwakeword.md).
