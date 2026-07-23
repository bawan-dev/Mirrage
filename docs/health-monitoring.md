# Health Monitoring

Health endpoints are designed for Docker, systemd checks, and manual diagnosis.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `/health` | Legacy quick backend health |
| `/api/health` | Production quick backend health |
| `/api/health/full` | Full subsystem health |
| `/api/system/status` | Existing mirror status summary |

`/api/health/full` requires `health.full.read`. Supply an owner trusted-device
bearer token, or deliberately enable the development bypass for local-only
diagnosis.

## Identity Component

The full response includes safe identity details:

- enabled state and operating mode
- database status
- active user count
- whether an active owner exists
- active trusted-device count
- pending approval count
- audit-store status

It does not include names, token prefixes, token hashes, permissions, or private
records. Enforced mode without an owner is an error. Enforced mode without an
active trusted device is a warning. A corrupt or unavailable identity database
is an error.

## Quick Health

```bash
curl http://127.0.0.1:8000/api/health
```

Expected:

```json
{"service":"mirrage-api","status":"online"}
```

## Full Health

```bash
export MIRRAGE_OWNER_TOKEN="<OWNER_DEVICE_TOKEN>"
curl -H "Authorization: Bearer $MIRRAGE_OWNER_TOKEN" http://127.0.0.1:8000/api/health/full
```

The response includes checks for:

- backend
- environment
- identity
- relationships
- agents
- memory
- AI runtime
- providers
- presence
- wake engine
- weather
- Calendar
- Spotify
- smart home

Full health may be `degraded` when optional integrations are not configured. That
does not mean the backend is down.

The agent component reports enabled state, database status, active,
approval-waiting, and failed run counts, queue status, and the concurrency
limit. It never includes goals, step arguments, events, or final results.
Disabled agents are healthy because the feature is opt-in; an unavailable agent
database is an error.

The wake engine check reports whether the local engine is enabled, configured,
running, and whether a model and microphone setting are present. Disabled is
reported as healthy because push-to-talk and the detection adapter still work.
Enabled but missing model setup is degraded or unavailable and should be fixed
before claiming hands-free operation.

The smart home check reports whether Mirrage smart home support is enabled,
whether Home Assistant is configured, whether discovery can run, and how many
safe entities were found. It does not expose the Home Assistant token.

## Docker Health Checks

`docker-compose.prod.yml` uses:

- backend `/api/health`
- frontend `/health`

Optional integration degradation should not kill the containers. A Spotify issue
should not stop memory, a smart home issue should not stop Calendar, and a
weather failure should not stop voice.

## External Monitoring

A simple local monitor can check:

```bash
curl --fail http://127.0.0.1:8000/api/health
curl --fail http://127.0.0.1:5173/health
```

Use `/api/health/full` for diagnosis, not as a hard uptime check.
