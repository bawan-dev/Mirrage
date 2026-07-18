# Backups

Mirrage stores private local memory and identity data in separate SQLite files.
Backups should stay local unless a future cloud backup feature is explicitly
designed and documented.

## What To Back Up

Recommended:

- `data/mirrage-memory.sqlite3`
- `data/mirrage-identity.sqlite3`
- `.env`
- `backups/`
- important local notes about hardware setup

Optional:
- `logs/`

Do not commit backups or `.env` to Git.

## Identity Backup And Restore

```powershell
python -m backend.app.identity_cli backup
python -m backend.app.identity_cli restore --path "backups/<IDENTITY_BACKUP>.sqlite3"
```

Identity backups use SQLite's backup API and names beginning with
`mirrage-identity-`. Restore validates the schema before overwriting the local
identity database, then appends a restore audit event. The command is explicit;
Mirrage never restores or overwrites identity state automatically.

The existing memory backup functions and filenames remain unchanged.

## Manual Backup

From the repo root:

```bash
python -c "from backend.app.services.backups import create_memory_backup; print(create_memory_backup())"
```

Expected result:

- a file is created in `backups/`
- filename starts with `mirrage-memory-`

Docker:

```bash
docker compose -f docker-compose.prod.yml exec backend python -c "from backend.app.services.backups import create_memory_backup; print(create_memory_backup())"
```

## Restore

Stop Mirrage first:

```bash
docker compose -f docker-compose.prod.yml down
```

Restore from a trusted backup:

```bash
python -c "from backend.app.services.backups import restore_memory_backup; print(restore_memory_backup('backups/mirrage-memory-YYYYMMDD-HHMMSS.sqlite3'))"
```

Start Mirrage:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Verify:

```bash
export MIRRAGE_OWNER_TOKEN="<OWNER_DEVICE_TOKEN>"
curl -H "Authorization: Bearer $MIRRAGE_OWNER_TOKEN" http://127.0.0.1:8000/api/health/full
```

## Automatic Local Backup

Use cron or a systemd timer. Example cron entry:

```text
0 3 * * * cd /opt/mirrage && docker compose -f docker-compose.prod.yml exec -T backend python -c "from backend.app.services.backups import create_memory_backup; create_memory_backup()"
```

Keep automatic backups local. If you later copy them elsewhere, treat them as
private user data.

## Future Cloud Backup

Cloud backup is not implemented. Before adding it, Mirrage should have:

- explicit user opt-in
- encryption
- restore testing
- clear retention settings
- documentation of what leaves the device
