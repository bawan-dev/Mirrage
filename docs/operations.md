# Operations

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

## Full Health Check

```bash
curl http://127.0.0.1:8000/api/health/full
```

Use this when diagnosing issues. It reports:

- backend
- environment validation
- memory database
- AI runtime
- provider configuration
- presence engine
- weather
- Calendar
- Spotify

The full endpoint does not expose API keys, OAuth tokens, or memory contents.

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
curl http://127.0.0.1:8000/api/health/full
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

## Maintenance Schedule

Weekly:

- check health
- check disk space
- create a local backup

Before updates:

- create a backup
- note the current Git commit
- rebuild and restart
- verify health

Monthly:

- update the host OS
- restart the machine during a planned maintenance window
- confirm Mirrage starts after reboot
