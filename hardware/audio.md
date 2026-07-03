# Audio

Mirrage needs audio output for assistant replies, alerts, and future media
features. The first build should favor reliability over hidden complexity.

## Options

| Option | Pros | Risks |
| --- | --- | --- |
| Built-in monitor speakers | No extra parts | Often weak, may be muffled inside frame |
| Small USB speakers | Reliable, simple power/data | Cable routing, may need mounting space |
| 3.5mm speakers | Simple and cheap | Separate power may be needed |
| Soundbar | Good sound, easy setup | Hard to hide, may look separate from mirror |
| Hidden stereo speakers | Cleaner finish | More frame planning and repair complexity |
| Surface transducers | Invisible sound source | Needs testing, can vibrate frame/mirror |
| Bluetooth speakers | No audio cable | Latency, pairing issues, battery/power reliability |

## Recommendation

Recommended first-build audio: **small wired USB speakers or compact 3.5mm
speakers hidden behind side/bottom vents**.

Why:

- reliable on boot
- no pairing step
- low latency
- easy to replace
- works with Linux mini PCs
- simpler than transducers or Bluetooth

Monitor speakers are acceptable for early testing, but they should not decide the
final audio plan.

## Mounting Notes

- Do not fully block speaker output behind sealed wood.
- Leave small side or bottom openings for sound.
- Keep speakers away from the microphone when possible.
- Add foam or rubber isolation if the frame vibrates.
- Make speakers replaceable without removing the mirror glass.

## Future Upgrades

- better hidden stereo speakers
- echo cancellation testing
- surface transducers if frame vibration is acceptable
- separate audio processing if wake-word and assistant voice need it

Do not claim high-quality or far-field audio until it has been tested inside the
actual frame.
