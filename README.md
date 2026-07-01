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

Development note: I use AI-assisted development heavily on this project, but I
define the product direction, architecture, roadmap, acceptance criteria, testing
process, and review the implementation as it evolves.

## Current Build

What works now:

- React + TypeScript + Tailwind mirror interface
- FastAPI backend with health, system, voice, weather, assistant, memory, Spotify, Calendar, presence, and AI runtime routes
- mirror interface connected to backend status data
- weather endpoint using Open-Meteo with a fallback state
- AI runtime with provider routing, task-aware model selection, privacy-aware context prompts, fallback behavior, and `stub`, `ollama`, and `openai` provider options
- browser push-to-talk voice input in the assistant focus view
- speech transcripts sent through the existing assistant endpoint
- browser text-to-speech for assistant replies
- mute and browser voice settings in the assistant focus view
- backend-owned assistant presence engine with Server-Sent Events
- wake-word adapter endpoint for local wake engines using `Hey Mirrage` by default
- local command routing for opening weather, media, assistant, calendar, and context focus views
- Spotify OAuth, currently playing, album artwork, and playback controls
- Google Calendar OAuth, today's schedule, upcoming events, and calendar assistant command
- local SQLite memory layer for preferences, facts, goals, and routines
- assistant memory commands for storing, recalling, and updating local memories
- provider-independent daily context aggregation from weather, calendar, and memory
- provider-independent proactive summary for calm daily nudges
- streaming-shaped assistant endpoint using Server-Sent Events for future token streaming
- Daily Briefing view for daily overview, goals, routines, and suggested focus
- optional Mirror Mode for kiosk-style wall display use, now styled as an ambient glass surface instead of a dashboard
- Docker Compose for running frontend and backend together
- backend tests, frontend lint/type/build checks, and GitHub Actions CI
- hardware planning notes for the first mirror prototype

What is still planned:

- trained local `Hey Mirrage` wake-word model asset
- backend or local speech-to-text option
- backend or local text-to-speech option
- Spotify persistence, device picker, and voice playback commands
- Calendar token persistence and richer schedule actions
- memory editing UI and stronger privacy controls
- AI-enhanced context summaries behind explicit privacy controls
- true provider token streaming
- richer local model profiles for small, summary, planning, and future agent tasks
- smart home control
- physical mirror installation
- production deployment

The default assistant provider is still `stub`. Real model replies require configuring Ollama or an OpenAI-compatible API provider.

## Current Status

| Area | Status |
| --- | --- |
| Mirror UI | Working local React app |
| Mirror Mode | Working behind `VITE_MIRROR_MODE=true` |
| Backend API | Working FastAPI service |
| Assistant | Runtime, provider routing, fallback, and deterministic handlers work; default provider is still `stub` |
| Voice | Browser push-to-talk, browser speech synthesis, and backend presence events |
| Wake word | Adapter and lifecycle ready; local engine/model still required |
| Weather | Live backend weather endpoint with fallback |
| Calendar | Google Calendar OAuth and read-only schedule views |
| Spotify | OAuth, current playback, artwork, and basic controls |
| Memory | Local SQLite preferences, facts, goals, and routines |
| Proactive assistant | Local rule-based daily nudge from context sources |
| Hardware | Planning docs only |
| Smart home / vision | Not built yet |

## Screenshots And Demo

![Mirrage ambient mirror home](assets/screenshots/mirror-home.png)

| View | Screenshot |
| --- | --- |
| Mirror home | [assets/screenshots/mirror-home.png](assets/screenshots/mirror-home.png) |
| Weather focus | [assets/screenshots/weather-focus.png](assets/screenshots/weather-focus.png) |
| Assistant focus | [assets/screenshots/assistant-focus.png](assets/screenshots/assistant-focus.png) |
| Calendar focus | [assets/screenshots/calendar-focus.png](assets/screenshots/calendar-focus.png) |
| Context focus | [assets/screenshots/context-focus.png](assets/screenshots/context-focus.png) |
| Media focus | [assets/screenshots/media-focus.png](assets/screenshots/media-focus.png) |

Demo video: `TBD`

Demo flow: [docs/demo-guide.md](docs/demo-guide.md)

## Architecture

![Mirrage architecture](assets/diagrams/architecture.svg)

```text
Mirror Dashboard
      |
      v
FastAPI Backend
      |
      +-- AI Runtime
      |     +-- Context Builder
      |     +-- Provider Router
      |     +-- Local / Cloud Providers
      |
      +-- Local Memory Store
      |
      +-- Personal Context Layer
      |
      +-- Proactive Assistant Layer
      |
      +-- Calendar Integration
      |
      +-- Spotify Integration
      |
      +-- Wake Word + Presence Layer
      |
      +-- Voice Pipeline
      |
      +-- Hardware Planning Layer
```

The frontend renders the mirror experience. The backend owns API boundaries, service state, assistant routing, daily context, proactive summaries, local memory, and external data. The AI runtime builds a small privacy-aware context, chooses a provider, and falls back safely if the selected provider is unavailable. AI providers, context aggregation, memory storage, voice input, and hardware integration stay behind those boundaries so they can change without rewriting the mirror surface.

More detail:

- [Architecture](docs/architecture.md)
- [AI runtime](docs/ai-runtime.md)
- [API notes](docs/api.md)
- [Calendar setup](docs/calendar.md)
- [Command routing](docs/command-routing.md)
- [Context system](docs/context.md)
- [Memory layer](docs/memory.md)
- [Mirror Mode](docs/mirror-mode.md)
- [Proactive assistant](docs/proactive-assistant.md)
- [Roadmap](docs/roadmap.md)
- [Spotify setup](docs/spotify.md)
- [Voice and presence](docs/voice.md)
- [Wake word and presence](docs/wake-word-presence.md)
- [Run notes](docs/run-notes.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Website update notes](docs/website-update-notes.md)

Hardware notes:

- [Build plan](hardware/build-plan.md)
- [Component tracker](hardware/components.md)
- [Wiring notes](hardware/wiring-notes.md)

## Tech Stack

| Area | Tooling |
| --- | --- |
| Frontend | React, TypeScript, Tailwind CSS, Vite |
| Backend | Python, FastAPI |
| AI | Runtime with provider routing, local/cloud privacy prompts, stub, Ollama, and OpenAI-compatible APIs |
| Weather | Backend Open-Meteo integration with fallback behavior |
| Music | Spotify OAuth and Web API through backend endpoints |
| Calendar | Google Calendar OAuth and read-only events through backend endpoints |
| Voice | Browser speech recognition, browser speech synthesis, and backend presence lifecycle |
| Wake word | Local wake adapter with configurable phrase; model asset still planned |
| Commands | Frontend intent routing for local UI actions |
| Context | Backend aggregation across weather, Calendar, and local memory |
| Memory | Local SQLite storage for preferences, facts, goals, and routines |
| Proactive | Deterministic backend summary for non-intrusive daily nudges |
| Mirror Mode | Frontend kiosk mode behind `VITE_MIRROR_MODE=true` |
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

Mirror Mode is optional:

```powershell
cd frontend
$env:VITE_MIRROR_MODE="true"
npm run dev
```

Details: [docs/mirror-mode.md](docs/mirror-mode.md).

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
- set `VITE_MIRROR_MODE=true`, reload the frontend, and confirm the ambient Mirror Mode home appears
- confirm Mirror Mode dims after inactivity and returns to home from a focus view after the second timeout
- open `http://127.0.0.1:8000/health` and confirm the backend is online
- check the mirror home shows backend status when the API is running
- check the weather view either shows live data or a clear fallback
- open the assistant focus view, press `Push to talk`, allow microphone access, and confirm the transcript appears
- confirm the voice transcript is sent to `/api/assistant/message` and the assistant reply appears in the assistant view
- confirm assistant replies are spoken aloud when speech output is not muted
- confirm `Mute`, `Test voice`, and the browser voice selector work in the assistant focus view
- open `http://127.0.0.1:8000/api/proactive/summary` and confirm it returns `headline`, `message`, `priority`, `suggestions`, and `should_interrupt`
- open `http://127.0.0.1:8000/api/presence/status` and confirm `state` and `wake_phrase` are present
- open `http://127.0.0.1:8000/api/ai/runtime/status` and confirm runtime settings load without secrets
- open `http://127.0.0.1:8000/api/ai/providers` and confirm `stub`, `ollama`, and `openai` are listed
- post a message to `http://127.0.0.1:8000/api/assistant/stream` and confirm `status`, `chunk`, and `done` events are returned
- post `{ "phrase": "Hey Mirrage" }` to `/api/wake-word/detect` and confirm the state moves to `wake_detected`
- in Mirror Mode, confirm the lower-right nudge shows a calm daily summary or fallback
- type `What is the weather?` in the assistant view and confirm Weather focus opens
- type `Show my music` in the assistant view and confirm Media focus opens
- type `What is on my calendar today?` and confirm Calendar focus opens with a schedule response
- type `daily briefing` and confirm Context focus opens with a provider-independent proactive briefing
- type `Good morning` or `What needs my attention?` and confirm the assistant replies with `provider: proactive`
- open `http://127.0.0.1:8000/api/context/daily` and confirm weather, calendar, memory, and suggested focus fields exist
- type `Open assistant` and confirm Assistant focus opens
- type `remember my favorite drink is coffee` and confirm the assistant replies with `provider: memory`
- type `what do you remember about me?` and confirm the response includes `favorite drink: coffee`
- open `http://127.0.0.1:8000/api/memory/summary` and confirm the memory appears under preferences
- configure Spotify credentials, connect through the Media view, and confirm playback state loads
- test Spotify play/pause/next/previous with an active Spotify device
- configure Google Calendar credentials, connect through the Calendar view, and confirm today's events load
- send a message to `/api/assistant/message` and confirm the response shape stays stable
- run `docker compose up --build` when Docker or shared run config changes

Browser voice works best in Chrome or Edge because it uses browser speech recognition and speech synthesis. Wake-word audio should be handled by a local engine; this repo currently includes the backend adapter and presence lifecycle, not a trained wake-word model asset.

Spotify playback controls require a connected Spotify account and an active Spotify
device. The first token store is in process memory, so reconnect after backend
restart.

Google Calendar uses a read-only events scope. The first token store is also in
process memory, so reconnect after backend restart.

Memory records are stored locally in `data/mirrage-memory.sqlite3`. That file is
ignored by Git. Docker Compose mounts `./data` into the backend container so
local memory can survive container restarts.

CI runs the core checks on every push and pull request through [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Project Structure

```text
mirrage/
  frontend/       mirror interface
  backend/        FastAPI service
  ai/             assistant provider layer
  data/           local runtime data placeholder
  docs/           architecture, API, roadmap, run notes
  hardware/       physical build planning
  assets/         screenshots and diagrams
```

## Roadmap Snapshot

Completed foundation work:

- frontend mirror interface
- backend API
- AI provider boundary and runtime
- live weather endpoint and ambient weather view
- Ambient Interaction Layer with focus views
- push-to-talk voice foundation
- browser text-to-speech foundation
- wake-word adapter and presence engine
- local command routing for focus views
- Spotify media integration
- Google Calendar daily schedule integration
- local memory layer
- personal context system
- mirror mode
- proactive ambient intelligence layer
- ambient intelligence redesign with sparse typography, fewer containers, and refreshed screenshots
- AI runtime with privacy-aware context building, provider routing, fallback, and stream shape
- Docker development setup
- tests and CI
- first hardware planning notes

Next planned milestone:

- Local AI runtime testing with Ollama, then local wake-word engine/model integration and microphone hardware testing

Future milestones:

- Wake Word Engine Integration
- AI Runtime Refinement
- Spotify Refinement
- Calendar Refinement
- Memory Refinement
- Context Refinement
- Smart Home Integration
- Physical Mirror Build
- Home Installation

The full phase breakdown lives in [docs/roadmap.md](docs/roadmap.md).
