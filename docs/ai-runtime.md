# AI Runtime

Mirrage now has a backend-owned AI runtime instead of one direct provider call.
The goal is to make model support stronger without letting provider details leak
into the mirror UI.

## What It Does

The runtime handles four jobs:

- build a small request context from weather, calendar, memory, and proactive state
- choose a provider based on task type and privacy level
- fall back safely when the selected provider is unavailable
- expose a streaming-shaped assistant endpoint for the frontend and future local models

The current provider options are:

| Provider | Type | Notes |
| --- | --- | --- |
| `stub` | local | Default. No network and used in tests. |
| `ollama` | local | Private local model route. Requires Ollama running separately. |
| `openai` | cloud | OpenAI-compatible hosted route. Requires an API key. |

## Request Flow

```text
assistant message
  -> deterministic handlers first
  -> AI runtime
  -> context builder
  -> provider router
  -> selected provider
  -> fallback provider if needed
  -> assistant response
```

Deterministic handlers still run before the model layer:

- memory commands
- daily context questions
- proactive briefing prompts
- presence and voice lifecycle updates

That means a direct memory or daily briefing request does not need a model.

## Privacy Boundary

The context builder creates two prompts:

- local prompt: can include selected local memory details
- cloud prompt: withholds raw memory details and only includes reduced context

Private task types, such as memory, planning, and future agent work, prefer local
providers. `MIRRAGE_AI_LOCAL_ONLY=true` prevents cloud provider selection.

This is still a first runtime layer. It does not add automatic long-term memory
extraction, autonomous planning, or cloud-enhanced personal briefings.

## Configuration

```text
MIRRAGE_AI_PROVIDER=stub
MIRRAGE_AI_MODEL=
MIRRAGE_AI_RUNTIME_MODE=standard
MIRRAGE_AI_LOCAL_FIRST=false
MIRRAGE_AI_LOCAL_ONLY=false
MIRRAGE_AI_FALLBACK_PROVIDER=stub
MIRRAGE_AI_STREAMING_ENABLED=true
MIRRAGE_AI_PRIVACY_MODE=limited_cloud_context
MIRRAGE_AI_DEFAULT_TASK_MODEL=
MIRRAGE_AI_SUMMARY_MODEL=
MIRRAGE_AI_PLANNING_MODEL=
```

Use local-only mode when testing private memory behavior:

```text
MIRRAGE_AI_PROVIDER=ollama
MIRRAGE_AI_LOCAL_ONLY=true
MIRRAGE_AI_FALLBACK_PROVIDER=stub
```

## Runtime Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/ai/runtime/status` | Safe runtime config and provider names |
| `GET` | `/api/ai/providers` | Provider capability list without secrets |
| `POST` | `/api/assistant/stream` | Server-Sent Events response shape |

`POST /api/assistant/message` continues to be the main stable assistant route.

## What Is Planned

- true token streaming from providers that support it
- richer local model profiles for small vs large tasks
- explicit opt-in AI-enhanced context summaries
- encrypted provider credential storage
- future agent tools behind approval and privacy controls
