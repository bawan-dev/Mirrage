# Microphones

The microphone choice will decide whether wake word and voice interaction feel
natural or frustrating.

The first physical build should make microphone testing easy. Do not hide the
microphone permanently until wake-word reliability is proven.

## Options

| Option | Pros | Risks |
| --- | --- | --- |
| Basic USB microphone | Cheap, simple | Weak far-field performance |
| USB conference microphone | Designed for room voice, reliable USB | Larger, visible unless mounted carefully |
| Microphone array | Better directionality potential | Driver and Linux support vary |
| ReSpeaker-style array | Common maker option, beamforming potential | Needs testing and setup |
| Webcam microphone | Easy if webcam already exists | Not ideal placement or quality |
| Laptop/mini-PC microphone | No extra hardware | Usually poor placement behind mirror |
| Far-field microphone hardware | Best target for voice-first mirror | More expensive, more integration work |

## Recommendation

Recommended first-build microphone: **wired USB conference microphone or USB mic
array mounted near the bottom edge of the frame**.

Why:

- more reliable than a tiny hidden mic
- easier Linux compatibility than exotic hardware
- easy to move during testing
- can be replaced without rebuilding the mirror
- better chance of working with wake-word tests

## Placement Notes

- Start with the microphone visible or semi-hidden near the bottom edge.
- Do not place it directly behind thick mirror material without testing.
- Keep it away from speakers where possible.
- Leave access to the USB cable.
- Test with normal room noise, TV audio, music, and people speaking nearby.

## Wake-Word Testing

Real reliability is not proven until testing includes:

- actual phrase: `Hey Mirrage`
- similar phrases
- silence
- music
- TV/background speech
- normal conversation
- repeated wake attempts during cooldown

See [testing-checklist.md](testing-checklist.md) and
[../docs/wake-engine.md](../docs/wake-engine.md).

## Future Upgrades

- far-field microphone array
- beamforming
- echo cancellation
- multiple room microphones
- backend/local speech-to-text

Do not assume far-field voice will work until tested in the actual room.
