# Operations

## Identity Operations

Check the safe identity summary with an owner device token:

```powershell
$headers = @{ Authorization = "Bearer <OWNER_DEVICE_TOKEN>" }
Invoke-RestMethod http://127.0.0.1:8000/api/identity/me -Headers $headers
Invoke-RestMethod http://127.0.0.1:8000/api/identity/status
Invoke-RestMethod http://127.0.0.1:8000/api/audit/events -Headers $headers
```

Review active users and devices after household changes. Revoke unused devices
instead of deleting audit history. Keep at least one tested owner device and a
recent identity backup.

The normal-mode frontend Identity view accepts a token for the current browser
session only. Mirror Mode intentionally does not expose household administration.

These are the normal maintenance tasks for a Mirrage installation.

## Daily Checks

```bash
curl http://127.0.0.1:8000/api/health
docker compose -f docker-compose.prod.yml ps
```

Expected:

- backend health returns `online`
- frontend and backend containers are running
- optional integrations may be degraded if they are not configured

For installed hardware, also check:

- mirror is not unusually warm
- ventilation is clear
- power and network cables are not strained
- frontend is still in kiosk/Mirror Mode

## Full Health Check

```bash
export MIRRAGE_OWNER_TOKEN="<OWNER_DEVICE_TOKEN>"
curl -H "Authorization: Bearer $MIRRAGE_OWNER_TOKEN" http://127.0.0.1:8000/api/health/full
```

Use this when diagnosing issues. It reports:

- backend
- environment validation
- memory database
- AI runtime
- provider configuration
- presence engine
- wake engine
- weather
- Calendar
- Spotify

The full endpoint does not expose API keys, OAuth tokens, or memory contents.

## Check Wake Engine

```bash
curl http://127.0.0.1:8000/api/wake-word/status
```

Expected default:

- `enabled` is `false`
- `status` is `disabled`
- `provider` is `openwakeword`

If the engine is enabled, check:

- `configured`
- `running`
- `model_configured`
- `microphone_configured`
- `error_message`

Disabled wake engine is not a backend failure. Enabled but unconfigured means
hands-free wake word is not ready on that machine.

## View Logs

Docker logs:

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
```

File logs:

```bash
tail -f logs/backend.log
```

systemd logs:

```bash
journalctl -u mirrage-docker -f
```

## Restart Services

```bash
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml restart frontend
```

Restart the whole stack:

```bash
docker compose -f docker-compose.prod.yml restart
```

## Recover After Power Loss

Expected behavior:

- systemd starts `mirrage-docker`
- Docker starts backend and frontend
- backend validates environment and creates runtime directories
- frontend waits for backend health before starting
- containers restart automatically if they crash

If the mirror does not return:

```bash
systemctl status mirrage-docker
docker compose -f /opt/mirrage/docker-compose.prod.yml ps
curl -H "Authorization: Bearer $MIRRAGE_OWNER_TOKEN" http://127.0.0.1:8000/api/health/full
```

## Check Integrations

Weather:

```bash
curl http://127.0.0.1:8000/api/info/weather
```

Calendar:

```bash
curl http://127.0.0.1:8000/api/integrations/calendar/status
```

Spotify:

```bash
curl http://127.0.0.1:8000/api/integrations/spotify/status
```

AI runtime:

```bash
curl http://127.0.0.1:8000/api/ai/runtime/status
curl http://127.0.0.1:8000/api/ai/providers
```

Wake engine:

```bash
curl http://127.0.0.1:8000/api/wake-word/status
```

## Maintenance Schedule

Weekly:

- check health
- check disk space
- create a local backup
- check the frame vents for dust or blockage
- confirm the mirror can still be safely unplugged or serviced

Before updates:

- create a backup
- note the current Git commit
- rebuild and restart
- verify health

Monthly:

- update the host OS
- restart the machine during a planned maintenance window
- confirm Mirrage starts after reboot
- inspect cable strain relief and wall mounting hardware
- clean the mirror surface with material-safe cleaner

## Hardware Service Notes

The physical mirror should keep these parts accessible:

- mini PC power button and USB ports
- display power and video cables
- microphone cable
- speaker cable
- Ethernet cable
- main power plug or power strip

Do not build Mirrage as a sealed box. If the display, microphone, speaker, or
mini PC fails, it should be replaceable without destroying the frame.
