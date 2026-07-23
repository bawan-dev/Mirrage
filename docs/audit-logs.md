# Audit Logs

The identity database contains a durable append-only audit table. Database
triggers reject normal update and delete operations. There is no audit edit or
delete API.

Events cover authentication, authorization, user and device changes, permission
overrides, approval decisions, profile settings changes, relationship consent,
shared-context access changes, human-session lifecycle events, sensitive data
access, backups, and smart-home control attempts/results.

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
- profile field values, shared-context titles, and shared-context values

Relationship and profile events record public identifiers, lifecycle actions,
and outcomes only. They do not record the private content that changed. Human
session creation records the user and device identifiers but never the raw
session token or its hash.

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

## Agent Events

The audit store records run creation, planning, plan validation or rejection,
authorization decisions, approval requests and decisions, tool start and
result, pause, resume, cancellation, completion, timeout, and denied cross-user
reads.

Agent audit metadata is limited to public run or step IDs, agent type, tool
name, step number, status, and safe error summaries. It does not include the
goal, complete prompt, raw arguments, memory values, Calendar content,
relationship data, tokens, or model chain-of-thought.

User-facing progress is stored separately in `agent_events`. Those events are
owner-scoped and also omit raw arguments.
