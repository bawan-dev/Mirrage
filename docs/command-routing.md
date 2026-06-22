# Command Routing

Command routing is the first step toward Mirrage acting on simple requests
instead of only returning text.

## Current Scope

The current router is small and local to the frontend. It recognizes a few
screen-navigation intents and turns them into UI actions.

Supported examples:

| User says or types | Result |
| --- | --- |
| `What is the weather?` | Opens the Weather focus view |
| `Show my music` | Opens the Media focus view |
| `What is on my calendar today?` | Opens the Calendar focus view and summarizes today's events |
| `daily briefing` | Opens the Context focus view and asks the backend context service for a briefing |
| `What should I focus on today?` | Opens the Context focus view and asks for suggested focus |
| `Open assistant` | Opens the Assistant focus view |

If a message is not recognized as a UI command, it still goes to the existing
assistant endpoint.

## Flow

```text
Assistant input
  -> intent routing layer
  -> known command?
      -> UI action system
      -> focus view changes
      -> assistant action response is shown/spoken
  -> unknown command?
      -> POST /api/assistant/message
      -> assistant provider response
```

## Frontend Boundary

The routing layer lives in `frontend/src/intentRouting.ts`.

Its job is only to classify simple command phrases and return an action object.
It does not change React state directly.

The app receives the action and decides what to do with it. Right now the only
action is:

```text
open_focus_view
```

Supported targets:

- `weather`
- `media`
- `assistant`
- `calendar`
- `context`

Most commands return a short local response. Calendar and context have extra
backend paths:

`What is on my calendar today?` opens the Calendar focus view and fetches today's
events from the backend Calendar endpoint before answering.

`daily briefing` and similar context commands open the Context focus view, fetch
`GET /api/context/daily`, and send the original prompt to
`POST /api/assistant/message`. The backend handles that prompt with deterministic
context logic before model provider routing.

## Why It Is Local For Now

Keeping this local makes the first version reliable and easy to test. Screen
navigation commands should not need a model call or internet access.

Later, the same shape can move behind the backend if Mirrage needs:

- richer intent detection
- smart home actions
- broader calendar actions
- broader context actions
- command permissions
- confirmations for risky actions

## Not Built Yet

The current router does not handle:

- multi-step commands
- smart home actions
- account actions
- hardware actions
- confirmations
- model-based intent classification
