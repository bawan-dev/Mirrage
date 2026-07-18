# Identity And Safety Engine

Phase 38 starts Mirrage v2 with a backend-owned answer to a basic safety
question: who is allowed to do what from which trusted device?

The engine separates four concerns:

1. Identity is the household user record.
2. Authentication proves a request holds an active trusted-device token.
3. Authorization compares the authenticated principal with a central permission
   policy and the risk of the requested action.
4. Audit records the decision and result without recording secrets or private
   content.

The request flow is:

```text
API request
  -> bearer-token authentication
  -> authenticated principal
  -> deterministic permission and safety policy
  -> allowed / denied / approval required
  -> service action, when allowed
  -> append-only redacted audit event
```

The frontend does not authenticate a person by sending a name or role. AI
providers do not decide permissions. An assistant intent is authorized again by
the backend before private data or a physical action is reached.

## Local Data

Identity data lives in `data/mirrage-identity.sqlite3`. The database contains:

- household users and roles
- explicit per-user permission grants and denies
- trusted devices with token hashes, never raw tokens
- expiring approval requests and decisions
- append-only audit events
- a schema migration version

SQLite foreign keys, WAL mode, indexes, and a busy timeout are enabled. Audit
rows have database triggers that reject normal update and delete statements.

The existing memory database is still installation-wide. Phase 38 treats it as
owner-private and protects it with `memory.read_private` and
`memory.write_private`. It does not pretend memory is partitioned per user.

## Operating Modes

`development` keeps local development workable. An optional development
principal is available only when `MIRRAGE_IDENTITY_DEV_BYPASS=true`. It is
low-assurance, explicitly audited, and rejected when the application environment
is production.

`enforced` requires an active owner. Production Compose fixes identity to this
mode and fixes the development bypass to false.

`disabled` is available for diagnosis in non-production environments. It is not
accepted by production startup validation.

## Current Boundary

Mirrage can authenticate trusted API clients using device bearer tokens. It does
not recognize who is speaking. Wake-word detection, browser speech recognition,
IP addresses, room location, Bluetooth, UWB, phones, wearables, voice, and face
signals are not authentication in this phase.

Future evidence providers must feed the authentication service. They will not be
allowed to call memory, smart-home, or administrative services directly.

## Related Documentation

- [Security model](security-model.md)
- [Permissions](permissions.md)
- [Trusted devices](trusted-devices.md)
- [Approvals](approvals.md)
- [Audit logs](audit-logs.md)
- [API](api.md)
