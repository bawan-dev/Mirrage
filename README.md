# Mirrage

[![CI](https://github.com/bawan-dev/Mirrage/actions/workflows/ci.yml/badge.svg)](https://github.com/bawan-dev/Mirrage/actions/workflows/ci.yml)

Mirrage is an AI smart mirror project: a wall-mounted mirror display with a clean dashboard, voice interaction, and an assistant layer that can eventually run with local or remote models.

The goal is to build the software and hardware plan together: dashboard first, backend next, then AI, voice, and physical mirror integration.

## What This Project Is

Mirrage is planned as a smart mirror assistant for everyday use. It should show useful information at a glance, respond to voice commands, and act as a focused AI interface in a physical room.

The long-term version includes:

- A dark mirror-friendly dashboard
- Clock, date, weather, and status widgets
- Voice input and assistant responses
- Local or remote AI model support
- Hardware planning for a real mirror build
- Docker-based development and deployment

## Current Status

This project is in the foundation stage.

Right now, the dashboard, backend, and first assistant boundary are in place. Voice is status-only. Hardware planning notes are started, but no physical build exists yet.

Current foundation:

- `frontend/` for the React dashboard
- `backend/` for the FastAPI service
- `ai/` for AI provider routing
- `docs/` for architecture and planning
- `hardware/` for the physical mirror build notes
- `assets/` for screenshots, diagrams, and visual material
- Docker and environment setup files

## Screenshot

![Mirrage dashboard](assets/screenshots/dashboard.png)

## Planned Architecture

![Mirrage architecture](assets/diagrams/architecture.svg)

```text
Mirror Dashboard
      |
      v
FastAPI Backend
      |
      +-- AI Service Layer
      |
      +-- Voice Service
      |
      +-- Hardware Status Layer
```

The system will be built in layers so each part can improve independently. The frontend should not need to know which AI provider is being used. The backend should expose clean status and assistant endpoints. Hardware support should be documented before it is wired into code.

More detail is tracked in [docs/architecture.md](docs/architecture.md).

The build plan is tracked in [docs/roadmap.md](docs/roadmap.md).

The first backend contract is tracked in [docs/api.md](docs/api.md).

Voice planning is tracked in [docs/voice.md](docs/voice.md).

Quick run steps are in [docs/run-notes.md](docs/run-notes.md), and common setup
problems are covered in [docs/troubleshooting.md](docs/troubleshooting.md).

## Tech Stack

Current stack:

| Area | Tooling |
| --- | --- |
| Frontend | React, TypeScript, Tailwind CSS, Vite |
| Backend | Python, FastAPI |
| AI | Provider layer: stub, Ollama (local), OpenAI-compatible |
| Voice | Status layer first, speech pipeline later |
| Dev setup | Docker Compose |
| Docs | Markdown |

## Build Approach

Mirrage will be built in small daily steps. Each step should have one clear purpose.

Near-term order:

- Keep the dashboard and backend connected
- Add features in small testable steps
- Keep planned features clearly marked
- Add Docker wiring
- Add hardware build notes
- Add real voice and AI support only after the boundaries are stable

## Project Structure

```text
mirrage/
  frontend/
  backend/
  ai/
  docs/
  hardware/
  assets/
  docker-compose.yml
  .env.example
  .gitignore
  README.md
```

## What Is Not Built Yet

This project does not currently include:

- A working voice pipeline
- Real hardware integration
- A production deployment

The AI assistant works through a pluggable provider layer (`stub` by default, or a
real Ollama / OpenAI-compatible model via `MIRRAGE_AI_PROVIDER`).

Those pieces will be added deliberately as the project develops.

## Local Development

Local workflow:

### Frontend

```powershell
# frontend
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
# backend
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

Docker runs the frontend and backend together.

```powershell
# docker
docker compose up --build
```

Open:

```text
http://127.0.0.1:5173
http://127.0.0.1:8000/health
```

Expected:

- the dashboard loads at `5173`
- the backend health check returns `{"service":"mirrage-api","status":"online"}`

Stop Docker:

```powershell
Ctrl + C
docker compose down
```

## Code Quality

The backend uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.
The frontend uses ESLint and Prettier.

```powershell
# backend (from the repo root, with the venv active)
pip install -r backend/requirements-dev.txt
ruff check .
ruff format --check .

# frontend
cd frontend
npm run lint
npm run format:check
```

`ruff format .` and `npm run format` apply fixes in place.

## Testing

The backend has a pytest suite covering the API endpoints and the AI service layer.

```powershell
pip install -r backend/requirements-dev.txt
pytest
```

Every push and pull request runs the full check suite in GitHub Actions
([.github/workflows/ci.yml](.github/workflows/ci.yml)): Ruff lint and format on the
backend, pytest, then ESLint, Prettier, type-check, and build on the frontend.

## Roadmap

- [x] Create repository structure
- [x] Add starter files for the main system areas
- [x] Draft the project overview
- [x] Document the architecture
- [x] Document the roadmap
- [x] Document the first API endpoints
- [x] Review and clean starter files
- [x] Set up the React + Vite frontend
- [x] Build the first smart mirror dashboard screen
- [x] Set up the FastAPI backend
- [x] Add health and status endpoints
- [x] Add AI provider routing
- [x] Add voice service status
- [x] Add Docker development setup
- [x] Add hardware planning details
- [x] Finish project polish (run notes, troubleshooting, current roadmap)
- [x] Migrate frontend to TypeScript + Tailwind
- [x] Add linting and formatting
- [x] Add tests and continuous integration
- [x] Connect a real AI provider
- [x] Add live weather data

The full phase breakdown lives in [docs/roadmap.md](docs/roadmap.md).

## Why Mirrage

Mirrage combines software, AI, interface design, and hardware into one project. The plan is to build it in layers so each part can be understood, tested, and improved without losing track of the whole system.
