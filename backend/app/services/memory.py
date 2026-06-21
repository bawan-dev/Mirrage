"""Local memory storage and assistant memory commands."""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.schemas import (
    AssistantMessageResponse,
    MemoryCreateRequest,
    MemoryKind,
    MemoryRecordResponse,
    MemorySearchResponse,
    MemoryStatus,
    MemorySummaryResponse,
    MemoryUpdateRequest,
)
from backend.app.settings import settings

MEMORY_KINDS: tuple[MemoryKind, ...] = ("preference", "fact", "goal", "routine")
MEMORY_STATUSES: tuple[MemoryStatus, ...] = ("active", "archived", "done")


class MemoryNotFoundError(Exception):
    """Raised when a memory record cannot be found."""


def initialize_memory_store() -> None:
    """Create the local memory database if it does not exist yet."""

    database_path = _database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN (
                    'preference', 'fact', 'goal', 'routine'
                )),
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN (
                    'active', 'archived', 'done'
                )),
                source TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(kind, key)
            )
            """
        )


def list_memories(
    kind: MemoryKind | None = None,
    query: str | None = None,
    status: MemoryStatus | None = "active",
) -> MemorySearchResponse:
    initialize_memory_store()

    filters: list[str] = []
    values: list[str] = []

    if kind is not None:
        filters.append("kind = ?")
        values.append(kind)

    if status is not None:
        filters.append("status = ?")
        values.append(status)

    if query:
        filters.append("(key LIKE ? OR value LIKE ?)")
        like_query = f"%{query}%"
        values.extend([like_query, like_query])

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    with _connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, kind, key, value, status, source, created_at, updated_at
            FROM memories
            {where_clause}
            ORDER BY updated_at DESC, id DESC
            """,
            values,
        ).fetchall()

    items = [_row_to_memory(row) for row in rows]
    return MemorySearchResponse(items=items, count=len(items))


def summarize_memories() -> MemorySummaryResponse:
    groups = {kind: list_memories(kind=kind).items for kind in MEMORY_KINDS}
    count = sum(len(items) for items in groups.values())
    message = (
        "No local memories are stored yet."
        if count == 0
        else f"{count} local memories are stored."
    )

    return MemorySummaryResponse(
        preferences=groups["preference"],
        facts=groups["fact"],
        goals=groups["goal"],
        routines=groups["routine"],
        count=count,
        message=message,
    )


def create_memory(memory: MemoryCreateRequest) -> MemoryRecordResponse:
    initialize_memory_store()

    now = _now()
    with _connect() as connection:
        row = connection.execute(
            """
            INSERT INTO memories (
                kind, key, value, status, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(kind, key) DO UPDATE SET
                value = excluded.value,
                status = excluded.status,
                source = excluded.source,
                updated_at = excluded.updated_at
            RETURNING id, kind, key, value, status, source, created_at, updated_at
            """,
            (
                memory.kind,
                _clean_text(memory.key),
                _clean_text(memory.value),
                memory.status,
                memory.source,
                now,
                now,
            ),
        ).fetchone()

    return _row_to_memory(row)


def update_memory(memory_id: int, update: MemoryUpdateRequest) -> MemoryRecordResponse:
    initialize_memory_store()

    fields: list[str] = []
    values: list[str] = []

    if update.key is not None:
        fields.append("key = ?")
        values.append(_clean_text(update.key))
    if update.value is not None:
        fields.append("value = ?")
        values.append(_clean_text(update.value))
    if update.status is not None:
        fields.append("status = ?")
        values.append(update.status)
    if update.source is not None:
        fields.append("source = ?")
        values.append(update.source)

    if fields:
        fields.append("updated_at = ?")
        values.append(_now())
        values.append(str(memory_id))

        with _connect() as connection:
            row = connection.execute(
                f"""
                UPDATE memories
                SET {", ".join(fields)}
                WHERE id = ?
                RETURNING id, kind, key, value, status, source, created_at, updated_at
                """,
                values,
            ).fetchone()
    else:
        row = _get_memory_row(memory_id)

    if row is None:
        raise MemoryNotFoundError(f"Memory {memory_id} was not found.")

    return _row_to_memory(row)


def handle_memory_message(message: str) -> AssistantMessageResponse | None:
    """Return a local memory response when the message is a memory command."""

    normalized = _normalize(message)

    if _is_memory_recall(normalized):
        return _build_recall_response(normalized)

    if normalized.startswith("remember "):
        return _build_store_response(message)

    if normalized.startswith("update "):
        return _build_update_response(message)

    return None


def _build_store_response(message: str) -> AssistantMessageResponse:
    parsed = _parse_memory_to_store(message)
    memory = create_memory(parsed)

    return AssistantMessageResponse(
        reply=f"Remembered {memory.kind}: {memory.key}.",
        provider="memory",
        model=None,
        memory_action="stored",
    )


def _build_recall_response(normalized: str) -> AssistantMessageResponse:
    kind = _requested_memory_kind(normalized)
    memories = list_memories(kind=kind).items if kind else summarize_memories()

    if isinstance(memories, MemorySummaryResponse):
        if memories.count == 0:
            reply = "I do not have any local memories yet."
        else:
            sections = [
                _format_memory_section("Preferences", memories.preferences),
                _format_memory_section("Facts", memories.facts),
                _format_memory_section("Goals", memories.goals),
                _format_memory_section("Routines", memories.routines),
            ]
            reply = "Here is what I remember locally: " + " ".join(
                section for section in sections if section
            )
    elif not memories:
        reply = f"I do not have any local {kind or 'memories'} yet."
    else:
        reply = _format_memory_section(f"{kind.title()}s", memories)

    return AssistantMessageResponse(
        reply=reply,
        provider="memory",
        model=None,
        memory_action="retrieved",
    )


def _build_update_response(message: str) -> AssistantMessageResponse | None:
    match = re.search(
        r"^update\s+(?:my\s+)?(?P<key>.+?)\s+to\s+(?P<value>.+)$",
        message.strip(),
        flags=re.IGNORECASE,
    )
    if match is None:
        return None

    key = _clean_text(match.group("key"))
    value = _clean_text(match.group("value"))
    existing = list_memories(query=key).items

    if not existing:
        return AssistantMessageResponse(
            reply=f"I could not find a local memory for {key}.",
            provider="memory",
            model=None,
            memory_action="not_found",
        )

    updated = update_memory(
        existing[0].id,
        MemoryUpdateRequest(value=value, source="assistant"),
    )

    return AssistantMessageResponse(
        reply=f"Updated {updated.kind}: {updated.key}.",
        provider="memory",
        model=None,
        memory_action="updated",
    )


def _parse_memory_to_store(message: str) -> MemoryCreateRequest:
    content = re.sub(r"^remember\s+(that\s+)?", "", message.strip(), flags=re.I)
    content = _clean_text(content)

    kind = _classify_memory(content)
    key = _derive_key(content, kind)
    value = _derive_value(content, key)

    return MemoryCreateRequest(
        kind=kind,
        key=key,
        value=value,
        source="assistant",
    )


def _classify_memory(content: str) -> MemoryKind:
    normalized = _normalize(content)

    if "goal" in normalized or normalized.startswith("i want to "):
        return "goal"
    if "routine" in normalized or "every morning" in normalized:
        return "routine"
    if "every night" in normalized or "every day" in normalized:
        return "routine"
    if "prefer" in normalized or "favorite" in normalized or "favourite" in normalized:
        return "preference"
    if "like" in normalized or "dislike" in normalized:
        return "preference"

    return "fact"


def _derive_key(content: str, kind: MemoryKind) -> str:
    patterns = (
        r"^my\s+(?P<key>.+?)\s+is\s+.+$",
        r"^i\s+prefer\s+(?P<key>.+?)(?:\s+to\s+.+)?$",
        r"^i\s+like\s+(?P<key>.+)$",
        r"^i\s+dislike\s+(?P<key>.+)$",
    )

    for pattern in patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        if match:
            return _clean_text(match.group("key")).lower()[:120]

    if kind == "goal":
        match = re.search(r"goal\s+(?:is\s+)?(?P<key>.+)", content, flags=re.I)
        if match:
            return f"goal: {_clean_text(match.group('key')).lower()[:80]}"
        return "goal"

    if kind == "routine":
        return _clean_text(content).lower()[:120]

    return _clean_text(content).lower()[:120]


def _derive_value(content: str, key: str) -> str:
    match = re.search(r"^my\s+.+?\s+is\s+(?P<value>.+)$", content, flags=re.I)
    if match:
        return _clean_text(match.group("value"))

    match = re.search(r"^i\s+prefer\s+.+?\s+to\s+(?P<value>.+)$", content, flags=re.I)
    if match:
        return _clean_text(match.group("value"))

    if content.lower().startswith(key.lower()):
        return _clean_text(content)

    return content


def _is_memory_recall(normalized: str) -> bool:
    recall_phrases = (
        "what do you remember",
        "what do you know about me",
        "show my memories",
        "list my memories",
        "my memories",
        "what are my preferences",
        "what are my facts",
        "what are my goals",
        "what are my routines",
    )
    return any(phrase in normalized for phrase in recall_phrases)


def _requested_memory_kind(normalized: str) -> MemoryKind | None:
    if "preference" in normalized or "preferences" in normalized:
        return "preference"
    if "fact" in normalized or "facts" in normalized:
        return "fact"
    if "goal" in normalized or "goals" in normalized:
        return "goal"
    if "routine" in normalized or "routines" in normalized:
        return "routine"
    return None


def _format_memory_section(
    title: str,
    memories: list[MemoryRecordResponse],
) -> str:
    if not memories:
        return ""

    entries = "; ".join(f"{memory.key}: {memory.value}" for memory in memories[:5])
    return f"{title}: {entries}."


def _get_memory_row(memory_id: int) -> sqlite3.Row | None:
    initialize_memory_store()

    with _connect() as connection:
        return connection.execute(
            """
            SELECT id, kind, key, value, status, source, created_at, updated_at
            FROM memories
            WHERE id = ?
            """,
            (memory_id,),
        ).fetchone()


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path())
    connection.row_factory = sqlite3.Row
    return connection


def _database_path() -> Path:
    return Path(settings.memory_database_path)


def _row_to_memory(row: sqlite3.Row | dict[str, Any]) -> MemoryRecordResponse:
    return MemoryRecordResponse(
        id=row["id"],
        kind=row["kind"],
        key=row["key"],
        value=row["value"],
        status=row["status"],
        source=row["source"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .")


def _normalize(value: str) -> str:
    return _clean_text(value).casefold()
