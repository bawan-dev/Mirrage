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

## Assistant always replies "no model is connected yet"

This is expected. The active provider is `stub` until a real provider is wired in
(see the roadmap). The reply is proof the assistant route works end to end through
the AI service layer.
