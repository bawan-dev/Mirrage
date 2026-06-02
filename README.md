# Mirrage

[![CI](https://github.com/bawan-dev/Mirrage/actions/workflows/ci.yml/badge.svg)](https://github.com/bawan-dev/Mirrage/actions/workflows/ci.yml)

Mirrage is a privacy-first ambient AI assistant for the home, starting with a smart mirror interface.

The project is being built as a serious full-stack system: a mirror-first frontend, a FastAPI backend, provider-based AI routing, live information endpoints, Docker development setup, CI, and hardware planning for a future physical build.

## Product Direction

The long-term version is not a cluttered dashboard. The goal is an assistant that stays quiet until it is needed:

```text
Minimal home state
  -> focused assistant / weather / media view
  -> return to home state
```

Planned direction:

- minimal mirror home screen with clock, weather, and subtle system state
- focus views for assistant, weather, media, calendar, and home controls
- local-first AI support where possible
- push-to-talk voice interaction first, with wake word and backend/local audio later
- physical mirror build after the display, material, audio, heat, and wiring choices are tested

## Current Build

What works now:

- React + TypeScript + Tailwind mirror interface
- FastAPI backend with health, system, voice, weather, assistant, Spotify, and Calendar routes
- dashboard connected to backend status data
- weather endpoint and card using Open-Meteo with a fallback state
- AI provider boundary with `stub`, `ollama`, and `openai` provider options
- browser push-to-talk voice input in the assistant focus view
- speech transcripts sent through the existing assistant endpoint
- browser text-to-speech for assistant replies
- mute and browser voice settings in the assistant focus view
- local command routing for opening weather, media, assistant, and calendar focus views
- Spotify OAuth, currently playing, album artwork, and playback controls
- Google Calendar OAuth, today's schedule, upcoming events, and calendar assistant command
- Docker Compose for running frontend and backend together
- backend tests, frontend lint/type/build checks, and GitHub Actions CI
- hardware planning notes for the first mirror prototype

What is still planned:

- wake word support
- backend or local speech-to-text option
- backend or local text-to-speech option
- Spotify persistence, device picker, and voice playback commands
- Calendar token persistence and richer schedule actions
- memory/context layer
- smart home control
- physical mirror installation
- production deployment

The default assistant provider is still `stub`. Real model replies require configuring Ollama or an OpenAI-compatible API provider.

## Screenshot

![Mirrage dashboard foundation](assets/screenshots/dashboard.png)

## Architecture

![Mirrage architecture](assets/diagrams/architecture.svg)

```text
Mirror Dashboard
      |
      v
FastAPI Backend
      |
      +-- AI Service Layer
      |
      +-- Calendar Integration
      |
      +-- Spotify Integration
      |
      +-- Voice Input Layer
      |
      +-- Hardware Planning Layer
```

The frontend renders the mirror experience. The backend owns API boundaries, service state, assistant routing, and external data. AI providers, voice input, and hardware integration stay behind those boundaries so they can change without rewriting the dashboard.

More detail:

- [Architecture](docs/architecture.md)
- [API notes](docs/api.md)
- [Calendar setup](docs/calendar.md)
- [Command routing](docs/command-routing.md)
- [Roadmap](docs/roadmap.md)
- [Spotify setup](docs/spotify.md)
- [Voice plan](docs/voice.md)
- [Run notes](docs/run-notes.md)
- [Troubleshooting](docs/troubleshooting.md)

Hardware notes:

- [Build plan](hardware/build-plan.md)
- [Component tracker](hardware/components.md)
- [Wiring notes](hardware/wiring-notes.md)

## Tech Stack

| Area | Tooling |
| --- | --- |
| Frontend | React, TypeScript, Tailwind CSS, Vite |
| Backend | Python, FastAPI |
| AI | Provider boundary for stub, Ollama, and OpenAI-compatible APIs |
| Weather | Backend Open-Meteo integration with fallback behavior |
| Music | Spotify OAuth and Web API through backend endpoints |
| Calendar | Google Calendar OAuth and read-only events through backend endpoints |
| Voice | Browser push-to-talk speech recognition and speech synthesis foundation |
| Commands | Frontend intent routing for local UI actions |
| Dev setup | Docker Compose |
| Quality | Pytest, Ruff, ESLint, Prettier, TypeScript |
| CI | GitHub Actions |

## Local Development

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

### Backend

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{"service":"mirrage-api","status":"online"}
```

### Docker

```powershell
docker compose up --build
```

Open:

```text
http://127.0.0.1:5173
http://127.0.0.1:8000/health
```

Stop Docker:

```powershell
Ctrl + C
docker compose down
```

## Testing

Current automated checks:

```powershell
# frontend
cd frontend
npm run lint
npm run format:check
npm run type-check
npm run build
```

```powershell
# backend, from repo root
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements-dev.txt
pytest
```

Current manual checks:

- open `http://127.0.0.1:5173` and confirm the mirror UI loads
- open `http://127.0.0.1:8000/health` and confirm the backend is online
- check the dashboard system card shows backend status when the API is running
- check the weather card either shows live data or a clear fallback
- open the assistant focus view, press `Push to talk`, allow microphone access, and confirm the transcript appears
- confirm the voice transcript is sent to `/api/assistant/message` and the assistant reply appears in the assistant view
- confirm assistant replies are spoken aloud when speech output is not muted
- confirm `Mute`, `Test voice`, and the browser voice selector work in the assistant focus view
- type `What is the weather?` in the assistant view and confirm Weather focus opens
- type `Show my music` in the assistant view and confirm Media focus opens
- type `What is on my calendar today?` and confirm Calendar focus opens with a schedule response
- type `Open assistant` and confirm Assistant focus opens
- configure Spotify credentials, connect through the Media view, and confirm playback state loads
- test Spotify play/pause/next/previous with an active Spotify device
- configure Google Calendar credentials, connect through the Calendar view, and confirm today's events load
- send a message to `/api/assistant/message` and confirm the response shape stays stable
- run `docker compose up --build` when Docker or shared run config changes

Browser voice works best in Chrome or Edge because it uses browser speech recognition and speech synthesis. Wake word detection is not built yet.

Spotify playback controls require a connected Spotify account and an active Spotify
device. The first token store is in backend memory, so reconnect after backend
restart.

Google Calendar uses a read-only events scope. The first token store is also in
backend memory, so reconnect after backend restart.

CI runs the core checks on every push and pull request through [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Project Structure

```text
mirrage/
  frontend/       mirror interface
  backend/        FastAPI service
  ai/             assistant provider layer
  docs/           architecture, API, roadmap, run notes
  hardware/       physical build planning
  assets/         screenshots and diagrams
```

## Roadmap Snapshot

Completed foundation work:

- frontend dashboard
- backend API
- AI provider boundary
- live weather endpoint and dashboard card
- Ambient Interaction Layer with focus views
- push-to-talk voice foundation
- browser text-to-speech foundation
- local command routing for focus views
- Spotify media integration
- Google Calendar daily schedule integration
- Docker development setup
- tests and CI
- first hardware planning notes

Next planned milestone:

- Calendar refinement: token persistence, event detail polish, and broader schedule commands

Future milestones:

- Wake Word
- Spotify Refinement
- Calendar Refinement
- Memory Layer
- Smart Home Integration
- Physical Mirror Build
- Home Installation

The full phase breakdown lives in [docs/roadmap.md](docs/roadmap.md).
