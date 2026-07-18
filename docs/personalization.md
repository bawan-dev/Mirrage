# Personalization

Personalization is deterministic backend behavior built from a user's profile,
not a model-generated personality.

## Profile Settings

A profile can store:

- preferred name and optional pronouns
- language, tone, and response length
- greeting style
- proactive behavior mode
- quiet hours
- cloud personalization consent
- visibility for each profile field

New profiles are private by default. A user edits only their own profile.
Being the installation owner does not bypass another user's field visibility.

## Greetings And Proactivity

Greetings use local rules and the current human session. Without an active
human session, Mirror Mode uses a generic greeting and does not expose a name.
Quiet hours and the `silent` proactive mode suppress unsolicited private
briefings.

This phase does not let AI decide when to interrupt someone. Proactive behavior
remains a small, auditable ruleset.

## Local And Cloud Context

Local providers may receive the current user's allowed communication settings,
preferred name, and explicitly accessible shared context.

Cloud providers receive only communication preferences after explicit cloud
personalization consent. A preferred name is included only when that field is
public. Shared context values are never sent to cloud providers in this phase.

```text
profile + visibility + human session
  -> deterministic context filter
  -> local provider context
  -> smaller opt-in cloud context
```

No assistant response can modify a profile, relationship, shared item, or
permission. Changes use typed API endpoints and are audited without recording
private values.

## Current Limits

- Language and tone settings guide prompts; they do not guarantee a provider's
  exact writing style.
- No learned preference model or automatic profile inference exists.
- Memory remains installation-wide and owner-private until a later migration.
