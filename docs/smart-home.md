# Smart Home

Mirrage has a backend-owned smart home foundation. The first provider is Home
Assistant.

The goal of this layer is controlled home interaction, not arbitrary automation.
The frontend calls Mirrage, Mirrage applies safety rules, and only then does the
backend talk to Home Assistant.

```text
Frontend Smart Home view
  -> FastAPI smart home routes
  -> SmartHomeService
  -> HomeAssistantClient
  -> Home Assistant local API
```

## Current Scope

Supported in this phase:

- discover entities from Home Assistant
- normalize entities into a Mirrage shape
- turn lights on and off
- turn switches on and off
- activate scenes
- read sensors
- show a Smart Home focus view
- report smart home status in `/api/health/full`

Not supported yet:

- locks
- alarms
- cameras
- garage doors
- covers
- climate control
- media players
- vacuums
- arbitrary Home Assistant service calls
- AI-generated device control

## Safety Model

| Category | Domains | Behavior |
| --- | --- | --- |
| Low risk | `light`, `switch`, `scene` | Allowed through explicit endpoints |
| Read only | `sensor`, `binary_sensor` | Can be read, not controlled |
| High risk | `lock`, `camera`, `alarm_control_panel`, `garage_door`, `cover`, `vacuum` | Blocked |
| Future | `climate`, `media_player` | Blocked until permissions are designed |

The frontend cannot call raw Home Assistant services by name. There is a guard
route that rejects arbitrary service calls with `403`.

## Endpoints

| Method | Endpoint |
| --- | --- |
| `GET` | `/api/smart-home/status` |
| `GET` | `/api/smart-home/entities` |
| `GET` | `/api/smart-home/entities/{entity_id}` |
| `GET` | `/api/smart-home/sensors` |
| `POST` | `/api/smart-home/entities/{entity_id}/turn-on` |
| `POST` | `/api/smart-home/entities/{entity_id}/turn-off` |
| `POST` | `/api/smart-home/scenes/{entity_id}/activate` |

## Frontend

The Smart Home focus view shows:

- connection status
- supported lights and switches
- scene activation
- read-only sensors
- calm setup guidance when Home Assistant is disabled or unconfigured

It intentionally stays small. The mirror home screen should not become a device
dashboard.

## Assistant Boundary

Mirrage can answer awareness prompts such as:

```text
show my smart home devices
show sensors
```

Those prompts do not give the AI model free device control. Device actions still
go through deterministic endpoints and backend safety checks.

## Privacy

The Home Assistant token stays on the backend. It is not sent to the frontend,
not returned by health checks, and should not be logged.

Smart home status and entity names may reveal private home details, so logs only
record operational events such as discovery success, provider failure, and
blocked actions.

## Future Work

- test against the real home Home Assistant instance
- add room grouping and better names
- add entity-level permission rules
- add confirmation prompts for sensitive actions
- add voice commands for approved devices
- persist user smart home preferences locally
