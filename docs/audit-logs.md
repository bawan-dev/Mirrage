# Audit Logs

The identity database contains a durable append-only audit table. Database
triggers reject normal update and delete operations. There is no audit edit or
delete API.

Events cover authentication, authorization, user and device changes, permission
overrides, approval decisions, sensitive data access, backups, and smart-home
control attempts/results.

Audit records may contain public UUIDs, role, authentication method, action,
resource identifier, decision, risk, policy reason, result, and correlation ID.
Metadata accepts only short scalar values and drops sensitive key families.

The following must never appear:

- raw device tokens or token hashes
- API keys, OAuth secrets, or Home Assistant tokens
- memory values
- Calendar event content
- complete assistant transcripts
- microphone audio
- biometric data

## Query API

Owners can query `GET /api/audit/events` with:

- `limit` and `offset`
- `event_type`
- `user_id`
- `decision`
- `date_from` and `date_to`

The maximum page size is 200. Retention configuration is recorded now, but an
automatic deletion job is intentionally not implemented. Any future retention
cleanup must be an explicit audited maintenance operation.

Operational logs and audit logs are separate. Operational logs explain service
health; audit logs explain security decisions without private payloads.
