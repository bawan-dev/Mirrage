# Roadmap

Mirrage will be built in small steps. Each phase has a clear job so the project does not drift.

## Working Style

Small steps, clear purpose.

Each session should do one of these:

- turn a starter file into working code or useful documentation
- connect two parts of the system
- document a decision
- improve the dashboard
- make the project easier to run

If a step needs more than one file, that is fine, but it should still have one clear purpose.

## Phase 1: Project Foundation

Goal: make the repository understandable before adding real app code.

- [x] Create the main folder structure
- [x] Add starter files so every planned area can be committed
- [x] Draft the project overview
- [x] Document the system architecture
- [x] Create this roadmap
- [x] Write basic API documentation
- [x] Review and clean starter files before coding starts

Why this matters:

The project should have a clear base before app code is added.

## Phase 2: Frontend Foundation

Goal: get the smart mirror dashboard running in the browser.

- [x] Set up React + Vite
- [x] Add a clean app entry point
- [x] Build the first dashboard layout
- [x] Add clock and date display
- [x] Add first cards for weather, assistant, voice, system, and hardware
- [x] Make the layout responsive
- [x] Polish the dark mirror visual style

Done when:

The frontend runs locally and shows the first version of the dashboard, even if the data is still static.

## Phase 3: Backend Foundation

Goal: get a small FastAPI backend running locally.

- [x] Add backend dependencies
- [x] Create the FastAPI app
- [x] Add a health endpoint
- [x] Add a system status endpoint
- [x] Add a voice status endpoint
- [x] Add an assistant message endpoint
- [x] Keep route code and service code separate

Done when:

The backend runs locally and returns JSON from the first planned endpoints.

## Phase 4: Connect Frontend And Backend

Goal: make the dashboard read backend status instead of only static text.

- [x] Add frontend API configuration
- [x] Fetch backend health/status data
- [x] Show loading states
- [x] Show basic error states
- [x] Connect voice status card
- [x] Connect system status card
- [x] Keep planned AI and hardware fields clearly marked

Done when:

The dashboard proves that the full stack is connected.

## Phase 5: AI Service Layer

Goal: create a clean assistant boundary without adding a real model too early.

- [x] Define a simple assistant request and response shape
- [x] Add an initial AI provider stub
- [x] Add provider selection config
- [x] Route assistant messages through the AI service layer
- [x] Document where Ollama or OpenAI support will fit later

Done when:

The assistant endpoint works through the AI layer, even if the answer is still a simple stub response.

## Phase 6: Voice Status

Goal: prepare for voice without jumping into microphone complexity too early.

- [x] Define voice status fields
- [x] Return voice status from the backend
- [x] Display voice status in the dashboard
- [x] Document future wake word, speech-to-text, and text-to-speech options

Done when:

The app has a clear place for voice work before microphone features are added.

## Phase 7: Docker Development Setup

Goal: make the project easier to run as a full stack.

- [x] Add frontend Dockerfile
- [x] Add backend Dockerfile
- [x] Wire services in Docker Compose
- [x] Document Docker run commands
- [x] Confirm frontend and backend ports

Done when:

`docker compose up` has a clear path, even if the setup is still development-focused.

## Phase 8: Hardware Planning

Goal: figure out the first physical version before buying parts.

- [x] List candidate display options
- [x] List mirror material options
- [x] Plan compute device choices
- [x] Plan microphone and speaker options
- [x] Write first wiring notes
- [x] Track open hardware risks

Done when:

There is enough hardware planning to build a rough first prototype.

## Phase 9: Project Polish

Goal: make Mirrage easy to run, explain, and improve.

- [x] Add dashboard screenshots
- [x] Add architecture diagram assets
- [x] Improve project visuals
- [x] Add short run notes
- [x] Add setup troubleshooting
- [x] Keep the roadmap current

Done when:

A new reader can understand what Mirrage is, what works, and what is coming next.

## Phase 10: Frontend TypeScript + Tailwind

Goal: align the frontend with the advertised stack and make it type-safe.

- [x] Add TypeScript and convert the React entry points
- [x] Add Tailwind CSS and a Vite Tailwind setup
- [x] Port the dashboard styling to Tailwind utilities
- [x] Type the API client and backend response shapes
- [x] Confirm the dashboard still loads and reads backend status

Done when:

The frontend is TypeScript + Tailwind and matches the project overview.

## Phase 11: Code Quality

Goal: keep the codebase consistent and easy to maintain.

- [x] Add Ruff for Python linting and formatting
- [x] Add ESLint + Prettier for the frontend
- [x] Fix existing lint findings
- [x] Document the quality commands

Done when:

Lint and format run cleanly across backend and frontend.

## Phase 12: Testing And Continuous Integration

Goal: prove the system works automatically on every change.

- [x] Add a real pytest suite for the backend endpoints and AI service
- [x] Add a frontend type-check and build check
- [x] Add a GitHub Actions workflow that runs lint, tests, and build
- [x] Add a status badge to the README

Done when:

Tests and checks run automatically in CI on every push.

## Phase 13: Real AI Provider

Goal: connect a real model behind the existing AI boundary.

- [x] Add an Ollama provider (local) behind the provider interface
- [x] Add an OpenAI-compatible provider option
- [x] Select the provider with `MIRRAGE_AI_PROVIDER` without frontend changes
- [x] Add an assistant chat input to the dashboard
- [x] Handle provider errors gracefully

Done when:

The assistant returns real model responses through the same backend route.

## Phase 14: Live Weather

Goal: replace the weather stub with real data.

- [x] Add a `GET /api/info/weather` endpoint
- [x] Fetch live data from Open-Meteo (no API key required)
- [x] Cache responses to avoid rate limits
- [x] Connect the weather card to live data
- [x] Keep a clear fallback when weather is unavailable

Done when:

The weather card shows real local conditions through the backend.

## Future: Mobile Companion App

Goal (planned, from the project overview): a companion mobile app for remote control
and notifications. Tracked here so the roadmap matches the project vision, but not
started until the core system is stable.

## Current Focus

All defined phases are complete. The next planned milestone is the Mobile Companion
App; real voice and hardware integration follow once the core system is stable.
