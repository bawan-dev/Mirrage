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

The frontend reads its backend URL from `VITE_API_BASE_URL`
(see [frontend/.env.example](../frontend/.env.example)); it defaults to
`http://127.0.0.1:8000`.

## Quick health check from the terminal

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/system/status
```
