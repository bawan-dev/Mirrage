# Home Assistant Setup

Mirrage uses Home Assistant as the first smart home provider.

Home Assistant is optional. If it is not configured, Mirrage returns disabled or
unconfigured status instead of crashing.

## Required Values

Add these to `.env`:

```text
MIRRAGE_SMART_HOME_ENABLED=true
MIRRAGE_SMART_HOME_TIMEOUT_SECONDS=5
MIRRAGE_HOME_ASSISTANT_ENABLED=true
MIRRAGE_HOME_ASSISTANT_BASE_URL=http://homeassistant.local:8123
MIRRAGE_HOME_ASSISTANT_TOKEN=your-long-lived-access-token
```

Restart the backend after changing `.env`.

## Create A Long-Lived Token

In Home Assistant:

1. Open your profile.
2. Go to Long-Lived Access Tokens.
3. Create a token for Mirrage.
4. Copy it once.
5. Paste it into `.env` as `MIRRAGE_HOME_ASSISTANT_TOKEN`.

Do not commit `.env`.

## Local Check

Start the backend, then run:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/smart-home/status
```

Expected when connected:

- `enabled` is `true`
- `configured` is `true`
- `connection_status` is `connected`
- `entity_count` is greater than or equal to `0`

Check discovered entities:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/smart-home/entities
Invoke-RestMethod http://127.0.0.1:8000/api/smart-home/sensors
```

## Control Check

Use an entity ID returned from `/api/smart-home/entities`.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/smart-home/entities/light.kitchen/turn-on" -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/smart-home/entities/light.kitchen/turn-off" -Method Post
```

Scene example:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/smart-home/scenes/scene.evening/activate" -Method Post
```

Only use entity IDs that exist in your Home Assistant instance.

## Docker

The Compose files pass these environment variables through to the backend:

```text
MIRRAGE_SMART_HOME_ENABLED
MIRRAGE_SMART_HOME_TIMEOUT_SECONDS
MIRRAGE_HOME_ASSISTANT_ENABLED
MIRRAGE_HOME_ASSISTANT_BASE_URL
MIRRAGE_HOME_ASSISTANT_TOKEN
```

If Docker cannot reach `homeassistant.local`, use the Home Assistant machine's
local IP address instead.

## Troubleshooting

`disabled` means Mirrage smart home support is off.

`provider_disabled` means Mirrage is enabled, but the Home Assistant provider is
off.

`unconfigured` means the URL or token is missing.

`unavailable` means Mirrage tried Home Assistant and the request failed.

Common fixes:

- confirm Home Assistant is running
- confirm the URL is reachable from the backend machine or container
- confirm the token is valid
- restart the backend after changing `.env`
- check `/api/health/full` for the smart home health component
