# Mirrage v1 Release Notes

Mirrage v1.0.0 is the first complete portfolio release of the project. It is
release-ready as a software foundation and demo experience, not as a finished
wall-mounted hardware product.

## What v1 Includes

- ambient React + TypeScript mirror interface
- Mirror Mode for kiosk-style display use
- polished assistant presence states for idle, wake, listening, processing,
  speaking, returning, sleeping, and error
- FastAPI backend with health, status, assistant, memory, weather, Calendar,
  Spotify, smart home, wake-word, presence, and AI runtime routes
- local SQLite memory layer
- provider-independent daily context and proactive briefing services
- browser push-to-talk speech input
- browser text-to-speech output
- backend-owned presence lifecycle and wake engine boundary
- OpenWakeWord provider boundary, disabled by default until a model and
  microphone are configured
- Spotify and Google Calendar service layers
- Home Assistant smart home boundary with safe supported domains
- Docker development and production Compose files
- systemd examples, health checks, logging, backups, and deployment docs
- physical mirror build documentation
- explicit frontend demo mode for portfolio screenshots

## What Is Real

The software stack runs locally, routes requests through the backend, and has
tests around the backend services. Demo mode is explicit and controlled by
`VITE_MIRRAGE_DEMO_MODE=true`.

## What Requires Configuration

- real AI replies require `stub`, Ollama, or OpenAI-compatible provider setup
- Spotify requires OAuth credentials and an active Spotify device
- Calendar requires Google OAuth credentials
- Home Assistant requires a local base URL and token
- local wake-word detection requires a model file, microphone, and target-device
  testing

## Known Limitations

- the physical mirror has not been built unless hardware has been assembled
  outside the repo
- wake-word reliability still needs real microphone and room testing
- browser speech recognition works best in Chrome or Edge
- Spotify and Calendar tokens are not yet persisted across backend restarts
- local AI quality depends on the configured provider and model
- final thermal, brightness, and mounting performance depend on chosen hardware

## Release Checklist

- [x] automated checks pass locally
- [x] screenshots refreshed
- [x] README updated
- [x] demo guide updated
- [x] known limitations documented
- [x] release tag commands documented
- [ ] final GitHub Actions run is green
- [ ] final commit pushed
- [ ] `v1.0.0` tag pushed

## Suggested Tag

```powershell
git tag v1.0.0
git push origin v1.0.0
```
