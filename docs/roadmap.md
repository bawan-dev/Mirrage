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

- [ ] Define voice status fields
- [ ] Return voice status from the backend
- [ ] Display voice status in the dashboard
- [ ] Document future wake word, speech-to-text, and text-to-speech options

Done when:

The app has a clear place for voice work before microphone features are added.

## Phase 7: Docker Development Setup

Goal: make the project easier to run as a full stack.

- [ ] Add frontend Dockerfile
- [ ] Add backend Dockerfile
- [ ] Wire services in Docker Compose
- [ ] Document Docker run commands
- [ ] Confirm frontend and backend ports

Done when:

`docker compose up` has a clear path, even if the setup is still development-focused.

## Phase 8: Hardware Planning

Goal: turn the physical mirror idea into a real build plan.

- [ ] List candidate display options
- [ ] List mirror material options
- [ ] Plan compute device choices
- [ ] Plan microphone and speaker options
- [ ] Write first wiring notes
- [ ] Track open hardware risks

Done when:

The hardware side has enough planning to guide a real prototype.

## Phase 9: Project Polish

Goal: make Mirrage easy to run, explain, and improve.

- [ ] Add dashboard screenshots
- [ ] Add architecture diagram assets
- [ ] Improve project visuals
- [ ] Add short run notes
- [ ] Add setup troubleshooting
- [ ] Keep the roadmap current

Done when:

A new reader can understand what Mirrage is, what works, and what is coming next.

## Current Focus

Phase 5 is complete enough for now. Current focus is Phase 6: Voice Status.
