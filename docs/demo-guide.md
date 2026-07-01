# Demo Guide

This is the short Mirrage demo flow I would use for a recruiter or portfolio
review. It is designed to be honest about what works now.

## Setup

Run backend and frontend:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload
```

```powershell
cd frontend
$env:VITE_MIRROR_MODE="true"
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## 60-90 Second Flow

1. Start on Mirror Mode home.

Say:

```text
This is Mirrage, a privacy-first smart mirror assistant. The home screen is meant
to stay quiet: time, weather, assistant state, light system status, and one
small proactive nudge when the day has useful context.
```

Point out that the current home screen is intentionally sparse. It should feel
more like information behind glass than a dashboard.

2. Open Weather focus.

Say:

```text
Weather comes through the FastAPI backend. If the provider is unavailable, the
screen falls back cleanly instead of breaking the mirror interface.
```

3. Open Assistant focus.

Say:

```text
The assistant has a provider boundary and runtime. It can run with the stub provider, Ollama,
or an OpenAI-compatible provider. Voice is push-to-talk in the browser for now,
and responses can be spoken with browser text-to-speech.
```

4. Type `Good morning`, `daily briefing`, or open Context.

Say:

```text
Daily context is generated locally by the backend from weather, calendar, and
local memory. The proactive briefing is rule-based and local too; it does not
automatically send personal memory to an external AI provider.
```

5. Open Calendar or Media.

Say:

```text
Calendar and Spotify are isolated behind backend service layers. OAuth and API
calls stay out of the frontend.
```

6. Return to Mirror Mode home.

Say:

```text
The system is built in phases: the core full-stack foundation is working, and the
next work is refinement, hardware testing, and stronger privacy controls.
```

## Notes For Recording

- Use Chrome or Edge for browser voice features.
- Keep the backend running so the status and context paths can show live data.
- Use `Good morning` to show the proactive assistant path.
- If Spotify or Google Calendar is not connected, say that those integrations are
  wired but not authenticated in this local demo.
- Do not claim wake word, smart home, vision, or physical hardware is complete.

## Suggested Video Title

```text
Mirrage Smart Mirror - Full-Stack Ambient Assistant Demo
```
