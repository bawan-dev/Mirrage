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
