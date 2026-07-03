# Wake Engine

Mirrage now has a backend-owned boundary for a local wake-word engine.

The important privacy rule is simple: microphone audio should stay inside the
local wake engine until the phrase is detected. Mirrage receives a detection
event, not raw pre-wake audio.

## Current Status

Implemented:

- provider-independent wake engine service
- OpenWakeWord provider boundary
- configurable wake phrase, sensitivity, model path, microphone, sample rate,
  frame size, and cooldown
- background listener lifecycle that does not block FastAPI
- status, start, stop, and detect endpoints
- integration with the existing Presence Engine
- health monitoring and tests that run without a real microphone or model

Still required on real hardware:

- install OpenWakeWord and audio dependencies
- create or install a real `Hey Mirrage` model file
- choose the microphone device
- run false activation and latency tests in the room where the mirror will live

Do not claim hands-free wake word is production-ready until that hardware test
passes.

## Runtime Flow

```text
microphone
  -> local wake engine
  -> local model file
  -> wake detected
  -> WakeEngineService
  -> WakeWordService
  -> AssistantStateManager
  -> Server-Sent Event
  -> Mirror frontend Conversation Mode
  -> browser speech recognition
  -> assistant endpoint
  -> browser speech synthesis
```

Backend speech-to-text is not part of this phase. After wake detection, the
frontend still uses browser speech recognition for the spoken request.

## Configuration

Default local development keeps the engine off:

```text
MIRRAGE_WAKE_ENGINE_ENABLED=false
MIRRAGE_WAKE_ENGINE_PROVIDER=openwakeword
MIRRAGE_WAKE_ENGINE_MODEL_PATH=
MIRRAGE_WAKE_ENGINE_PHRASE=Hey Mirrage
MIRRAGE_WAKE_ENGINE_SENSITIVITY=0.5
MIRRAGE_WAKE_ENGINE_MICROPHONE=
MIRRAGE_WAKE_ENGINE_SAMPLE_RATE=16000
MIRRAGE_WAKE_ENGINE_FRAME_MS=80
MIRRAGE_WAKE_ENGINE_COOLDOWN_SECONDS=3
```

Suggested model location:

```text
models/wake/hey-mirrage.onnx
```

The `models/` folder is ignored by Git except for `.gitkeep` placeholders. Do
not commit large model files.

## API

```text
GET  /api/wake-word/status
POST /api/wake-word/start
POST /api/wake-word/stop
POST /api/wake-word/detect
```

`/api/wake-word/status` returns safe runtime state:

- enabled
- configured
- provider
- phrase
- sensitivity
- microphone configured
- model configured
- running
- cooldown
- last detection time
- last detection latency
- error message

It does not return raw audio or the model path.

## Manual Checks

Status:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/wake-word/status
```

Expected when disabled:

```text
enabled: false
status: disabled
running: false
```

Adapter path:

```powershell
$body = @{ phrase = "Hey Mirrage"; engine = "manual-test"; confidence = 0.9 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/wake-word/detect" -Method Post -ContentType "application/json" -Body $body
```

Expected:

- response state is `wake_detected`
- frontend enters Conversation Mode through the existing presence event stream

Cooldown:

```powershell
$body = @{ phrase = "Hey Mirrage"; engine = "manual-test"; confidence = 0.9 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/wake-word/detect" -Method Post -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/wake-word/detect" -Method Post -ContentType "application/json" -Body $body
```

Expected: the second request may return `429` during the cooldown window.

## False Activation Checklist

Run this on the target device after a real model and microphone are configured.

Test:

- silence for 10 minutes
- normal conversation near the mirror
- TV or podcast audio in the same room
- music at normal room volume
- similar phrases such as `hey mirror`, `hey mirage`, and `okay Mirrage`
- the actual phrase: `Hey Mirrage`
- repeated `Hey Mirrage` attempts inside the cooldown window

Record:

- number of false wakes
- detection delay after the real phrase
- whether the frontend opened Conversation Mode
- whether cooldown suppressed duplicate detections
- room noise conditions
- microphone device and sensitivity value

## Sensitivity

Mirrage normalizes sensitivity as `0.0` to `1.0`.

- lower values are more likely to wake
- higher values are stricter

Start at `0.5`, then adjust after real-room testing. Do not tune based only on a
quiet desk test.

## Health

`GET /api/health/full` includes `wake_engine`.

Disabled wake engine is healthy because push-to-talk and the adapter path still
work. Enabled but missing model or microphone setup is reported as degraded or
unavailable depending on the state.

## Production Notes

For direct Linux host use, the target device needs:

- microphone visible to the OS
- user permission for the audio device
- OpenWakeWord runtime dependencies
- model file stored outside Git
- stable sample rate, usually `16000`

Docker microphone access is host-specific. Linux deployments may need ALSA,
PulseAudio, or PipeWire device mounts. That is not fully solved in this phase;
the recommended first hardware test is running the backend directly on the host.

See [openwakeword.md](openwakeword.md) for the provider-specific setup notes.
