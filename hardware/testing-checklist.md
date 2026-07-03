# Hardware Testing Checklist

Use this before permanent wall mounting.

## Display And Mirror

- [ ] Mirrage UI is visible without mirror material.
- [ ] UI is visible through mirror material in daytime light.
- [ ] UI is visible through mirror material at night.
- [ ] Reflection looks acceptable with screen off.
- [ ] Reflection looks acceptable with screen on.
- [ ] Text is readable from normal viewing distance.
- [ ] Viewing angles are acceptable.
- [ ] Brightness is not maxed out just to be usable.

## Thermal

- [ ] 1 hour heat test passed.
- [ ] 4 hour heat test passed.
- [ ] Display back is warm but not concerning.
- [ ] Mini PC is not throttling or crashing.
- [ ] Power bricks are not trapped in a sealed cavity.
- [ ] Top and bottom ventilation are clear.
- [ ] Cables are not touching hot surfaces.

## Network And Software

- [ ] Ethernet works, or Wi-Fi is stable.
- [ ] Docker production stack starts.
- [ ] systemd starts Mirrage after reboot.
- [ ] Frontend kiosk mode opens.
- [ ] `GET /api/health` returns online.
- [ ] `GET /api/health/full` returns subsystem checks.
- [ ] Frontend `/health` works.
- [ ] Logs are written.
- [ ] Backups can be created.

## Audio And Voice

- [ ] Speakers play assistant speech.
- [ ] Speaker volume is usable from normal distance.
- [ ] Microphone receives speech.
- [ ] Microphone placement does not sound muffled.
- [ ] Wake engine status endpoint returns expected state.
- [ ] Manual wake detection opens Conversation Mode.
- [ ] Real wake model test is completed if model is installed.
- [ ] False activation test is completed if wake model is installed.

## Smart Home And Integrations

- [ ] Weather endpoint works or falls back clearly.
- [ ] Calendar status is clear.
- [ ] Spotify status is clear.
- [ ] Smart Home status is clear.
- [ ] Home Assistant devices are discovered if configured.
- [ ] Unsupported smart home domains remain blocked.

## Frame And Mounting

- [ ] Frame supports display and mirror material.
- [ ] Back panel is removable.
- [ ] Mini PC and USB ports are accessible.
- [ ] Cable exit has strain relief.
- [ ] Service loop exists.
- [ ] Wall mounting hardware is rated for the total weight.
- [ ] Mount is level.
- [ ] Ventilation is not blocked after mounting.
- [ ] No mains wiring is exposed or modified.

If any critical item fails, fix it before final installation.
