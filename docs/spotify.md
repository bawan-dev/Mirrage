# Spotify

Mirrage can connect to Spotify through the backend and show the current playback
state in the Media focus view.

## What Works

- Spotify OAuth login through the backend
- currently playing track
- artist, album, device, progress, and album artwork
- play/pause
- next/previous
- Media focus view integration

The frontend never talks to Spotify directly. It calls Mirrage backend endpoints,
and the backend calls the Spotify Web API.

## Requirements

- a Spotify Developer app
- a Spotify account authorized for that app
- Spotify Premium for playback control endpoints
- an active Spotify device for play/pause/next/previous to work

Spotify may return a control error if there is no active device or the account
cannot use playback controls.

## Spotify App Setup

1. Open the Spotify Developer Dashboard.
2. Create an app.
3. Add this redirect URI exactly:

```text
http://127.0.0.1:8000/api/integrations/spotify/callback
```

Spotify requires the redirect URI in the OAuth request to exactly match the value
registered on the app.

4. Copy the app's client ID and client secret.
5. Add them to `.env`:

```powershell
MIRRAGE_SPOTIFY_CLIENT_ID=your-client-id
MIRRAGE_SPOTIFY_CLIENT_SECRET=your-client-secret
MIRRAGE_SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/integrations/spotify/callback
MIRRAGE_FRONTEND_URL=http://127.0.0.1:5173
```

6. Restart the backend.
7. Open the Media focus view and click `Connect Spotify`.

## Docker Setup

Docker Compose reads Spotify values from your shell or `.env` file:

```powershell
docker compose up --build
```

If the backend container starts without Spotify credentials, the Media view will
show a setup-needed state instead of failing.

## Scopes

Mirrage requests:

```text
user-read-currently-playing
user-read-playback-state
user-modify-playback-state
```

These are enough to read playback state and control playback on Spotify Connect
devices.

## Current Token Storage

The first implementation stores Spotify tokens in backend memory.

That means:

- it is fine for local single-user development
- reconnecting is required after backend restart
- no database is required yet

A database or encrypted local token store becomes useful once Mirrage needs
persistent login, multiple users, or production deployment.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/integrations/spotify/status` | Check configuration and auth state |
| `GET` | `/api/integrations/spotify/login` | Start Spotify OAuth |
| `GET` | `/api/integrations/spotify/callback` | OAuth callback from Spotify |
| `GET` | `/api/integrations/spotify/player/currently-playing` | Read current playback |
| `POST` | `/api/integrations/spotify/player/play` | Resume playback |
| `POST` | `/api/integrations/spotify/player/pause` | Pause playback |
| `POST` | `/api/integrations/spotify/player/next` | Skip forward |
| `POST` | `/api/integrations/spotify/player/previous` | Skip backward |
