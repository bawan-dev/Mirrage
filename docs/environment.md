# Environment

Mirrage uses `.env` for local and production configuration. Start from
[../.env.example](../.env.example).

## Backend

| Variable | Purpose |
| --- | --- |
| `MIRRAGE_APP_ENV` | `development`, `test`, or `production` |
| `MIRRAGE_API_PORT` | Backend port |
| `MIRRAGE_FRONTEND_URL` | URL used for OAuth redirects |
| `MIRRAGE_ALLOWED_ORIGINS` | CORS origins accepted by FastAPI |

## Frontend

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Backend URL baked into the frontend build |
| `VITE_MIRROR_MODE` | Enables wall-display mode |
| `VITE_MIRROR_DIM_TIMEOUT_SECONDS` | Dimming delay |
| `VITE_MIRROR_SLEEP_TIMEOUT_SECONDS` | Sleep/return-home delay |

## Logging

| Variable | Purpose |
| --- | --- |
| `MIRRAGE_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |
| `MIRRAGE_LOG_JSON` | JSON logs when true |
| `MIRRAGE_LOG_FILE` | Optional backend log file |

## Memory And Backups

| Variable | Purpose |
| --- | --- |
| `MIRRAGE_MEMORY_DATABASE_PATH` | Local SQLite memory path |
| `MIRRAGE_BACKUP_DIRECTORY` | Local backup directory |

## Smart Home

| Variable | Purpose |
| --- | --- |
| `MIRRAGE_SMART_HOME_ENABLED` | Enables Mirrage smart home routes and UI state |
| `MIRRAGE_SMART_HOME_TIMEOUT_SECONDS` | Timeout for smart home provider requests |
| `MIRRAGE_HOME_ASSISTANT_ENABLED` | Enables the Home Assistant provider |
| `MIRRAGE_HOME_ASSISTANT_BASE_URL` | Local Home Assistant URL, for example `http://homeassistant.local:8123` |
| `MIRRAGE_HOME_ASSISTANT_TOKEN` | Home Assistant long-lived access token |

Smart home is off by default. Keep the Home Assistant token in `.env` only; do
not commit it.

## AI Runtime

| Variable | Purpose |
| --- | --- |
| `MIRRAGE_AI_PROVIDER` | `stub`, `ollama`, or `openai` |
| `MIRRAGE_AI_MODEL` | Default model |
| `MIRRAGE_AI_BASE_URL` | Optional compatible provider base URL |
| `MIRRAGE_AI_API_KEY` | Hosted provider API key |
| `MIRRAGE_AI_LOCAL_FIRST` | Prefer local providers |
| `MIRRAGE_AI_LOCAL_ONLY` | Prevent cloud provider selection |
| `MIRRAGE_AI_FALLBACK_PROVIDER` | Provider used after selected provider fails |

## Startup Validation

The backend validates key settings during startup:

- log level
- weather coordinates
- memory database path
- backup directory
- smart home timeout
- Home Assistant provider/token readiness
- wake-word sensitivity
- presence timeout
- AI provider names
- production CORS wildcard usage

Hard errors stop startup. Warnings are logged but do not stop the backend.

## Secrets

Keep these out of Git:

- `.env`
- Spotify client secret
- Google Calendar client secret
- AI provider API keys
- Home Assistant long-lived access token
- OAuth tokens
- backups
- logs
