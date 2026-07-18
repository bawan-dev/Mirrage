# OpenWakeWord Notes

OpenWakeWord is the first local wake engine boundary prepared for Mirrage.

It is a good first choice because it is local-first and open-source friendly.
Mirrage imports OpenWakeWord only when the local wake engine is enabled and
started, so CI and normal development do not need the package installed.

## What Mirrage Expects

Mirrage expects a local model file path:

```text
MIRRAGE_WAKE_ENGINE_MODEL_PATH=models/wake/hey-mirrage.onnx
```

That file is not included in the repository. A real `Hey Mirrage` model still
needs to be trained or generated and tested on target hardware.

## Python Packages

The production device will need packages similar to:

```bash
pip install openwakeword sounddevice numpy
```

Exact package versions should be pinned after the first successful hardware
test. They are not in `backend/requirements.txt` yet because the default backend
must keep working without an audio stack.

## Device Setup

Check available input devices with the audio tooling on the target OS. Then set:

```text
MIRRAGE_WAKE_ENGINE_MICROPHONE=0
```

or the device name if the runtime supports it reliably.

If the microphone fails to open, Mirrage should keep the backend online and show
the wake engine error in:

```text
GET /api/wake-word/status
GET /api/health/full (owner bearer token required)
```

## Honest Current Limitation

The OpenWakeWord provider boundary is implemented. A real trained model and
microphone run have not been verified by this code change.

The next real-world step is:

1. train or obtain a `Hey Mirrage` OpenWakeWord model
2. copy it to `models/wake/hey-mirrage.onnx`
3. install the optional OpenWakeWord/audio packages on the target machine
4. enable `MIRRAGE_WAKE_ENGINE_ENABLED=true`
5. run the false activation checklist in [wake-engine.md](wake-engine.md)

## Porcupine Alternative

Porcupine remains a possible future provider. It should be added behind the same
`WakeEngineService` boundary rather than replacing the Presence Engine or the
adapter endpoint.
