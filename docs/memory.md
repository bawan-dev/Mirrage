# Memory Layer

Mirrage now has a small local memory layer. The goal is simple: remember useful
personal context without sending it to an outside service by default.

This is not long-term agent memory yet. It is the first storage boundary for
preferences, facts, goals, and routines.

## What It Stores

Memory records are grouped into four types:

| Type | Used for |
| --- | --- |
| `preference` | User choices such as units, favorite items, or preferred behavior |
| `fact` | Stable information the assistant should know later |
| `goal` | Things the user is working toward |
| `routine` | Repeated habits or schedule patterns |

Each memory has:

- `kind`
- `key`
- `value`
- `status`
- `source`
- created and updated timestamps

The current statuses are `active`, `archived`, and `done`.

## Storage

Mirrage uses SQLite through Python's standard library.

Default path:

```text
data/mirrage-memory.sqlite3
```

Configuration:

```powershell
MIRRAGE_MEMORY_DATABASE_PATH=data/mirrage-memory.sqlite3
```

The database file is ignored by Git. The `data/` folder is tracked with
`data/.gitkeep`, but the private SQLite file is not committed.

When running with Docker Compose, `./data` is mounted into the backend container
so memory survives container restarts.

## Privacy Boundary

Memory commands are handled before the assistant calls the AI provider.

```text
assistant message
  -> memory command check
  -> local SQLite memory action, if matched
  -> AI provider only if no local memory command matched
```

Examples that stay local:

```text
remember my favorite drink is coffee
what do you remember about me?
update my favorite drink to tea
```

Those commands are not sent to Ollama, OpenAI-compatible providers, or the stub
provider. Normal assistant messages still use the configured AI provider.

## API

### List Memories

```text
GET /api/memory
GET /api/memory?kind=preference
GET /api/memory?q=coffee
```

### Summary

```text
GET /api/memory/summary
```

### Create Or Upsert

```text
POST /api/memory
```

Example body:

```json
{
  "kind": "preference",
  "key": "temperature unit",
  "value": "celsius"
}
```

Creating the same `kind` and `key` again updates the existing record.

### Update

```text
PATCH /api/memory/{memory_id}
```

Example body:

```json
{
  "value": "fahrenheit",
  "status": "active"
}
```

## Assistant Commands

The first command parser is intentionally small.

| Message | Current behavior |
| --- | --- |
| `remember my favorite drink is coffee` | Stores a preference |
| `remember my goal is finish the mirror prototype` | Stores a goal |
| `remember that I live in London` | Stores a fact |
| `remember every morning I check my calendar` | Stores a routine |
| `what do you remember about me?` | Summarizes local memory |
| `what are my goals?` | Lists goals |
| `update my favorite drink to tea` | Updates the first matching memory |

The parser is not trying to understand every sentence yet. It is meant to prove
the storage boundary and give the assistant a useful local recall path.

## Resetting Local Memory

Stop the backend first, then delete the SQLite file:

```powershell
Remove-Item data/mirrage-memory.sqlite3
```

The backend will recreate it the next time memory is used.

## Current Limits

- No encryption yet.
- No multi-user accounts yet.
- No memory editing UI yet.
- No automatic memory extraction from normal chat.
- No confirmation step for sensitive memories yet.

Those are intentional limits. This phase creates the local storage foundation
before adding heavier agent behavior.
