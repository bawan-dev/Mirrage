# Relationship Privacy

Relationship data is private household data. Mirrage uses explicit visibility
and consent instead of assuming that a household role may see everything.

## Visibility Levels

| Level | Who can see the field or item |
| --- | --- |
| `private` | Owner of the data only |
| `relationship` | Owner and users with an active relationship |
| `household` | Owner and active household members |
| `public` | Authenticated directory users |

Visibility is evaluated for each field. A visible preferred name does not make
pronouns, quiet hours, or any other field visible. Installation owners follow
the same rule when viewing another profile.

## Consent Rules

- Both users must participate before a relationship is active.
- A relationship can be rejected or archived.
- Shared context starts private.
- Direct sharing names the specific user who receives access.
- `relationship` visibility requires an active relationship independently of
  direct sharing.
- Revocation takes effect on later reads.
- Relationship state never changes role permissions.

## Sensitive Data

Shared context is intended for low-risk household coordination such as an
anniversary reminder or a shared routine. The API rejects obvious sensitive
categories such as credentials, financial identifiers, health records, and
security codes.

That keyword guard is a conservative safety check, not a complete content
classifier. Users should not store secrets in shared context. Raw values are not
written to audit events, operational logs, or cloud AI context.

## Threat Boundaries

- A stolen trusted-device token remains a credential risk until revoked.
- Explicit mirror user selection is not proof that the selected person is
  physically present.
- Database administrators can access local SQLite files; host and backup access
  must therefore be protected.
- No biometric inference or automatic relationship discovery is performed.

See [Security model](security-model.md), [Trusted devices](trusted-devices.md),
and [Backups](backups.md).
