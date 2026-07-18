# Trusted Devices

A trusted device is the authentication credential boundary for Mirrage v2.
Users and devices have separate public UUIDs. A device belongs to one active
user and has a type, trust level, status, and optional non-secret metadata.

## First Owner

Bootstrap works only while the identity store has no users:

```powershell
python -m backend.app.identity_cli bootstrap-owner `
  --name "Owner Name" `
  --device-name "Primary Mirror"
```

The command creates the owner and an optional privileged mirror device. It
prints the raw device token once. Move that token to an appropriate local secret
store; do not commit it, place it in a `VITE_` variable, paste it into docs, or
write it to normal logs.

The bootstrap command refuses to run after any user exists. There is no default
owner, password, or production token.

## Token Design

- Python `secrets` generates at least 32 random bytes.
- The API token contains a non-secret lookup prefix and random secret material.
- SQLite stores the prefix and a SHA-256 hash of the high-entropy full token.
- Authentication uses constant-time hash comparison.
- Enrollment returns the plaintext token once.
- List and detail APIs never return the token, prefix, or hash.
- Revocation immediately stops authentication and records an audit event.

The browser admin view keeps a pasted token only in module memory. Reloading or
closing the page clears it. `localStorage` is not used.

## Enrolling Another Device

An owner can call:

```powershell
$headers = @{ Authorization = "Bearer <OWNER_DEVICE_TOKEN>" }
$body = @{
  user_id = "<USER_PUBLIC_UUID>"
  display_name = "Kitchen Mirror"
  device_type = "mirror"
  trust_level = "trusted"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/identity/devices" `
  -Headers $headers -ContentType "application/json" -Body $body
```

Capture the returned token at enrollment time. It cannot be retrieved later.

## Revocation

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/identity/devices/<DEVICE_UUID>/revoke" `
  -Headers $headers
```

The revoked token should then receive HTTP `401` from `/api/identity/me`.

## Owner Recovery

There is deliberately no unauthenticated recovery endpoint. Back up the identity
database after owner/device changes. If all owner devices are lost, stop Mirrage,
restore a known-good local identity backup, and enroll a replacement device from
a controlled maintenance environment. Recovery should be treated as access to
private household data, not as a normal browser flow.
