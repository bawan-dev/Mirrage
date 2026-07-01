# Updates

Use a predictable process so a home installation can recover if an update fails.

## Before Updating

Create a backup:

```bash
docker compose -f docker-compose.prod.yml exec backend python -c "from backend.app.services.backups import create_memory_backup; print(create_memory_backup())"
```

Record the current commit:

```bash
git rev-parse --short HEAD
```

Check current health:

```bash
curl http://127.0.0.1:8000/api/health/full
```

## Update

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Verify:

```bash
docker compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/health/full
```

Open the mirror UI and confirm it loads.

## Rollback

If the update fails:

```bash
git log --oneline -5
git checkout <previous-commit>
docker compose -f docker-compose.prod.yml up -d --build
```

If local memory was damaged, restore from backup using [backups.md](backups.md).

## Versioned Releases

For a stable home install, prefer tags:

```bash
git checkout v0.1.0
MIRRAGE_VERSION=v0.1.0 docker compose -f docker-compose.prod.yml up -d --build
```

Do not update a wall-mounted installation right before you need it to work.
