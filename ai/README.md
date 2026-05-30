# Mirrage AI Layer

Provider layer for local and remote assistant models. The backend talks only to
`AssistantAIService`; it never knows which model answered.

## Providers

| Provider | When to use | Config |
| --- | --- | --- |
| `stub` | Default. No network, used for development and CI. | none |
| `ollama` | Local, private, offline (e.g. on a Jetson Orin Nano). | `MIRRAGE_AI_MODEL`, optional `MIRRAGE_AI_BASE_URL` |
| `openai` | Hosted, high-quality, OpenAI-compatible. | `MIRRAGE_AI_MODEL`, `MIRRAGE_AI_API_KEY`, optional `MIRRAGE_AI_BASE_URL` |

The `openai` provider is OpenAI-compatible, so it also works against other gateways
and even a local Ollama server's `/v1` endpoint by setting `MIRRAGE_AI_BASE_URL`.

## Selecting a provider

Set `MIRRAGE_AI_PROVIDER` in `.env` (see [.env.example](../.env.example)). No
frontend or route changes are needed — only the provider behind the boundary
changes.

## Adding a provider

1. Implement `AssistantProvider` in `ai/providers/` and return an `AssistantResult`.
2. Raise `AIProviderError` on failure so the backend can degrade gracefully.
3. Register the class in `PROVIDERS` in [service.py](service.py).
