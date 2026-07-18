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
$env:VITE_MIRRAGE_DEMO_MODE="true"
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
This is Mirrage, a privacy-first ambient AI mirror platform. The home screen is
meant to stay quiet: time, weather, assistant presence, and one small proactive
nudge when the day has useful context.
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
The assistant is designed to feel voice-first. It has visible states for idle,
listening, processing, speaking, returning, sleeping, and error. The backend owns
the assistant runtime and presence lifecycle; browser push-to-talk and browser
speech output work today.
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
v1 is the first complete software release: the full-stack foundation is working,
the mirror UI has been polished for demo use, and the remaining work is target
hardware validation, real wake-word model testing, and deeper provider
configuration.
```

7. For a technical v2 walkthrough, restart normal mode and open Identity.

```text
Phase 38 adds trusted-device authentication and backend-owned permissions. The
sample users are demo-only, raw tokens are never part of demo data, and the
Mirror home does not expose administration controls.
```

## Notes For Recording

- Demo mode is explicit. Use `VITE_MIRRAGE_DEMO_MODE=true` only for fake
  portfolio data.
- Use Chrome or Edge for browser voice features.
- Keep the backend running so the status and context paths can show live data.
- Use `Good morning` to show the proactive assistant path.
- If Spotify or Google Calendar is not connected, say that those integrations are
  wired but not authenticated in this local demo.
- Do not claim hands-free wake word, real smart home hardware, vision, or
  physical mirror installation is complete.

## Refresh Screenshots

Start the frontend in mirror demo mode first:

```powershell
cd frontend
$env:VITE_MIRROR_MODE="true"
$env:VITE_MIRRAGE_DEMO_MODE="true"
$env:VITE_MIRROR_STARTUP_SECONDS="1"
npm run dev
```

Then capture each view from another terminal:

```powershell
cd frontend
npx playwright screenshot --viewport-size "1920,1080" --wait-for-timeout 1800 http://127.0.0.1:5173 ..\assets\screenshots\mirror-home.png
npx playwright screenshot --viewport-size "1920,1080" --wait-for-timeout 1800 http://127.0.0.1:5173?view=assistant ..\assets\screenshots\assistant-focus.png
npx playwright screenshot --viewport-size "1920,1080" --wait-for-timeout 1800 http://127.0.0.1:5173?view=weather ..\assets\screenshots\weather-focus.png
npx playwright screenshot --viewport-size "1920,1080" --wait-for-timeout 1800 http://127.0.0.1:5173?view=calendar ..\assets\screenshots\calendar-focus.png
npx playwright screenshot --viewport-size "1920,1080" --wait-for-timeout 1800 http://127.0.0.1:5173?view=context ..\assets\screenshots\context-focus.png
npx playwright screenshot --viewport-size "1920,1080" --wait-for-timeout 1800 http://127.0.0.1:5173?view=media ..\assets\screenshots\media-focus.png
npx playwright screenshot --viewport-size "1920,1080" --wait-for-timeout 1800 http://127.0.0.1:5173?view=smart-home ..\assets\screenshots\smart-home-focus.png
```

Capture the Identity view in normal demo mode, not Mirror Mode:

```powershell
$env:VITE_MIRROR_MODE="false"
npx playwright screenshot --viewport-size "1440,1000" --wait-for-timeout 1800 http://127.0.0.1:5173?view=identity ..\assets\screenshots\identity-admin.png
```

## Suggested Video Title

```text
Mirrage Smart Mirror - Full-Stack Ambient Assistant Demo
```
