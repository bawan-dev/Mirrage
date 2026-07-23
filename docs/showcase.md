# Showcase Notes

Use this page when explaining Mirrage in a portfolio review or interview.

## Short Pitch

Mirrage is a privacy-first ambient AI mirror platform. It combines a React mirror
interface, FastAPI backend, AI runtime, local memory, presence engine, smart-home
boundary, v2 identity, relationship, privacy, and bounded-agent foundations,
production deployment setup, and physical hardware build planning.

## Why It Is Technically Interesting

- It is built as a system, not a single frontend page.
- The frontend is mirror-first, with sparse typography and focus views instead
  of a traditional dashboard.
- The backend owns integrations and service state so the browser does not talk
  directly to AI providers, Spotify, Calendar, or Home Assistant.
- Memory and daily context are local-first and deterministic before model calls.
- Wake-word handling is designed around local detection before any cloud service
  sees speech.
- Smart home actions are restricted to safe domains instead of letting free-form
  AI call arbitrary home services.
- Trusted-device authentication, role permissions, approvals, and append-only
  audit events are backend-owned. Names and AI output are not authentication.
- Profiles are private by default. Relationships require consent, never grant
  permissions, and expose only deliberately visible or shared context.
- A trusted mirror identifies the appliance; a temporary hash-only session is
  still required before private user data appears.
- Agent runs persist structured plans but can execute only registered tools.
  Backend policy rechecks permissions per step, every side effect needs a
  separate approver, and users can pause or cancel a bounded run.
- Production docs cover Docker, systemd, health checks, logs, backups, and
  hardware installation planning.

## Architecture Decisions To Mention

- React + Vite keeps the mirror UI simple and portable.
- FastAPI gives a clean API boundary for the assistant and integrations.
- SQLite is used for local memory because v1 is a single-user local appliance.
- A separate versioned SQLite store begins v2 household identity without
  pretending the existing memory database is already multi-user.
- Provider routing keeps `stub`, Ollama, and OpenAI-compatible APIs behind one
  assistant interface.
- Demo mode is explicit so fake portfolio data cannot be confused with
  production behavior.
- The AI Runtime proposes plans and summaries; deterministic backend code owns
  authorization, approval, limits, and tool execution.

## Honest Limitations

- The physical mirror still needs real display, glass, heat, microphone, and
  mounting validation.
- Wake-word code supports the engine boundary, but a real trained `Hey Mirrage`
  model still needs target hardware testing.
- Spotify, Calendar, Home Assistant, and non-stub AI providers require local
  configuration.
- Browser speech APIs depend on browser support.
- Trusted-device tokens authenticate clients, but real voice, face, UWB, phone,
  vehicle, and wearable identity evidence is not implemented.
- Mirror user activation is an explicit selection, not human recognition.
- Existing local memory is still installation-wide and owner-private rather
  than partitioned by relationship.
- Agents are disabled by default. They do not have live web research, arbitrary
  computer control, messaging, purchases, bookings, or security-critical home
  tools.

## Suggested Walkthrough Order

1. Mirror Mode home
2. Assistant focus view
3. Daily Briefing / Context
4. Weather
5. Calendar or Media
6. Smart Home boundary
7. Normal-mode Identity view and default-deny policy
8. Normal-mode Profile/Relationships workspace and privacy controls
9. Normal-mode Agent workspace with a read-only bounded task
10. Architecture and deployment docs
11. Physical mirror build plan
