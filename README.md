# Mirrage

Mirrage is an AI smart mirror project: a wall-mounted mirror display with a clean dashboard, voice interaction, and an assistant layer that can eventually run with local or remote AI models.

The goal is not to make a quick demo. The goal is to build this like a real system, one small piece at a time, with a frontend, backend, AI layer, voice service, hardware notes, and deployment structure that can grow without turning messy.

## What This Project Is

Mirrage is planned as a smart mirror assistant for everyday use. It should be able to show useful information at a glance, respond to voice commands, and act as a focused AI interface in a physical room.

The long-term version includes:

- A dark mirror-friendly dashboard
- Clock, date, weather, and status widgets
- Voice input and assistant responses
- Local or remote AI model support
- Hardware planning for a real mirror build
- Docker-based development and deployment

## Current Status

This repository is in the foundation stage.

Right now, the project structure is in place and the main areas of the system have been separated into folders. Most files are placeholders on purpose. The next step is to replace those placeholders one by one with real implementation.

Current foundation:

- `frontend/` for the React dashboard
- `backend/` for the FastAPI service
- `ai/` for future AI provider routing
- `docs/` for architecture and planning
- `hardware/` for the physical mirror build notes
- `assets/` for screenshots, diagrams, and visual material
- Docker and environment placeholder files

## Planned Architecture

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

## Tech Stack

Planned stack:

| Area | Tooling |
| --- | --- |
| Frontend | React, Vite, CSS |
| Backend | Python, FastAPI |
| AI | Provider layer for local and remote models |
| Voice | Placeholder first, speech pipeline later |
| Dev setup | Docker Compose |
| Docs | Markdown |

## Build Approach

Mirrage will be built in small daily steps. Each step should leave the repo better than it was before, even if the change is only one file.

Near-term order:

- Write the project README
- Define the architecture document
- Define the roadmap
- Set up the frontend package
- Build the first dashboard screen
- Add backend API basics
- Add AI and voice placeholders
- Add Docker wiring
- Add hardware build notes

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

This project does not currently claim to have:

- A working AI assistant
- A working voice pipeline
- Live weather data
- Real hardware integration
- A production deployment

Those pieces will be added deliberately as the project develops.

## Local Development

The exact setup commands will be added when the frontend and backend placeholders are replaced with real code.

Planned local workflow:

```bash
# frontend
cd frontend
npm install
npm run dev
```

```bash
# backend
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

```bash
# docker
docker compose up --build
```

## Roadmap

- [x] Create repository structure
- [x] Add placeholder files for the main system areas
- [x] Write the first real README
- [x] Document the architecture
- [ ] Document the roadmap
- [ ] Set up the React + Vite frontend
- [ ] Build the first smart mirror dashboard screen
- [ ] Set up the FastAPI backend
- [ ] Add health and status endpoints
- [ ] Add AI provider placeholder logic
- [ ] Add voice service placeholder logic
- [ ] Add Docker development setup
- [ ] Add hardware planning details

## Why Mirrage

Mirrage is a way to combine software, AI, interface design, and hardware into one serious portfolio project. It is being built slowly on purpose, with the goal of making each layer understandable, useful, and good enough to show.
