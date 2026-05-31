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

## Assistant replies with a stub or fallback message

This is expected when `MIRRAGE_AI_PROVIDER=stub`, or when a configured model
provider is unavailable. The reply is proof the assistant route is still working
through the backend and AI service layer.

Use `MIRRAGE_AI_PROVIDER=ollama` for a local Ollama model or
`MIRRAGE_AI_PROVIDER=openai` for an OpenAI-compatible API provider.

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
