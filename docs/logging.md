# Logging

Mirrage backend logs are structured JSON by default.

## Configuration

```text
MIRRAGE_LOG_LEVEL=INFO
MIRRAGE_LOG_JSON=true
MIRRAGE_LOG_FILE=logs/backend.log
```

Supported levels:

- `DEBUG`
- `INFO`
- `WARNING`
- `ERROR`
- `CRITICAL`

## What Gets Logged

Operational events:

- backend startup validation
- AI runtime provider selection and fallback
- provider request failures
- wake-word detection events
- presence state changes
- weather, Calendar, and Spotify integration failures

## What Should Not Be Logged

Never log:

- API keys
- OAuth tokens
- raw memory values
- user transcripts
- assistant replies
- `.env` contents

The current JSON formatter only includes a small allowlist of operational fields
such as provider, model, state, event, and subsystem.

## Viewing Logs

Docker:

```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

File:

```bash
tail -f logs/backend.log
```

systemd:

```bash
journalctl -u mirrage-docker -f
```
