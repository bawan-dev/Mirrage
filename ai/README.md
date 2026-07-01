# Mirrage AI Layer

Provider and runtime layer for local and remote assistant models. The backend
routes assistant messages through the runtime, which builds a small context,
chooses a provider, and falls back safely when a provider is unavailable.

## Providers

| Provider | When to use | Config |
| --- | --- | --- |
| `stub` | Default. No network, used for development and CI. | none |
| `ollama` | Local, private, offline. | `MIRRAGE_AI_MODEL`, optional `MIRRAGE_AI_BASE_URL` |
| `openai` | Hosted, OpenAI-compatible. | `MIRRAGE_AI_MODEL`, `MIRRAGE_AI_API_KEY`, optional `MIRRAGE_AI_BASE_URL` |

The `openai` provider is OpenAI-compatible, so it can also work against other
gateways that expose an OpenAI-style chat completions API.

## Runtime

The runtime owns:

- task classification
- privacy-aware context building
- provider and model selection
- provider fallback
- the current Server-Sent Events response shape

Context building creates separate local and cloud prompts. Local prompts can use
selected memory details. Cloud prompts withhold raw memory values and only pass
reduced context.

## Selecting a provider

Set `MIRRAGE_AI_PROVIDER` in `.env` (see [.env.example](../.env.example)). No
frontend or route changes are needed.

Useful runtime flags:

| Variable | Purpose |
| --- | --- |
| `MIRRAGE_AI_LOCAL_FIRST` | Prefer local providers when possible. |
| `MIRRAGE_AI_LOCAL_ONLY` | Prevent cloud provider selection. |
| `MIRRAGE_AI_FALLBACK_PROVIDER` | Provider used when the selected provider fails. |
| `MIRRAGE_AI_STREAMING_ENABLED` | Enables the current Server-Sent Events response shape. |
| `MIRRAGE_AI_DEFAULT_TASK_MODEL` | Optional model override for normal conversation. |
| `MIRRAGE_AI_SUMMARY_MODEL` | Optional model override for summary/context tasks. |
| `MIRRAGE_AI_PLANNING_MODEL` | Optional model override for planning tasks. |

## Adding a provider

1. Implement `AssistantProvider` in `ai/providers/` and return an `AssistantResult`.
2. Raise `AIProviderError` on failure so the backend can degrade gracefully.
3. Register the class in `PROVIDER_DEFINITIONS` in [router.py](router.py).

More detail: [docs/ai-runtime.md](../docs/ai-runtime.md).
