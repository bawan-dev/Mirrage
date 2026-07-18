# Security Model

Mirrage is a local home appliance, but local network access is not treated as
proof of identity. The security model assumes browsers, devices, assistant
prompts, and integration payloads can be wrong or hostile.

## Rules

- Protected routes default to deny.
- A missing, malformed, unknown, or revoked device token does not become an
  owner session.
- Names, roles, IP addresses, headers, wake phrases, and transcripts supplied by
  a client are not authentication evidence.
- Explicit permission denies take precedence over role grants and explicit
  grants.
- Permission and safety decisions are deterministic backend code.
- AI output cannot grant permissions, approve requests, or bypass policy.
- Locks, garage doors, alarms, cameras, covers, vacuums, and arbitrary Home
  Assistant service calls remain globally blocked.
- Audit metadata is allow-listed and redacted. Raw tokens, hashes, memory values,
  calendar details, transcripts, OAuth secrets, and audio are excluded.

## Route Classification

| Class | Current examples |
| --- | --- |
| Public | `/`, `/health`, `/api/health`, `/api/info/weather`, OAuth callbacks |
| Authenticated | `/api/identity/me`, approval creation and cancellation |
| Private | memory, daily context, proactive summaries, Calendar events, Spotify state, smart-home state |
| Administrative | full health, identity users/devices, permissions, approval decisions, audit events, presence settings |

OAuth callback routes must remain reachable by their providers. They complete an
integration protocol but do not return private Calendar or Spotify data.

## Authentication Assurance

| Method | Assurance | Meaning |
| --- | --- | --- |
| Anonymous | anonymous | no authenticated identity |
| Development | low | explicit local bypass; never valid in production |
| Trusted device | trusted_device | valid active bearer token for an active device and user |

No multi-factor or biometric method exists yet. The `future_multi_factor` model
value is an extension point, not a current claim.

## Assistant Boundary

Basic assistant use requires `assistant.use`. Before deterministic assistant
handlers access memory, personal context, or smart-home state, the route checks
the matching private permission. Model context can include a safe display name,
role, or capability summary later, but device identifiers, tokens, and evidence
must not be sent to a model.

## Known Limitations

- Device bearer tokens are long-lived credentials until revoked. Browser entry
  is kept in memory only; a secure cookie/session flow is future work.
- There is no user-scoped memory partition yet.
- Approval records establish workflow state but do not unlock currently blocked
  device classes.
- Real-world phone, UWB, voice, vision, vehicle, and wearable identity evidence
  remains unimplemented.
