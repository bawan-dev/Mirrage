# Run Notes

## Phase 38 Identity And Safety Manual Validation

These commands use placeholders. Do not paste a real token into committed files,
screenshots, issue comments, or logs.

1. Initialize the identity database.

```powershell
python -c "from backend.app.services.identity_store import identity_store; identity_store.initialize(); print(identity_store.database_path())"
```

Expected: `data\mirrage-identity.sqlite3` or the configured local path.

2. Bootstrap the first owner and mirror device while no users exist.

```powershell
python -m backend.app.identity_cli bootstrap-owner `
  --name "Owner Name" --device-name "Primary Mirror"
```

Expected: owner/device public UUIDs and one raw token. The command refuses a
second bootstrap.

3. Authenticate the trusted mirror device.

```powershell
$ownerToken = "<OWNER_DEVICE_TOKEN>"
$ownerHeaders = @{ Authorization = "Bearer $ownerToken" }
```

4. Read the backend principal.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/identity/me -Headers $ownerHeaders
```

Expected: `authenticated: true`, role `owner`, method `trusted_device`; no token
or token hash.

5. Create a family user.

```powershell
$familyBody = @{ display_name = "Sample Family"; role = "family" } | ConvertTo-Json
$family = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/identity/users `
  -Headers $ownerHeaders -ContentType "application/json" -Body $familyBody
```

6. Create a guest user.

```powershell
$guestBody = @{ display_name = "Sample Guest"; role = "guest"; household_member = $false } | ConvertTo-Json
$guest = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/identity/users `
  -Headers $ownerHeaders -ContentType "application/json" -Body $guestBody
```

7. Enroll family and guest test devices. Each token is returned once.

```powershell
$familyDeviceBody = @{
  user_id = $family.public_id; display_name = "Family Test Phone"
  device_type = "phone"; trust_level = "trusted"
} | ConvertTo-Json
$familyDevice = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/identity/devices `
  -Headers $ownerHeaders -ContentType "application/json" -Body $familyDeviceBody
$familyHeaders = @{ Authorization = "Bearer $($familyDevice.token)" }

$guestDeviceBody = @{
  user_id = $guest.public_id; display_name = "Guest Test Phone"
  device_type = "phone"; trust_level = "limited"
} | ConvertTo-Json
$guestDevice = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/identity/devices `
  -Headers $ownerHeaders -ContentType "application/json" -Body $guestDeviceBody
$guestHeaders = @{ Authorization = "Bearer $($guestDevice.token)" }
```

8. List role permissions.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/identity/roles -Headers $ownerHeaders
```

Expected: five roles. Family has low-risk home control; guest does not.

9. Confirm guest smart-home control is denied before the provider call.

```powershell
try {
  Invoke-RestMethod -Method Post `
    -Uri http://127.0.0.1:8000/api/smart-home/entities/light.office/turn-on `
    -Headers $guestHeaders
} catch { $_.Exception.Response.StatusCode.value__ }
```

Expected: `403`.

10. Confirm family passes authorization for a low-risk action.

```powershell
try {
  Invoke-RestMethod -Method Post `
    -Uri http://127.0.0.1:8000/api/smart-home/entities/light.office/turn-on `
    -Headers $familyHeaders
} catch { $_.Exception.Response.StatusCode.value__ }
```

Expected: not `401` or `403`. A configured provider returns success; disabled or
unavailable Home Assistant may return `503` or `502` after authorization.

11. Revoke the guest device and confirm its token stops working.

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/identity/devices/$($guestDevice.device.public_id)/revoke" `
  -Headers $ownerHeaders
try {
  Invoke-RestMethod http://127.0.0.1:8000/api/identity/me -Headers $guestHeaders
} catch { $_.Exception.Response.StatusCode.value__ }
```

Expected: `401` from `/api/identity/me`.

12. Create and decide an approval request.

```powershell
$approvalBody = @{
  action = "future.medium.action"; resource_type = "future_resource"
  resource_id = "sample"; risk_level = "medium"; reason = "Owner review"
} | ConvertTo-Json
$approval = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/approvals `
  -Headers $familyHeaders -ContentType "application/json" -Body $approvalBody
$decisionBody = @{ reason = "Reviewed locally" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/approvals/$($approval.public_id)/approve" `
  -Headers $ownerHeaders -ContentType "application/json" -Body $decisionBody
```

Expected: `approved`. This record does not unlock blocked smart-home domains.

13. Read recent audit events as owner.

```powershell
$audit = Invoke-RestMethod `
  "http://127.0.0.1:8000/api/audit/events?limit=25" -Headers $ownerHeaders
$audit.items | Select-Object timestamp,event_type,action,result
```

14. Confirm secrets are absent from health, audit, and safe device responses.

```powershell
$safePayload = @(
  Invoke-RestMethod http://127.0.0.1:8000/api/health/full -Headers $ownerHeaders
  Invoke-RestMethod http://127.0.0.1:8000/api/identity/devices -Headers $ownerHeaders
  $audit
) | ConvertTo-Json -Depth 8
$safePayload.Contains($ownerToken)
$safePayload -match 'token_hash|home_assistant_token|memory_value|transcript'
```

Expected: both checks return `False`.

15. Back up and explicitly restore identity data.

```powershell
python -m backend.app.identity_cli backup
python -m backend.app.identity_cli restore --path "backups/<IDENTITY_BACKUP>.sqlite3"
```

Expected: separate `mirrage-identity-*.sqlite3` file, validated restore, and
backup/restore audit events.

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

## Production path: Docker Compose plus systemd

For a dedicated mirror device, use the production Compose file:

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

Check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
$ownerHeaders = @{ Authorization = "Bearer <OWNER_DEVICE_TOKEN>" }
Invoke-RestMethod http://127.0.0.1:8000/api/health/full -Headers $ownerHeaders
```

Startup-on-boot is documented in [deployment](deployment.md). Normal maintenance
is documented in [operations](operations.md).

Hardware build planning is documented in
[physical build](../hardware/physical-build.md) and
[testing checklist](../hardware/testing-checklist.md).

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

Verify: http://127.0.0.1:5173 shows the local mirror interface. Backend-aware
status text should read live values from the API; if the backend is not running,
the interface should show a clear unavailable state instead of crashing.

## Mirror Mode check

Mirror Mode is optional. Use it when testing the wall-display version of the UI.

```powershell
cd frontend
$env:VITE_MIRROR_MODE="true"
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Expected result:

- a short Mirrage startup screen appears
- the ambient home shows a large clock, weather summary, assistant presence, and
  one subtle proactive nudge
- Weather, Assistant, Media, Calendar, Context, and Smart Home focus views still open
- `Close` or `Esc` returns to the ambient home
- after inactivity, the screen dims and then returns to the home state

## Portfolio demo mode

Use demo mode only when you want stable fake data for screenshots or a portfolio
walkthrough.

```powershell
cd frontend
$env:VITE_MIRROR_MODE="true"
$env:VITE_MIRRAGE_DEMO_MODE="true"
npm run dev
```

Expected result:

- the mirror home uses demo weather and a demo daily nudge
- Calendar, Media, Context, and Smart Home views show labelled demo data
- no real Spotify, Google Calendar, Home Assistant, or backend account is needed
- turning `VITE_MIRRAGE_DEMO_MODE` off returns the app to real API behavior

## Physical mirror readiness checks

Before building or mounting the mirror:

- test the chosen display with Mirrage Mirror Mode
- test mirror material over the actual display
- confirm day/night readability
- run a 1 hour and 4 hour heat test
- confirm mini PC, microphone, speakers, and cables have service access
- confirm wall mounting hardware is suitable for the total weight and wall type
- confirm Docker production Compose starts after reboot

Use [hardware/testing-checklist.md](../hardware/testing-checklist.md) before
final installation.

## Wake word and presence checks

Check the local wake engine boundary:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/wake-word/status
```

Expected default result:

- `enabled` is `false`
- `status` is `disabled`
- `provider` is `openwakeword`
- `model_configured` is `false`

Start and stop are safe even when disabled:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/wake-word/start" -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/wake-word/stop" -Method Post
```

Check the current lifecycle snapshot:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/presence/status
```

Expected result:

- `state` is present
- `wake_phrase` is `Hey Mirrage` unless changed in `.env`
- `wake_word_engine` is `adapter` by default

Simulate a local wake engine detection:

```powershell
$body = @{ phrase = "Hey Mirrage"; engine = "manual-test"; confidence = 0.9 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/wake-word/detect" -Method Post -ContentType "application/json" -Body $body
```

Expected result:

- backend returns `state: wake_detected`
- the frontend receives the presence event
- Conversation Mode opens and starts browser speech recognition if the browser
  supports it

The manual wake call does not prove a real local wake model is installed. It
only proves the wake service, presence manager, SSE stream, and frontend handoff
work.

Run the local wake engine only after installing a real OpenWakeWord model and
microphone on the target device. See [wake-engine](wake-engine.md) and
[OpenWakeWord notes](openwakeword.md).

Tune the timeouts in `frontend/.env`:

```text
VITE_MIRROR_DIM_TIMEOUT_SECONDS=60
VITE_MIRROR_SLEEP_TIMEOUT_SECONDS=120
VITE_MIRROR_STARTUP_SECONDS=3
VITE_MIRROR_BURN_IN_SHIFT_SECONDS=45
```

Docker can run the same mode:

```powershell
$env:VITE_MIRROR_MODE="true"
docker compose up --build
```

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
speech recognition and browser speech synthesis. The local wake engine can open
Conversation Mode, but the spoken request still uses the browser STT path.

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
| `daily briefing` | Context focus view opens and replies with a proactive local briefing |
| `What should I focus on today?` | Context focus view opens and replies with a proactive focus nudge |
| `What is my day like?` | Context focus view opens and replies with provider-independent daily context |
| `show my smart home devices` | Smart Home focus view opens |
| `show sensors` | Smart Home focus view opens |
| `Open assistant` | Assistant focus view opens |

The assistant also adds a short action response to the message thread. Commands
that are not recognized still go to the backend assistant endpoint.

## Smart home checks

Smart home is disabled by default, so it should be safe to test without Home
Assistant installed.

Check status:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/smart-home/status
```

Expected result when disabled:

- `enabled` is `false`
- `connection_status` is `disabled`
- no token or secret values appear

Check discovery fallback:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/smart-home/entities
Invoke-RestMethod http://127.0.0.1:8000/api/smart-home/sensors
```

Expected result when disabled or unconfigured:

- response is JSON, not a crash page
- `items` is an empty list
- `message` explains what is missing

If Home Assistant is available:

1. Create a long-lived access token in Home Assistant.
2. Add the smart-home variables to `.env`.
3. Restart the backend.
4. Open the Smart Home focus view.
5. Press `Refresh`.

Expected result after configuration:

- supported lights, switches, scenes, and sensors appear
- sensors have no write buttons
- light and switch controls call the backend endpoints
- scenes can be activated
- unsupported domains such as locks and cameras do not appear

Details are in [smart-home](smart-home.md) and
[Home Assistant setup](home-assistant.md).

## Daily context checks

Open the Context focus view from the mirror home, or ask from the Assistant focus
view:

```text
daily briefing
```

Expected result:

- Context focus view opens
- the assistant reply uses `provider: proactive` for `daily briefing`, or
  `provider: context` for `What is my day like?`
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
$body = @{ message = "What is my day like?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected result:

- `provider` is `context`
- `context_action` is `daily`
- the reply includes `Daily briefing`

## Proactive assistant checks

Check the raw proactive endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/proactive/summary
```

Expected result:

- `status` is `ready`, `partial`, or `unavailable`
- `priority` is `high`, `medium`, `low`, or `none`
- `headline`, `message`, `suggestions`, `sources`, and `should_interrupt` are present
- unavailable context returns a clear fallback instead of an error page

Assistant proactive check:

```powershell
$body = @{ message = "Good morning" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/assistant/message" -Method Post -ContentType "application/json" -Body $body
```

Expected result:

- `provider` is `proactive`
- `context_action` is `proactive`
- the reply contains a short headline-style briefing

Mirror Mode check:

- start the frontend with `VITE_MIRROR_MODE=true`
- confirm the home screen shows the lower-right proactive nudge
- open Context and confirm the proactive briefing appears in the Daily Briefing view

## AI runtime checks

Check the runtime status:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/ai/runtime/status
```

Expected result:

- `configured_provider` is present
- `available_providers` includes `stub`, `ollama`, and `openai`
- no API keys or secrets are returned

Check provider capability state:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/ai/providers
```

Expected result:

- each provider has `name`, `kind`, `configured`, `supports_streaming`, and
  `default_model`
- `openai` shows configured only when an API key or base URL is set

Check the streaming-shaped endpoint:

```powershell
$body = @{ message = "hello" } | ConvertTo-Json
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/assistant/stream" -Method Post -ContentType "application/json" -Body $body
```

Expected response text includes:

```text
event: status
event: chunk
event: done
```

This is not true token streaming yet. It is a stable Server-Sent Events shape
that currently sends one assistant response chunk.

To test local-first routing with Ollama:

```text
MIRRAGE_AI_PROVIDER=ollama
MIRRAGE_AI_MODEL=llama3.2
MIRRAGE_AI_LOCAL_FIRST=true
MIRRAGE_AI_FALLBACK_PROVIDER=stub
```

Restart the backend after changing `.env`. If Ollama is not running, the
assistant should fall back instead of crashing.

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
- upcoming events appear in the schedule timeline
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
| `MIRRAGE_AI_LOCAL_FIRST` | `false` | Prefer local providers for runtime requests |
| `MIRRAGE_AI_LOCAL_ONLY` | `false` | Prevent cloud provider selection |
| `MIRRAGE_AI_FALLBACK_PROVIDER` | `stub` | Provider used when the selected provider fails |
| `MIRRAGE_AI_STREAMING_ENABLED` | `true` | Enables the current SSE response shape |
| `MIRRAGE_ALLOWED_ORIGINS` | localhost:5173 | CORS origins the backend accepts |
| `MIRRAGE_MEMORY_DATABASE_PATH` | `data/mirrage-memory.sqlite3` | Local SQLite memory path |
| `MIRRAGE_WAKE_ENGINE_ENABLED` | `false` | Enables local OpenWakeWord runtime support |
| `MIRRAGE_WAKE_ENGINE_MODEL_PATH` | blank | Path to a local wake model file |
| `VITE_MIRROR_MODE` | `false` | Enables the wall-display Mirror Mode frontend |
| `VITE_MIRRAGE_DEMO_MODE` | `false` | Enables explicit fake frontend demo data |

The frontend reads its backend URL from `VITE_API_BASE_URL`
(see [frontend/.env.example](../frontend/.env.example)); it defaults to
`http://127.0.0.1:8000`.

## Quick health check from the terminal

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/system/status
```
