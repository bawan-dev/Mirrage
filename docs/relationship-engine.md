# Relationship Engine

Mirrage keeps identity, relationships, and authorization separate.

- **Identity** answers which user and trusted device made a request.
- **Relationships** record mutual household context between two users.
- **Permissions** decide which backend operations a principal may perform.

Accepting a relationship does not add permissions, weaken route policy, or make
private profile fields visible. It only allows fields explicitly marked with
`relationship` visibility. Shared context has a separate explicit recipient or
visibility decision.

## Lifecycle

```text
proposed -> active
         -> rejected

active -> archived
```

Either participant may propose a relationship. The other participant must
accept it before it becomes active. Self-relationships and duplicate pending or
active pairs are rejected. Either participant can archive an active
relationship.

The API does not model relationship labels as authority. Values such as
`partner`, `parent`, `sibling`, or `friend` are descriptive only.

## Storage

Identity schema version 2 adds:

- `personalization_profiles`
- `relationships`
- `shared_context_items`
- `shared_context_access`
- `interaction_sessions`

The migration preserves existing Phase 38 users and creates a private profile
for each one. It is safe to run more than once. Relationship records use public
UUIDs at the API boundary and internal foreign keys in SQLite.

## Human Sessions

A trusted mirror authenticates the appliance, not the person standing in front
of it. Private mirror requests therefore require a short-lived human
interaction session in addition to the trusted-device token.

```text
trusted mirror token + temporary human session -> private mirror request
trusted mirror token without session           -> generic mirror state
```

Session tokens are returned once and stored only as hashes. They are bound to a
specific user and device, expire automatically, and can be ended early. Current
activation is an explicit user selection, not biometric or voice recognition.

## API

See [API](api.md) for the complete endpoint table. The main groups are:

- `/api/profile/me` and `/api/profiles/*`
- `/api/relationships/*`
- `/api/shared-context/*`
- `/api/sessions/*`

## Current Limits

- No face, voice, proximity, UWB, or wearable identity proof exists yet.
- The existing memory database is not migrated into per-user storage.
- Relationship suggestions and profile changes are not inferred by AI.
- Relationship labels do not establish legal, parental, or household authority.

Read [Relationship privacy](relationship-privacy.md), [Shared context](shared-context.md),
and [Permissions](permissions.md) before extending this layer.
