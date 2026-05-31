# Voice

Voice support is being added in layers. The current foundation is browser push-to-talk: the assistant focus view can ask for microphone permission, use browser speech recognition, show the transcript, and send that transcript to the existing assistant endpoint.

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

This is still a browser-based foundation. There is no wake word, no always-on listening, and no text-to-speech yet.

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
```

The assistant endpoint did not need to change. Voice sends text into the same route as typed messages.

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
```

The backend still exposes voice status separately through `GET /api/voice/status`. That endpoint describes the planned voice service state. Browser push-to-talk lives in the frontend for now because it depends on browser microphone permission and browser speech recognition support.

## Browser Support

The first version uses the browser Web Speech API. It works best in Chromium-based browsers such as Chrome and Edge.

If a browser does not support speech recognition, the assistant focus view keeps typed input available and shows a clear unsupported message.

## Options To Research Later

These are possible options, not final decisions:

| Area | Possible Direction |
| --- | --- |
| Wake word | Local wake word detection |
| Speech-to-text | Local Whisper-style transcription or browser speech APIs |
| Text-to-speech | Local TTS engine or browser speech output |
| Device input | USB microphone or microphone array |
| Device output | Small speaker, monitor audio, or external speaker |

The first real choice should be based on the target device. A desktop browser, Raspberry Pi, and mini PC may need different audio setups.

## Not Built Yet

The project does not currently include:

- wake word detection
- always-on listening
- spoken assistant responses
- backend speech-to-text
- local Whisper-style transcription
- local text-to-speech

Those pieces should come after the push-to-talk flow is stable.

## Next Step

The next useful voice step is to decide whether speech-to-text should stay browser-based or move into a local backend service.
