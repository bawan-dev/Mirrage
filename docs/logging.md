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
- wake engine startup, shutdown, microphone errors, cooldown suppression, and
  latency measurements
- presence state changes
- weather, Calendar, and Spotify integration failures
- safe identity startup status and authentication outcomes
- authorization decisions and approval lifecycle events
- identity database and audit-write failures

Operational logs and the durable identity audit log serve different purposes.
Operational logs help diagnose the service. Audit events provide a redacted,
append-only history of security decisions and administrative changes.

## What Should Not Be Logged

Never log:

- API keys
- OAuth tokens
- raw memory values
- user transcripts
- assistant replies
- raw microphone audio
- `.env` contents
- trusted-device token hashes or prefixes
- private Calendar event details

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
