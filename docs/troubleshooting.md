# Troubleshooting

Common setup problems and how to fix them. For normal run steps see
[run-notes](run-notes.md).

## The dashboard shows "Backend unavailable"

The frontend cannot reach the backend.

- Confirm the backend is running: open http://127.0.0.1:8000/health.
- Confirm the frontend is pointing at the right URL. The default is
  `http://127.0.0.1:8000`; override it with `VITE_API_BASE_URL` in
  `frontend/.env`.
- If you see a CORS error in the browser console, the origin is not allowed. Add it
  to `MIRRAGE_ALLOWED_ORIGINS` in `.env` and restart the backend.

## `Activate.ps1 cannot be loaded because running scripts is disabled`

Windows PowerShell blocks script execution by default. Allow it for your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then activate the virtual environment again.

## `ModuleNotFoundError: No module named 'backend'`

`uvicorn` must be started from the repository root so the `backend` package is
importable. Run from the project root:

```powershell
uvicorn backend.app.main:app --reload
```

Not from inside the `backend/` folder.

## Port already in use (8000 or 5173)

Another process is holding the port. Find and stop it, or change the port.

```powershell
# find the process using port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess
# stop it (replace <pid>)
Stop-Process -Id <pid>
```

Or start the backend on a different port:

```powershell
uvicorn backend.app.main:app --reload --port 8001
```

## `npm install` fails or the dashboard will not start

- Confirm Node.js 20+ : `node --version`.
- Delete `frontend/node_modules` and `frontend/package-lock.json`, then run
  `npm install` again.

## Docker: `docker compose up` does nothing or errors

- Confirm Docker Desktop is running.
- Rebuild from scratch if images are stale:

```powershell
docker compose down
docker compose up --build
```

For production:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs frontend
```

Diagnosis before changing anything:

- if containers are not listed, Compose did not start
- if backend is unhealthy, check `/api/health/full`
- if frontend is unhealthy, check `http://127.0.0.1:5173/health`
- if Docker itself is down, fix Docker before changing Mirrage code

## Assistant replies with a stub or fallback message

This is expected when `MIRRAGE_AI_PROVIDER=stub`, or when a configured model
provider is unavailable. The reply is proof the assistant route is still working
through the backend and AI runtime.

Use `MIRRAGE_AI_PROVIDER=ollama` for a local Ollama model or
`MIRRAGE_AI_PROVIDER=openai` for an OpenAI-compatible API provider.

Check the runtime state:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/ai/runtime/status
Invoke-RestMethod http://127.0.0.1:8000/api/ai/providers
```

If `MIRRAGE_AI_LOCAL_ONLY=true`, cloud providers will not be selected. If Ollama
is selected but not running, Mirrage should fall back to the configured fallback
provider instead of crashing.

## OpenAI provider is not configured

`MIRRAGE_AI_PROVIDER=openai` needs an API key or compatible base URL.

Add the values to `.env`, then restart the backend:

```text
MIRRAGE_AI_PROVIDER=openai
MIRRAGE_AI_MODEL=gpt-4o-mini
MIRRAGE_AI_API_KEY=your-key
```

The provider status endpoint should show `configured: true` for `openai` after
the backend restarts.

## Ollama provider falls back to stub

This usually means Ollama is not reachable from the backend.

- Confirm Ollama is running.
- Confirm the model exists: `ollama list`.
- Pull the model if needed: `ollama pull llama3.2`.
- If Ollama runs on a non-default URL, set `MIRRAGE_AI_BASE_URL`.
- Restart the backend after changing `.env`.

Expected fallback behavior is still a `200` assistant response, usually from the
`stub` provider.

## Assistant stream returns one chunk

That is expected right now.

`POST /api/assistant/stream` uses Server-Sent Events, but providers do not expose
true token streaming in this phase. The endpoint currently returns:

```text
event: status
event: chunk
event: done
```

True provider token streaming is planned runtime refinement work.

## Assistant memory commands do not store anything

The first memory parser only handles direct memory phrases.

Try this exact command first:

```text
remember my favorite drink is coffee
```

Expected result:

- `provider` is `memory`
- `memory_action` is `stored`

Then check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/memory/summary
```

If the memory still does not appear:

- confirm the backend is running
- confirm `MIRRAGE_MEMORY_DATABASE_PATH` points to a writable path
- check that the backend process can create the `data/` folder

## Memory disappears after restart

Local memory is stored in `data/mirrage-memory.sqlite3`.

If you run locally, confirm that file exists after storing a memory. If you run
Docker, confirm `docker-compose.yml` still mounts `./data:/app/data`.

The SQLite file is private runtime data and is ignored by Git, so it will not
appear on GitHub.

## Database health check fails

First inspect full health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/full
```

Look for the `memory` check. If it reports an error:

- stop the backend
- copy the current `data/mirrage-memory.sqlite3` somewhere safe
- restore the latest known-good backup from `backups/`
- restart the backend
- check `/api/health/full` again

Do not delete the damaged database until a backup or copy exists.

## Frontend container is running but the mirror page is unavailable

Diagnosis:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs frontend
curl http://127.0.0.1:5173/health
```

Common causes:

- production frontend image was not rebuilt after `.env` changes
- port `5173` is already in use
- backend health never became healthy, so frontend waited during startup

Rebuild after changing frontend environment values:

```bash
docker compose -f docker-compose.prod.yml up -d --build frontend
```

## Reset local memory

Stop the backend first, then delete the SQLite file:

```powershell
Remove-Item data/mirrage-memory.sqlite3
```

Start the backend again. The database will be recreated the next time memory is
used.

## Push to talk says speech recognition is unsupported

The current voice foundation uses browser speech recognition. Use Chrome or Edge
for the first version. Some browsers do not expose the Web Speech API.

Typed assistant input still works when speech recognition is unavailable.

## Microphone permission is blocked

The browser needs permission before push-to-talk can listen.

- Open the site settings for `http://127.0.0.1:5173`.
- Allow microphone access.
- Refresh the page.
- Open the Assistant focus view and press `Push to talk` again.

If Windows blocks microphone access globally, enable microphone permission in
Windows privacy settings and restart the browser.

## Saying "Hey Mirrage" does nothing

The repo has the wake-word adapter and presence lifecycle, but it does not ship a
trained local wake-word model asset yet.

First test the adapter manually:

```powershell
$body = @{ phrase = "Hey Mirrage"; engine = "manual-test"; confidence = 0.9 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/wake-word/detect" -Method Post -ContentType "application/json" -Body $body
```

Expected result:

- backend returns `state: wake_detected`
- the frontend moves into Conversation Mode

If that works, the Mirrage backend/frontend path is working. The missing piece is
a local wake engine such as OpenWakeWord or Porcupine calling the adapter
endpoint after hearing the phrase.

## Presence stream is disconnected

The frontend subscribes to:

```text
http://127.0.0.1:8000/api/presence/events
```

If the UI says the presence stream is disconnected:

- confirm the backend is running
- open `http://127.0.0.1:8000/api/presence/status`
- check `VITE_API_BASE_URL`
- restart the frontend after changing env values

The app can still fall back to the latest snapshot, but live state transitions
need the event stream.

## Browser wake listener does not start

The browser wake listener is experimental and disabled by default:

```text
VITE_EXPERIMENTAL_BROWSER_WAKE_WORD=false
```

Only turn it on for local testing. Browser speech recognition may use browser or
operating-system services, so it is not the privacy-first production wake path.

## Voice hears nothing

- Confirm the correct microphone is selected in the browser or Windows.
- Speak after pressing `Push to talk`.
- Try a short phrase first.
- Check that no other app is holding exclusive microphone access.

## Assistant replies are not spoken aloud

The first text-to-speech layer uses browser speech synthesis.

- Confirm the Assistant focus view is not muted.
- Press `Test voice` in the voice output panel.
- Check the system volume and browser tab volume.
- Try Chrome or Edge if the browser does not expose speech output.
- If a voice was selected, switch back to `System default` and test again.

Typed replies should still appear even when speech output is unavailable.

## No voices appear in the voice dropdown

Voice lists come from the browser and operating system.

- Wait a moment after opening the Assistant focus view; some browsers load voices
  after the page renders.
- Refresh the page.
- Try Chrome or Edge.
- Use `System default` if the browser does not list named voices.

## Mute does not stop sound

- Press `Mute` once and wait a moment.
- Press `Stop speech` if the current utterance is still playing.
- Refresh the page if the browser speech engine gets stuck.

## A command does not open the expected view

The first command router only handles a small set of local screen commands.

- Try one of the known phrases from [run notes](run-notes.md#command-routing-checks).
- Confirm you are sending the message from the Assistant focus view.
- If the message is not recognized, it will go to the normal assistant endpoint.
- Keep command wording simple for now: weather, music/media, calendar, context,
  smart home, sensors, or assistant.

## Mirror Mode does not appear

Mirror Mode is off by default.

- Confirm `VITE_MIRROR_MODE=true` is set before starting the frontend.
- If Vite is already running, stop it and start it again after changing the env
  value.
- For Docker, confirm the variable is set in the shell or `.env` before running
  `docker compose up --build`.

Quick local check:

```powershell
cd frontend
$env:VITE_MIRROR_MODE="true"
npm run dev
```

Expected result: the home screen shows the large ambient clock, top-right
weather summary, and assistant orb.

## Mirror Mode dims too quickly or too slowly

Change the frontend timeout values:

```text
VITE_MIRROR_DIM_TIMEOUT_SECONDS=60
VITE_MIRROR_SLEEP_TIMEOUT_SECONDS=120
```

Restart the frontend after editing `.env`.

The dimming is a visual overlay. It does not change monitor brightness or power
settings.

## Mirror Mode startup shows planned or unavailable services

That can be normal in local development.

- `Calendar` is planned until Google Calendar credentials are configured and the
  account is connected.
- `Voice` depends on browser speech support and microphone permission.
- `Weather` can show unavailable if the backend or provider cannot be reached.
- `Context` can be partial if weather, Calendar, or memory has a fallback state.
- `Home` can show planned or unavailable if smart home is disabled or Home
  Assistant is not configured.

## Smart Home says disabled

That is expected until the feature is enabled.

Add these values to `.env`, then restart the backend:

```text
MIRRAGE_SMART_HOME_ENABLED=true
MIRRAGE_HOME_ASSISTANT_ENABLED=true
MIRRAGE_HOME_ASSISTANT_BASE_URL=http://homeassistant.local:8123
MIRRAGE_HOME_ASSISTANT_TOKEN=your-long-lived-token
```

Never commit the token.

## Smart Home says unconfigured

Mirrage smart home support is enabled, but Home Assistant details are missing or
incomplete.

- Confirm `MIRRAGE_HOME_ASSISTANT_BASE_URL` is reachable from the backend.
- Confirm `MIRRAGE_HOME_ASSISTANT_TOKEN` is set.
- Restart the backend after editing `.env`.
- Check `http://127.0.0.1:8000/api/smart-home/status`.

## Smart Home says unavailable

The backend tried Home Assistant and could not complete discovery.

- Confirm Home Assistant is running.
- Confirm the URL includes the scheme, for example `http://`.
- Confirm the token is valid.
- Confirm the backend machine can reach the Home Assistant machine on the local
  network.
- If using Docker, confirm the container can reach the same local address.

## Smart Home controls fail

Controls are intentionally limited.

- Lights and switches support on/off.
- Scenes support activate.
- Sensors are read-only.
- Locks, alarms, cameras, covers, garage doors, vacuums, climate, and media
  players are blocked in this phase.

Check one endpoint directly:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/smart-home/entities
```

If the entity is not listed there, Mirrage will not control it.

## Daily context is partial

This is usually expected. The context route combines weather, Calendar, and local
memory. If one source is unavailable, the response still loads with a fallback.

Check the raw context response:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/context/daily
```

Look at:

- `weather.status`
- `calendar.status`
- `memory.status`
- top-level `message`

Examples:

- `calendar.status: not_configured` means Google Calendar credentials are not set.
- `calendar.status: not_authenticated` means Calendar needs to be connected.
- `weather.status: unavailable` means the weather provider or network failed.
- `memory.status: empty` means local memory is working but has no stored context.

## Day question uses `provider: context`

That is expected for direct context questions such as `What is my day like?`.
Daily context questions are handled by deterministic backend logic before model
provider routing. This keeps local memory and personal context out of external
model providers for this phase.

AI-enhanced context summaries are not enabled yet.

## Morning or focus prompts use `provider: proactive`

That is expected for prompts such as:

- `Good morning`
- `Brief me`
- `What should I focus on today?`
- `What needs my attention?`

The proactive layer reads the local daily context response and returns a short
priority-based nudge before any model provider is called.

## Proactive nudge is unavailable

Check the raw endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/proactive/summary
```

Expected result:

- a JSON response appears even when context is partial or unavailable
- `status: unavailable` means Mirrage could not load local context right now
- `priority: none` means nothing needs attention or the fallback path is active

If the browser still shows no nudge:

- confirm the backend is running
- refresh the frontend
- check `VITE_API_BASE_URL` points at the backend
- open `/api/context/daily` and confirm context itself returns JSON

## Calendar says setup is needed

The backend did not receive Google Calendar credentials.

- Add `MIRRAGE_GOOGLE_CALENDAR_CLIENT_ID` and
  `MIRRAGE_GOOGLE_CALENDAR_CLIENT_SECRET` to `.env`.
- Confirm the Google Calendar API is enabled in Google Cloud.
- Confirm the backend was restarted after editing `.env`.
- For Docker, confirm the values are available to `docker compose`.

## Calendar OAuth fails or returns to an error state

- Confirm the Google OAuth client has this authorized redirect URI exactly:
  `http://127.0.0.1:8000/api/integrations/calendar/callback`.
- Confirm `MIRRAGE_GOOGLE_CALENDAR_REDIRECT_URI` matches that value.
- Confirm the backend is running at `http://127.0.0.1:8000`.
- If the backend restarted, connect Google Calendar again because the current
  token store is in process memory.

## Calendar events do not appear

- Confirm the connected Google account has events on the selected calendar.
- Confirm `MIRRAGE_GOOGLE_CALENDAR_ID` is `primary` or a valid calendar ID.
- Confirm `MIRRAGE_GOOGLE_CALENDAR_TIME_ZONE` matches the day you expect.
- Try `Refresh` in the Calendar focus view.

## Spotify says setup is needed

The backend did not receive Spotify credentials.

- Add `MIRRAGE_SPOTIFY_CLIENT_ID` and `MIRRAGE_SPOTIFY_CLIENT_SECRET` to `.env`.
- Confirm the backend was restarted after editing `.env`.
- For Docker, confirm the values are available to `docker compose`.

## Spotify OAuth fails or returns to an error state

- Confirm the Spotify app has this redirect URI exactly:
  `http://127.0.0.1:8000/api/integrations/spotify/callback`.
- Confirm `MIRRAGE_SPOTIFY_REDIRECT_URI` matches that value.
- Confirm the backend is running at `http://127.0.0.1:8000`.
- If the backend restarted, connect Spotify again because the current token store
  is in process memory.

## Spotify controls fail

- Start playback in the Spotify desktop, mobile, or web app first.
- Confirm there is an active Spotify device.
- Confirm the connected account can use playback controls.
- Try `Refresh` in the Media focus view after opening Spotify on a device.
