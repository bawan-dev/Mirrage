# Voice

Voice support is being added in layers. The current foundation is browser-based:
the assistant focus view can listen with push-to-talk, show the transcript, send
that transcript to the existing assistant endpoint, and speak the assistant reply
back through browser speech synthesis.

## Current State

Voice does not use a wake word yet.

What exists now:

- `GET /api/voice/status` returns the current voice status
- the dashboard reads that endpoint
- the assistant focus view has a push-to-talk control
- the browser asks for microphone permission on first use
- browser speech recognition turns speech into text
- the transcript is shown before it is sent
- the transcript is sent to `POST /api/assistant/message`
- the assistant response appears in the assistant focus view
- assistant responses can be spoken aloud with browser speech synthesis
- speech output can be muted
- the browser voice can be changed from the assistant settings panel

This is still a browser-based foundation. There is no wake word, no always-on
listening, and no backend/local speech engine yet.

## Status Fields

Current response shape:

```json
{
  "status": "planned",
  "listening": false,
  "wake_word": "not_configured",
  "speech_to_text": "not_configured",
  "text_to_speech": "not_configured"
}
```

Field meanings:

| Field | Meaning |
| --- | --- |
| `status` | Overall voice layer state |
| `listening` | Whether the system is actively listening |
| `wake_word` | Wake word setup state |
| `speech_to_text` | Speech-to-text setup state |
| `text_to_speech` | Text-to-speech setup state |

## Current Voice Flow

The current push-to-talk flow is:

```text
Assistant focus view
  -> Push to talk
  -> browser microphone permission
  -> browser speech recognition
  -> transcript shown in the UI
  -> assistant message endpoint
  -> assistant response
  -> response shown in the assistant focus view
  -> browser speech synthesis
  -> spoken assistant reply
```

The assistant endpoint did not need to change. Voice sends text into the same
route as typed messages, and browser speech synthesis reads the returned reply.

## Voice Architecture

Current architecture:

```text
Browser microphone
  -> Web Speech API
  -> React assistant focus view
  -> POST /api/assistant/message
  -> FastAPI backend
  -> AI provider layer
  -> assistant reply
  -> Browser SpeechSynthesis API
  -> device speaker
```

The backend still exposes voice status separately through `GET /api/voice/status`.
That endpoint describes the planned voice service state. Browser voice input and
output live in the frontend for now because they depend on browser microphone,
speaker, and speech API support.

## Browser Support

The first version uses browser speech APIs. Speech recognition works best in
Chromium-based browsers such as Chrome and Edge. Speech synthesis is more widely
available, but voice lists vary by browser and operating system.

If a browser does not support speech recognition, the assistant focus view keeps typed input available and shows a clear unsupported message.

If a browser does not expose speech synthesis, assistant replies still appear as
text. The mute and voice controls are disabled when speech output is not
available.

## Options To Research Later

These are possible options, not final decisions:

| Area | Possible Direction |
| --- | --- |
| Wake word | Local wake word detection |
| Speech-to-text | Local Whisper-style transcription or browser speech APIs |
| Text-to-speech | Browser speech output now, local/backend TTS later if needed |
| Device input | USB microphone or microphone array |
| Device output | Small speaker, monitor audio, or external speaker |

The first real choice should be based on the target device. A desktop browser, Raspberry Pi, and mini PC may need different audio setups.

## Not Built Yet

The project does not currently include:

- wake word detection
- always-on listening
- backend speech-to-text
- local Whisper-style transcription
- backend or local text-to-speech
- hardware speaker routing

Those pieces should come after browser voice input and output are stable.

## Next Step

The next useful voice step is to test browser compatibility and decide whether
speech-to-text or text-to-speech should stay browser-based or move into local
backend services.
