# Roadmap

Mirrage will be built in small steps. Each phase has a clear job so the project does not drift.

## Working Style

Small steps, clear purpose.

Each session should do one of these:

- turn a starter file into working code or useful documentation
- connect two parts of the system
- document a decision
- improve the mirror experience
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

## Phase 15: Ambient Interaction Layer

Goal: move Mirrage from a dashboard foundation toward an ambient assistant interface.

- [x] Simplify the home state
- [x] Add a focus view state model
- [x] Add weather focus view
- [x] Add assistant focus view
- [x] Add planned media focus view
- [x] Add a return-to-home flow
- [x] Keep future integrations clearly marked

Done when:

The mirror UI feels like a calm home interface that can expand into focused views
without pretending future voice, media, or smart home integrations are finished.

## Phase 16: Real Voice Foundation

Goal: talk to Mirrage without adding a wake word yet.

- [x] Add browser microphone access
- [x] Add push-to-talk in the assistant focus view
- [x] Add browser speech-to-text
- [x] Display the transcript in the assistant view
- [x] Send the transcript to the existing assistant endpoint
- [x] Display the assistant reply
- [x] Document voice architecture, setup, and troubleshooting

Done when:

The assistant focus view accepts a spoken request through push-to-talk and routes
the transcript through the existing assistant endpoint.

## Phase 17: Text To Speech

Goal: Mirrage talks back after the assistant route returns a reply.

- [x] Speak assistant responses aloud
- [x] Use browser speech synthesis first
- [x] Add a mute control
- [x] Add a browser voice selector
- [x] Add a voice settings panel
- [x] Keep text replies visible even when speech output is unavailable
- [x] Document setup and troubleshooting

Done when:

The assistant focus view can speak returned assistant replies through the
browser, and the user can mute or change the browser voice without changing the
backend.

## Phase 18: Command Routing

Goal: let simple assistant commands change the mirror view.

- [x] Add a frontend intent routing layer
- [x] Add a UI action object for focus view changes
- [x] Route weather commands to the Weather focus view
- [x] Route music/media commands to the Media focus view
- [x] Route assistant commands to the Assistant focus view
- [x] Add assistant action responses for routed commands
- [x] Keep normal assistant messages going to the backend endpoint
- [x] Document the command routing architecture

Done when:

Typing or speaking a known command can open the correct focus view, while
unknown messages still use the existing assistant route.

## Phase 19: Spotify Integration

Goal: control real Spotify playback from the Media focus view.

- [x] Add Spotify OAuth through the backend
- [x] Add currently playing endpoint
- [x] Return album artwork, artist, album, device, and progress
- [x] Add play/pause endpoint
- [x] Add next/previous endpoints
- [x] Connect Media focus view to real Spotify state
- [x] Keep Spotify API calls isolated in the backend service layer
- [x] Document setup, scopes, and limitations

Done when:

The Media focus view can connect a Spotify account, show current playback, show
album artwork, and control playback through Mirrage backend endpoints.

## Phase 20: Calendar Integration

Goal: make Mirrage useful as a daily schedule assistant.

- [x] Add Google Calendar OAuth through the backend
- [x] Add a Calendar service layer
- [x] Add today's schedule endpoint
- [x] Add upcoming events endpoint
- [x] Add Calendar focus view
- [x] Add assistant command for `What is on my calendar today?`
- [x] Keep Google API calls isolated in the backend service layer
- [x] Document setup, scope, and limitations

Done when:

The Calendar focus view can connect a Google account, show today's events, show
upcoming events, and the assistant can answer what is on the calendar today.

## Phase 21: Memory Layer

Goal: give Mirrage a local place to remember useful context.

- [x] Add a local SQLite database
- [x] Add memory types for preferences, facts, goals, and routines
- [x] Add backend routes to create, list, summarize, and update memories
- [x] Route direct assistant memory commands through local storage
- [x] Keep memory commands local before AI provider calls
- [x] Mount the Docker `data/` folder so memory can survive container restarts
- [x] Document the memory architecture, API, setup, and reset path
- [x] Add backend tests for memory routes and assistant memory commands

Done when:

The assistant can store, retrieve, and update simple local memories without
sending those memory commands to a model provider.

## Phase 22: Personal Context System

Goal: give Mirrage a backend-owned daily context layer.

- [x] Add a context aggregation service
- [x] Combine weather, Calendar, and local memory into one daily context response
- [x] Add `GET /api/context/daily`
- [x] Add provider-independent assistant replies for daily briefing and focus prompts
- [x] Add Context focus view in the frontend
- [x] Route typed and spoken context commands to the Context view
- [x] Keep context responses deterministic and local before AI provider calls
- [x] Document context architecture, fallback behavior, privacy boundary, and tests
- [x] Add backend tests for context response, fallbacks, assistant commands, and memory goals

Done when:

Mirrage can answer daily-context questions from backend-owned weather, Calendar,
and memory data without requiring a model provider.

## Phase 26: Mirror Mode

Goal: make Mirrage feel like a real wall-mounted mirror interface.

- [x] Add `VITE_MIRROR_MODE=true` as an optional frontend display mode
- [x] Keep normal development mode unchanged by default
- [x] Add a minimal ambient home state for mirror use
- [x] Show top-left time/date, top-right weather, assistant presence, and subtle status
- [x] Keep Weather, Assistant, Media, Calendar, and Context focus views working
- [x] Add inactivity dimming and automatic return to home
- [x] Add light burn-in movement for static elements
- [x] Add a startup sequence with non-blocking service checks
- [x] Document setup, behavior, and limitations

Done when:

Mirror Mode can run locally or through Docker as the wall-display version of the
existing app, without claiming wake word, smart home, vision, or physical
hardware support.

## Phase 26.5: Portfolio Assets

Goal: make the project easier to review quickly.

- [x] Add a recruiter-friendly demo guide
- [x] Add website update notes and an honest AI-assisted development note
- [x] Add README status table and demo section
- [x] Add a screenshot gallery section for the main views
- [x] Track the expected screenshot asset names

Done when:

A visitor can understand the current product, what is working, what is still
planned, and how to demo the project without reading the entire codebase.

## Phase 27/29: Ambient Intelligence Experience

Goal: make Mirror Mode feel more like an ambient product experience and less
like a regular dashboard.

- [x] Refine Mirror Mode toward a calmer premium mirror UI
- [x] Improve assistant presence states for idle, listening, thinking, speaking, and error
- [x] Make the Mirror Mode Assistant focus view voice-first
- [x] Keep detailed assistant provider/debug information in normal development mode
- [x] Add a backend proactive assistant service
- [x] Add `GET /api/proactive/summary`
- [x] Build proactive summaries from existing daily context instead of a model provider
- [x] Route morning, briefing, focus, reminder, and attention prompts through the proactive layer
- [x] Show a subtle proactive nudge on the Mirror Mode home screen
- [x] Surface the proactive briefing inside the Context focus flow
- [x] Keep proactive logic deterministic and local for privacy
- [x] Add backend tests for proactive endpoint, fallback behavior, goals, and assistant commands
- [x] Document the proactive assistant boundary and manual checks

Done when:

Mirror Mode has a quieter product feel, and Mirrage can surface a small local
daily nudge without sending private context to an AI provider.

## Phase 30A: Ambient Intelligence Redesign

Goal: remove the dashboard feeling from the visible product.

- [x] Redesign Mirror Home around floating time, date, weather, and assistant status
- [x] Remove card and grid styling from the main React view markup
- [x] Replace the assistant orb as the main identity with a quieter presence line
- [x] Rework Assistant focus as a voice-first conversation mode
- [x] Rework Weather focus as ambient type instead of a weather card
- [x] Rework Context focus as a Daily Briefing instead of metric cards
- [x] Rework Calendar disconnected state as simple onboarding text
- [x] Rework Media disconnected state without a setup panel
- [x] Keep the focus views reachable by URL and the quiet word navigation
- [x] Refresh the screenshot set for the new mirror-first UI

Done when:

The first impression is no longer a web dashboard. The screen should feel like a
smart mirror surface that only shows enough information to be useful.

## Future: Voice Interaction

- [ ] Wake phrase
- [ ] Backend or local speech-to-text option
- [ ] Assistant intent handling
- [ ] Backend or local text-to-speech option
- [ ] Return-to-home voice flow

## Future: Spotify Refinement

- [ ] Persist Spotify token securely across backend restarts
- [ ] Add device picker
- [ ] Add better handling for Premium/device errors
- [ ] Add voice commands for playback controls

## Future: Calendar Refinement

- [ ] Persist Calendar token securely across backend restarts
- [ ] Add event detail view
- [ ] Add tomorrow and week schedule commands
- [ ] Add create/update event support behind confirmations
- [ ] Handle account permissions clearly

## Future: Memory Refinement

- [ ] Add a memory editing UI
- [ ] Add delete/archive controls
- [ ] Add confirmation prompts for sensitive memories
- [ ] Add optional encryption or OS keychain support
- [ ] Add safer automatic memory extraction, only after clear controls exist

## Future: Context Refinement

- [ ] Add richer focus scoring
- [ ] Add tomorrow and week briefings
- [ ] Add Spotify/media context once playback state is stable enough
- [ ] Add explicit opt-in AI-enhanced briefings
- [ ] Add UI controls for what context sources are included

## Future: Smart Home Integration

- [ ] Pick the first home control target
- [ ] Add backend action boundaries
- [ ] Add confirmation for risky actions

## Future: Physical Mirror Build

- [ ] Test display brightness through mirror material
- [ ] Choose final display and mirror material
- [ ] Test heat and airflow
- [ ] Build the first frame

## Future: Home Installation

- [ ] Plan wall mounting
- [ ] Plan cable routing
- [ ] Test daily reliability

## Current Focus

Phase 30A is the current milestone. Current focus is testing the redesigned
ambient interface, then refining context scoring, memory controls, and privacy
settings without adding visual clutter.
