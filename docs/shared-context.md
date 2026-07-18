# Shared Context

Shared context lets one user deliberately expose a small household fact or
routine to an active relationship. It is separate from the existing memory
store and is private by default.

Examples that fit this layer:

- a shared anniversary reminder
- a household pickup routine
- a jointly agreed preference for a common space

Examples that do not fit:

- passwords, access codes, or API keys
- bank, government, or medical identifiers
- private Calendar event bodies
- complete assistant transcripts

## Access Flow

```text
create item (private)
  -> choose a specific active user or broader safe visibility
  -> share explicitly when using a named user
  -> authorized participant may read
  -> owner may revoke or archive
```

Direct sharing is per item and per user. `relationship` visibility is evaluated
separately and only active relationships qualify. Archiving an item removes it
from normal reads. Archiving a relationship removes visibility that depended on
that relationship, but does not silently rewrite explicit user access; owners
can revoke that access directly.

## AI Boundary

The local personalization builder may include an item only after the same
visibility and relationship checks used by the API. Cloud AI context excludes
shared values in this phase, even when cloud personalization is enabled.

The assistant does not create, share, or revoke items from free-form model
output. Those changes use typed endpoints so consent and audit behavior remain
clear.

## Relationship To Memory

The Phase 21 memory store remains installation-wide and owner-private. Phase 39
does not copy or reinterpret those rows. A future per-user memory migration must
define ownership, consent, deletion, and backup behavior before it can use
relationship sharing.
