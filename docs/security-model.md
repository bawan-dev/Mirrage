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
- A trusted mirror authenticates the appliance. It needs a valid temporary
  human session before private user data is returned.
- Relationship records and household membership do not grant permissions.
- Profile and shared-context visibility is checked even when the requester is
  the installation owner.
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

Trusted mirror devices add a second, short-lived interaction boundary. The
human session token is hash-only in SQLite, bound to one user and one mirror,
and sent through `X-Mirrage-Human-Session`. Manual selection is not biometric
assurance and must not be described as recognition.

## Relationship Privacy

Profiles are private by default and each field has its own visibility. An active
relationship can expose `relationship` fields, but does not expose private
fields and does not affect role permissions. Shared context requires a separate
explicit share for an active relationship and can be revoked.

Cloud personalization is opt-in. Cloud context receives communication settings
only; names require public visibility and shared context values are never sent
to a cloud provider in this phase.

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
- Explicit mirror user selection can be chosen by the wrong person; automatic
  human recognition evidence is not implemented.
- Sensitive shared-context term filtering is a guardrail, not a complete data
  loss prevention system.
- Approval records establish workflow state but do not unlock currently blocked
  device classes.
- Real-world phone, UWB, voice, vision, vehicle, and wearable identity evidence
  remains unimplemented.
