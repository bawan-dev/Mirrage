# Troubleshooting

## Agent Workspace Is Disabled

This is the safe default. Set `MIRRAGE_AGENTS_ENABLED=true` and restart the
backend. Check `/api/agents/status` with a trusted-device bearer token.

If the workspace reports authentication failure:

- use a trusted device token;
- if the device type is `mirror`, start a human session and send
  `X-Mirrage-Human-Session`;
- confirm the user has `agents.use`, `agents.plan`, and the relevant execution
  and service permissions.

## Agent Plan Is Rejected

Plans fail closed when a tool is unknown, arguments do not match its schema, the
agent type cannot use that tool, the step limit is exceeded, or an effective
permission is missing. Check the safe run error and audit decision. Do not work
around rejection by adding a generic shell, file, URL, or Home Assistant tool.

Guests can create a draft but do not receive execution permissions by default.
Relationships do not change this.

## Agent Is Waiting For Approval

Every write or smart-home action requires a different authenticated user with
`agents.approve`. The requester cannot approve their own step. In a single-owner
installation, use read-only agents until a legitimate separate approver is
configured.

If the approval disappeared, it may have expired after
`MIRRAGE_AGENT_APPROVAL_TTL_SECONDS` or been cancelled with its run. Create a
new run rather than modifying the old approval record.

## Agent Timed Out Or Stopped

Check:

- `MIRRAGE_AGENT_MAX_RUNTIME_SECONDS`;
- the registered tool timeout;
- provider availability;
- whether the run was paused or cancelled;
- whether permissions changed after planning.

The executor rechecks policy before each step. A new explicit deny can stop an
already planned run. Side effects are not retried.

## Protected API Returns 401

The route did not receive a valid active trusted-device token. Check that the
request uses `Authorization: Bearer <DEVICE_TOKEN>`, the user and device are
active, and the token has not been revoked. A name or role header is not a
replacement for authentication.

For deliberate local-only work, set:

```powershell
$env:MIRRAGE_IDENTITY_DEV_BYPASS="true"
```

Restart the backend. This bypass is low-assurance, audited, and rejected in
production.

## Protected API Returns 403

Authentication succeeded, but the role/override policy or global safety policy
denied the action. Read the response `permission` and `policy_id`, then check
[Permissions](permissions.md). Do not work around a 403 in the frontend or AI
prompt.

If the authenticated device is registered as `mirror`, a private route also
requires `X-Mirrage-Human-Session`. Open the normal-mode Identity view and use
**Activate selected user**, or call `POST /api/sessions`. An expired or ended
session must be replaced; it cannot be refreshed from its hash.

## Profile Or Relationship View Is Unavailable

Check `/api/identity/me` first. The principal needs the relevant profile or
relationship permission and, on a mirror device, an active human session.
Profile management intentionally stays outside Mirror Mode.

If a relationship proposal returns `409`, check for an existing pending or
active relationship between the same two users. Self-relationships and
duplicate pairs are rejected.

## A Profile Field Is Missing From The Directory

This is normally the privacy filter working. The field owner controls its
visibility. Installation owners do not receive an automatic privacy bypass.
Confirm the field is marked `relationship`, `household`, or `public` and that
the corresponding active relationship or household condition exists.

## Shared Context Cannot Be Shared

The item must belong to the current user and the target must be an active user.
An active relationship is required only when access depends on `relationship`
visibility. Shared context is private when created. Obvious credential,
financial, medical, and security-code categories are rejected, but the filter
is not a substitute for keeping secrets out of the feature.

## Production Fails With Identity Startup Error

Production requires enabled, enforced identity mode, no development bypass, and
at least one active owner. Run the documented owner bootstrap against the
production data volume before the first normal start. Invalid token length, TTL,
retention, or database paths also fail startup.

## Trusted Device Token Was Lost

Raw tokens cannot be retrieved from SQLite or the API. Enroll a replacement from
an active owner device, then revoke the lost device. If no owner device remains,
stop the service and follow the controlled restore process in
[Trusted devices](trusted-devices.md).

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

## Demo data appears instead of real integrations

Check whether demo mode is enabled:

```powershell
$env:VITE_MIRRAGE_DEMO_MODE
```

Expected production value:

```text
false
```

Fix:

- stop the frontend dev server
- unset the variable or set `VITE_MIRRAGE_DEMO_MODE=false`
- restart `npm run dev`

Demo mode is only for screenshots and portfolio walkthroughs. It intentionally
uses fake weather, Calendar, Spotify, Smart Home, memory, and context data.

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
$ownerHeaders = @{ Authorization = "Bearer <OWNER_DEVICE_TOKEN>" }
Invoke-RestMethod http://127.0.0.1:8000/api/health/full -Headers $ownerHeaders
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

The repo has the local wake engine boundary, OpenWakeWord provider support, and
presence lifecycle, but it does not ship a trained local wake-word model asset.

Check the local engine status first:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/wake-word/status
```

Default local development should report `enabled: false`. If enabled but
unconfigured, check `message`, `model_configured`, and `error_message`.

First test the adapter manually:

```powershell
$body = @{ phrase = "Hey Mirrage"; engine = "manual-test"; confidence = 0.9 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/wake-word/detect" -Method Post -ContentType "application/json" -Body $body
```

Expected result:

- backend returns `state: wake_detected`
- the frontend moves into Conversation Mode

If that works, the Mirrage backend/frontend path is working. The missing piece is
a real local model and microphone run.

For OpenWakeWord setup notes, see [wake-engine](wake-engine.md) and
[openwakeword](openwakeword.md).

## Wake engine says unconfigured

The local wake engine is enabled but cannot start.

Common causes:

- `MIRRAGE_WAKE_ENGINE_MODEL_PATH` is blank
- the model file does not exist on disk
- sensitivity is outside `0.0` to `1.0`
- sample rate or frame size is invalid
- provider is not `openwakeword`

The backend should stay online. Check:

```powershell
$ownerHeaders = @{ Authorization = "Bearer <OWNER_DEVICE_TOKEN>" }
Invoke-RestMethod http://127.0.0.1:8000/api/health/full -Headers $ownerHeaders
```

Look for the `wake_engine` check.

## Wake engine starts but immediately stops

This usually means the optional runtime or audio device failed.

- install `openwakeword`, `sounddevice`, and `numpy` on the target device
- confirm the microphone is visible to the OS
- set `MIRRAGE_WAKE_ENGINE_MICROPHONE` if the default device is wrong
- run the backend directly on the host before solving Docker audio mounts

The backend logs should include a wake engine startup or microphone failure
event, but never raw audio.

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
weather summary, and assistant presence.

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
- `Voice` depends on browser speech support, microphone permission, and local
  wake engine configuration if that path is enabled.
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

## Display is too dim behind mirror material

This is a hardware fit problem, not a frontend bug.

- Test the display without mirror material first.
- Increase display brightness only for testing; watch heat after increasing it.
- Try the mirror material in daytime and nighttime room light.
- Test a lighter tint or different two-way material.
- Confirm the UI uses Mirror Mode with a black background and high-contrast text.

Do not order final-size mirror material until the sample is readable with the
actual display.

## Mirror frame gets too warm

Stop the long-running test and inspect the physical layout.

- Confirm display vents are not blocked.
- Add bottom and top ventilation.
- Move the mini PC away from the hottest display area.
- Keep power bricks outside sealed cavities.
- Check that cables are not pressed against hot electronics.
- Run another 1 hour and 4 hour test before mounting.

## Microphone works on desk but not inside the frame

Microphone placement is part of the hardware build.

- Move the microphone near the bottom edge of the frame.
- Test with the mirror material installed.
- Keep it away from speakers where possible.
- Try a USB conference microphone or microphone array.
- Check `/api/wake-word/status` for local wake engine state.

Do not hide the microphone permanently until wake-word and speech tests pass in
the actual room.

## Speakers sound muffled

- Do not fully seal speakers behind wood.
- Add side or bottom openings for sound.
- Reduce frame vibration with rubber isolation.
- Use wired USB or 3.5mm speakers before trying Bluetooth.
- Keep the speaker path serviceable so replacement is possible.

## Mirror cannot be serviced after mounting

The frame design needs to change.

Mirrage should allow access to:

- mini PC power and USB ports
- display power/video cables
- microphone and speaker cables
- Ethernet cable
- power plug or power strip

A sealed frame may look clean, but it will make repairs, updates, and part
replacement painful.
