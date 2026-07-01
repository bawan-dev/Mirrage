"""Local backup utilities for private Mirrage data."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from backend.app.services.memory import initialize_memory_store
from backend.app.settings import settings


@dataclass(frozen=True)
class BackupResult:
    status: str
    source: str
    destination: str
    created_at: str
    size_bytes: int


def create_memory_backup(destination_dir: str | Path | None = None) -> BackupResult:
    """Create a SQLite-safe local backup of the memory database."""

    initialize_memory_store()
    source = Path(settings.memory_database_path)
    destination_root = Path(destination_dir or settings.backup_directory)
    destination_root.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(UTC)
    destination = destination_root / (
        f"mirrage-memory-{created_at.strftime('%Y%m%d-%H%M%S')}.sqlite3"
    )

    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as backup_connection:
            source_connection.backup(backup_connection)

    return BackupResult(
        status="created",
        source=str(source),
        destination=str(destination),
        created_at=created_at.isoformat(),
        size_bytes=destination.stat().st_size,
    )


def restore_memory_backup(backup_path: str | Path) -> BackupResult:
    """Restore the local memory database from a trusted local backup file."""

    source = Path(backup_path)
    if not source.exists():
        raise FileNotFoundError(f"Backup file does not exist: {source}")

    destination = Path(settings.memory_database_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(UTC)

    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)

    return BackupResult(
        status="restored",
        source=str(source),
        destination=str(destination),
        created_at=created_at.isoformat(),
        size_bytes=destination.stat().st_size,
    )


def list_memory_backups(directory: str | Path | None = None) -> list[Path]:
    """Return local memory backups newest first."""

    root = Path(directory or settings.backup_directory)
    if not root.exists():
        return []

    return sorted(root.glob("mirrage-memory-*.sqlite3"), reverse=True)
