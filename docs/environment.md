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
| `VITE_MIRRAGE_DEMO_MODE` | Enables explicit fake frontend demo data for screenshots and walkthroughs |
| `VITE_MIRROR_MODE` | Enables wall-display mode |
| `VITE_MIRROR_DIM_TIMEOUT_SECONDS` | Dimming delay |
| `VITE_MIRROR_SLEEP_TIMEOUT_SECONDS` | Sleep/return-home delay |

Keep `VITE_MIRRAGE_DEMO_MODE=false` for normal development and production-style
testing. Turn it on only when you want stable portfolio demo data without
connecting real accounts.

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
| `MIRRAGE_APP_VERSION` | API version, currently `2.0.0-dev` on `main` |
| `MIRRAGE_IDENTITY_ENABLED` | Enables the local identity store and authentication boundary |
| `MIRRAGE_IDENTITY_MODE` | `development`, `enforced`, or `disabled` |
| `MIRRAGE_IDENTITY_DATABASE_PATH` | Local identity, device, approval, and audit SQLite path |
| `MIRRAGE_IDENTITY_DEVICE_TOKEN_BYTES` | Random token bytes; minimum 32 |
| `MIRRAGE_IDENTITY_SESSION_TTL_SECONDS` | Reserved session lifetime boundary; defaults to 86400 |
| `MIRRAGE_APPROVAL_TTL_SECONDS` | Pending approval lifetime; defaults to 120 |
| `MIRRAGE_AUDIT_RETENTION_DAYS` | Audit retention target; automatic cleanup is not enabled |
| `MIRRAGE_IDENTITY_DEV_BYPASS` | Explicit local principal; forbidden in production |

Production requires:

```text
MIRRAGE_IDENTITY_ENABLED=true
MIRRAGE_IDENTITY_MODE=enforced
MIRRAGE_IDENTITY_DEV_BYPASS=false
```

Do not place a trusted-device token in a `VITE_` variable. The normal-mode
Identity view accepts a token for the current browser session and keeps it in
memory only.

## Bounded Agents

| Variable | Default | Purpose |
| --- | --- | --- |
| `MIRRAGE_AGENTS_ENABLED` | `false` | Enables planning and execution routes |
| `MIRRAGE_AGENT_MAX_STEPS` | `10` | Hard maximum steps accepted in a run |
| `MIRRAGE_AGENT_MAX_RUNTIME_SECONDS` | `300` | Total execution time limit |
| `MIRRAGE_AGENT_MAX_RETRIES` | `2` | Global retry ceiling; tools may choose less |
| `MIRRAGE_AGENT_MAX_CONCURRENT_RUNS` | `2` | Active run limit per user and installation |
| `MIRRAGE_AGENT_APPROVAL_TTL_SECONDS` | `300` | Agent side-effect approval lifetime |

Keep agents disabled until trusted devices, permissions, and a separate
approver are configured. Enabling agents does not enable arbitrary shell,
filesystem, web, or Home Assistant access; the registered tool list remains the
capability boundary.

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

## Wake Engine

| Variable | Purpose |
| --- | --- |
| `MIRRAGE_WAKE_ENGINE_ENABLED` | Starts the backend local wake engine when `true` |
| `MIRRAGE_WAKE_ENGINE_PROVIDER` | `openwakeword` for the current provider boundary |
| `MIRRAGE_WAKE_ENGINE_MODEL_PATH` | Local wake model path, for example `models/wake/hey-mirrage.onnx` |
| `MIRRAGE_WAKE_ENGINE_PHRASE` | Phrase the engine reports, default `Hey Mirrage` |
| `MIRRAGE_WAKE_ENGINE_SENSITIVITY` | Normalized threshold from `0.0` to `1.0` |
| `MIRRAGE_WAKE_ENGINE_MICROPHONE` | Optional microphone device name or index |
| `MIRRAGE_WAKE_ENGINE_SAMPLE_RATE` | Audio sample rate, default `16000` |
| `MIRRAGE_WAKE_ENGINE_FRAME_MS` | Audio frame length in milliseconds |
| `MIRRAGE_WAKE_ENGINE_COOLDOWN_SECONDS` | Duplicate wake suppression window |

The local wake engine is disabled by default. Leave it disabled until a real
model file and microphone are ready on the target device.

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
- wake engine provider, sensitivity, sample rate, frame size, cooldown, and
  model path when enabled
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
