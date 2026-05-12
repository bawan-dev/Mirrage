# Voice

Voice support will be added in layers. The first layer is status only: the backend reports what is planned or configured, and the dashboard shows that state clearly.

## Current State

Voice is not listening to the microphone yet.

What exists now:

- `GET /api/voice/status` returns the current voice status
- the dashboard reads that endpoint
- the voice card shows whether the system is listening
- wake word, speech-to-text, and text-to-speech are marked as not configured

This gives the project a real place for voice work without adding audio complexity too early.

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

## Planned Voice Flow

The planned voice flow is:

```text
Wake word
  -> speech-to-text
  -> assistant message endpoint
  -> assistant response
  -> text-to-speech
  -> dashboard and speaker output
```

The assistant endpoint already exists, so voice can eventually send text into the same backend route instead of creating a separate assistant path.

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

- microphone access
- wake word detection
- speech recording
- live transcription
- spoken assistant responses
- audio permissions handling

Those pieces should come after the dashboard, backend, and assistant route are stable.

## Next Step

The next useful voice step is to keep the current status endpoint stable and later add a real voice service module when microphone work begins.
