# Run Notes

Short, practical notes for getting Mirrage running. For the full explanation see the
[README](../README.md). For problems see [troubleshooting](troubleshooting.md).

## Prerequisites

| Tool | Version | Used for |
| --- | --- | --- |
| Python | 3.11+ | Backend (FastAPI) |
| Node.js | 20+ | Frontend (React + Vite) |
| Docker | optional | Running the full stack together |

## Fastest path: Docker

This runs the frontend and backend together with one command.

```powershell
docker compose up --build
```

Then open:

- Dashboard: http://127.0.0.1:5173
- Backend health: http://127.0.0.1:8000/health

Stop with `Ctrl + C`, then `docker compose down`.

## Local path: run each service

### 1. Backend (terminal one)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Verify: http://127.0.0.1:8000/health returns
`{"service":"mirrage-api","status":"online"}`.

Interactive API docs are available at http://127.0.0.1:8000/docs.

### 2. Frontend (terminal two)

```powershell
cd frontend
npm install
npm run dev
```

Verify: http://127.0.0.1:5173 shows the dashboard. The System and Voice cards should
read live values from the backend; if the backend is not running they show
"Backend unavailable".

## Browser voice setup

Voice input is push-to-talk inside the Assistant focus view. Voice output uses
browser speech synthesis.

1. Open http://127.0.0.1:5173.
2. Open the Assistant focus view.
3. Press `Push to talk`.
4. Allow microphone permission when the browser asks.
5. Speak a short request.

Expected result:

- the transcript appears in the assistant view
- the transcript is sent to the existing assistant endpoint
- the assistant reply appears in the message thread
- the assistant reply is spoken aloud unless speech output is muted

This works best in Chrome or Edge because the current foundation uses browser
speech recognition and browser speech synthesis. There is no wake word yet.

## Speech output setup

Inside the Assistant focus view:

1. Use `Mute` to stop assistant replies from speaking aloud.
2. Use the `Voice` dropdown to choose a browser voice when voices are available.
3. Use `Test voice` to confirm the selected voice can speak.
4. Use `Stop speech` if a reply is currently speaking.

Expected result:

- selected voices affect future spoken replies
- mute stops current speech and keeps future replies quiet
- typed assistant messages and push-to-talk messages both use the same speech
  output path

## Command routing checks

The assistant can route a few local screen commands without calling a model.

From the Assistant focus view, type each command:

| Command | Expected result |
| --- | --- |
| `What is the weather?` | Weather focus view opens |
| `Show my music` | Media focus view opens |
| `What is on my calendar today?` | Calendar focus view opens and replies with today's schedule |
| `daily briefing` | Context focus view opens and replies with provider-independent daily context |
| `What should I focus on today?` | Context focus view opens and replies with suggested focus |
| `Open assistant` | Assistant focus view opens |

The assistant also adds a short action response to the message thread. Commands
that are not recognized still go to the backend assistant endpoint.

## Daily context checks

Open the Context focus view from the dashboard, or ask from the Assistant focus
view:

```text
daily briefing
```

Expected result:

- Context focus view opens
- the assistant reply uses `provider: context`
- the reply mentions weather, calendar, memory, and suggested focus when those
  sources are available

Check the backend endpoint directly:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/context/daily
```

Expected result:

- top-level `status` is `ready`, `partial`, or `unavailable`
- `weather`, `calendar`, `memory`, and `suggested_focus` fields are present
- unavailable sources report a clear status instead of crashing

Assistant context check:

```powershell
$body = @{ message = "What should I focus on today?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected result:

- `provider` is `context`
- `context_action` is `focus`
- the reply includes `Suggested focus`

## Memory checks

Memory is local. The default database file is:

```text
data/mirrage-memory.sqlite3
```

Store a memory through the assistant route:

```powershell
$body = @{ message = "remember my favorite drink is coffee" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected result:

- `provider` is `memory`
- `memory_action` is `stored`
- the reply says the memory was remembered

Recall memory:

```powershell
$body = @{ message = "what do you remember about me?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected result:

- `provider` is `memory`
- `memory_action` is `retrieved`
- the reply includes `favorite drink: coffee`

Check the raw summary:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/memory/summary
```

Expected result:

- `count` is at least `1`
- `preferences` includes the `favorite drink` memory

## Spotify setup check

Spotify needs credentials before the Media focus view can connect.

1. Create a Spotify app.
2. Add this redirect URI to the Spotify app:

```text
http://127.0.0.1:8000/api/integrations/spotify/callback
```

3. Add credentials to `.env`:

```powershell
MIRRAGE_SPOTIFY_CLIENT_ID=your-client-id
MIRRAGE_SPOTIFY_CLIENT_SECRET=your-client-secret
MIRRAGE_SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/integrations/spotify/callback
MIRRAGE_FRONTEND_URL=http://127.0.0.1:5173
```

4. Restart the backend.
5. Open the Media focus view.
6. Click `Connect Spotify`.
7. Approve the Spotify OAuth request.

Expected result:

- Media focus view shows the current Spotify track if playback is active
- album artwork appears when Spotify returns artwork
- `Play`, `Pause`, `Next`, and `Previous` call the backend Spotify routes

Spotify controls need an active Spotify device. Some player control endpoints
also require Spotify Premium.

## Google Calendar setup check

Calendar needs Google OAuth credentials before the Calendar focus view can
connect.

1. Enable Google Calendar API in Google Cloud.
2. Create an OAuth client ID for a web application.
3. Add this authorized redirect URI:

```text
http://127.0.0.1:8000/api/integrations/calendar/callback
```

4. Add credentials to `.env`:

```powershell
MIRRAGE_GOOGLE_CALENDAR_CLIENT_ID=your-client-id
MIRRAGE_GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret
MIRRAGE_GOOGLE_CALENDAR_REDIRECT_URI=http://127.0.0.1:8000/api/integrations/calendar/callback
MIRRAGE_GOOGLE_CALENDAR_ID=primary
MIRRAGE_GOOGLE_CALENDAR_TIME_ZONE=Europe/London
MIRRAGE_FRONTEND_URL=http://127.0.0.1:5173
```

5. Restart the backend.
6. Open the Calendar focus view.
7. Click `Connect Google Calendar`.
8. Approve the Google OAuth request.

Expected result:

- Calendar focus view shows today's events if the account has events today
- upcoming events appear in the side panel
- asking `What is on my calendar today?` in the Assistant focus view returns a
  schedule answer

## Configuration

Copy the example environment file and adjust as needed:

```powershell
Copy-Item .env.example .env
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `MIRRAGE_API_PORT` | `8000` | Backend port |
| `MIRRAGE_FRONTEND_PORT` | `5173` | Frontend dev server port |
| `MIRRAGE_AI_PROVIDER` | `stub` | Which AI provider the assistant uses |
| `MIRRAGE_ALLOWED_ORIGINS` | localhost:5173 | CORS origins the backend accepts |
| `MIRRAGE_MEMORY_DATABASE_PATH` | `data/mirrage-memory.sqlite3` | Local SQLite memory path |

The frontend reads its backend URL from `VITE_API_BASE_URL`
(see [frontend/.env.example](../frontend/.env.example)); it defaults to
`http://127.0.0.1:8000`.

## Quick health check from the terminal

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/system/status
```
