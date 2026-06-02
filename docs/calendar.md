# Google Calendar

Mirrage can connect to Google Calendar through the backend and show today's
schedule in the Calendar focus view.

What works now:

- Google OAuth login through the backend
- read-only Calendar API scope
- today's events
- upcoming events
- daily schedule focus view
- assistant command: `What is on my calendar today?`

The frontend never talks to Google directly. It calls Mirrage backend endpoints,
and the backend calls the Google Calendar API.

## Requirements

- a Google Cloud project
- Google Calendar API enabled
- an OAuth client ID for a web application
- a Google account allowed to authorize that OAuth app

## Google Cloud Setup

1. Open Google Cloud Console.
2. Enable the Google Calendar API for the project.
3. Configure the OAuth consent screen.
4. Create an OAuth client ID with application type `Web application`.
5. Add this authorized redirect URI:

```text
http://127.0.0.1:8000/api/integrations/calendar/callback
```

Google requires the redirect URI in the OAuth request to exactly match the value
configured for the OAuth client.

## Local Setup

Add these values to `.env`:

```powershell
MIRRAGE_GOOGLE_CALENDAR_CLIENT_ID=your-client-id
MIRRAGE_GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret
MIRRAGE_GOOGLE_CALENDAR_REDIRECT_URI=http://127.0.0.1:8000/api/integrations/calendar/callback
MIRRAGE_GOOGLE_CALENDAR_ID=primary
MIRRAGE_GOOGLE_CALENDAR_TIME_ZONE=Europe/London
MIRRAGE_FRONTEND_URL=http://127.0.0.1:5173
```

Restart the backend after editing `.env`.

Open the Calendar focus view and click `Connect Google Calendar`. After approval,
Mirrage redirects back to the frontend and the Calendar view can load today's
schedule.

## Docker Setup

Docker Compose reads Calendar values from your shell or `.env` file:

```powershell
docker compose up --build
```

If the backend container starts without Google Calendar credentials, the Calendar
view will show a setup-needed state.

## Scope

Mirrage uses this read-only scope:

```text
https://www.googleapis.com/auth/calendar.events.readonly
```

That is enough to read events without asking for permission to create, edit, or
delete calendar data.

## Token Storage

The first implementation stores Google Calendar tokens in backend memory.

That means:

- reconnect after restarting the backend
- no token is committed to Git
- no database is required yet

Before production, Calendar tokens should move to an encrypted persistent store.

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/integrations/calendar/status` | Check configuration and auth state |
| `GET` | `/api/integrations/calendar/login` | Start Google OAuth |
| `GET` | `/api/integrations/calendar/callback` | OAuth callback from Google |
| `GET` | `/api/integrations/calendar/events/today` | Read today's schedule |
| `GET` | `/api/integrations/calendar/events/upcoming` | Read upcoming events |
