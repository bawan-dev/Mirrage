# Website Update Notes

These notes are for updating a portfolio site, GitHub profile, or project page
after the v1 polish milestone.

## Short Description

Mirrage is a privacy-first ambient AI mirror platform with a React mirror
interface, FastAPI backend, provider-based assistant routing, local memory, daily
context, rule-based proactive nudges, Spotify, Calendar, Home Assistant
boundaries, trusted-device authentication, deterministic permissions, production
deployment docs, and a kiosk-style Mirror Mode.

## Honest AI-Assisted Development Note

I used AI-assisted development heavily, but I defined the product direction,
architecture, roadmap, acceptance criteria, testing process, and reviewed the
implementation as the project evolved. The goal was not to generate a toy app;
it was to build a coherent full-stack system with clear boundaries and a path to
hardware.

## Current Status

| Area | Status |
| --- | --- |
| Mirror frontend | Working local React app |
| Mirror Mode | v1 polished ambient mirror mode behind `VITE_MIRROR_MODE=true` |
| Demo mode | Explicit fake portfolio data behind `VITE_MIRRAGE_DEMO_MODE=true` |
| Identity and safety | v2 trusted devices, roles, permissions, approvals, and audit history |
| Backend API | Working FastAPI service |
| Assistant routing | Working provider runtime and local command routing |
| Voice | Browser push-to-talk and browser speech output |
| Weather | Backend Open-Meteo integration with fallback |
| Calendar | Google Calendar OAuth and read-only event views |
| Spotify | OAuth, current playback, artwork, and basic controls |
| Memory | Local SQLite preferences, facts, goals, and routines |
| Proactive nudges | Local rule-based summaries from weather, Calendar, and memory context |
| Smart home | Home Assistant foundation with safe supported domains; real-home testing still needed |
| Wake word | Local wake engine boundary prepared; real model and microphone testing still needed |
| Hardware | Physical build plan documented; real parts still need testing |
| Vision | Not built |

## Suggested Portfolio Bullets

- Built a full-stack smart mirror assistant with React, TypeScript, FastAPI, and
  Docker.
- Designed a backend-owned personal context layer that combines weather,
  calendar, and local memory without sending private context to a model by
  default.
- Added a local proactive assistant layer that surfaces small daily nudges from
  context without relying on an external model.
- Added a kiosk-friendly Mirror Mode with startup checks, inactivity dimming,
  burn-in movement, ambient focus transitions, and polished assistant presence
  states.
- Integrated Spotify and Google Calendar through isolated backend service
  layers.
- Added local SQLite memory for preferences, goals, facts, and routines.
- Prepared a local OpenWakeWord wake engine boundary without sending pre-wake
  audio to cloud services.
- Documented the first physical mirror build path, including display, mirror
  material, mini PC, microphone, audio, thermal, frame, maintenance, and cost
  planning.
- Added a backend-owned v2 identity and safety layer with hash-only
  trusted-device tokens, default-deny permissions, approvals, protected private
  routes, and append-only redacted audit events.

## Assets To Include

Recommended screenshots:

- `assets/screenshots/mirror-home.png`
- `assets/screenshots/weather-focus.png`
- `assets/screenshots/assistant-focus.png`
- `assets/screenshots/calendar-focus.png`
- `assets/screenshots/context-focus.png`
- `assets/screenshots/media-focus.png`
- `assets/screenshots/smart-home-focus.png`
- `assets/screenshots/identity-admin.png`

Recommended docs to link:

- `README.md`
- `docs/architecture.md`
- `docs/mirror-mode.md`
- `docs/context.md`
- `docs/proactive-assistant.md`
- `docs/demo-guide.md`
- `docs/v1-release.md`
- `docs/showcase.md`
- `docs/demo-script.md`
- `docs/identity-safety.md`
- `docs/security-model.md`
- `docs/wake-engine.md`
- `hardware/physical-build.md`
- `hardware/build-plan.md`

## Video Placeholder

Add the final demo video URL here once recorded:

```text
Demo video: TBD
```
