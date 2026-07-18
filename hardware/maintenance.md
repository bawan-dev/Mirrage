# Maintenance

Mirrage should be built like something that can be repaired.

Do not make a sealed mirror that has to be destroyed to replace a cable,
microphone, display, or mini PC.

## Required Access

- mini PC power button
- mini PC USB ports
- display power and video cables
- microphone cable
- speaker cable
- Ethernet cable
- power strip or main plug
- removable storage if used
- frame mounting hardware

## Maintenance Tasks

| Task | Plan |
| --- | --- |
| Software update | Pull latest repo, rebuild Compose, restart service |
| Health check | Use `/api/health`; use an owner token for `/api/health/full` |
| Logs | Read Docker logs or `logs/backend.log` |
| Backups | Use local backup process for SQLite memory |
| Microphone replacement | Keep USB access reachable |
| Speaker replacement | Mount speakers without permanent glue |
| Display replacement | Use removable back and standard mount where possible |
| Mirror cleaning | Use material-safe cleaner and soft cloth |
| Reboot recovery | systemd starts Docker stack after boot |

## Cleaning

- Use a soft microfiber cloth.
- Avoid harsh cleaners on acrylic.
- Do not press hard on acrylic or thin glass.
- Keep liquid away from frame edges and electronics.

## Serviceability Rules

- Use screws where future access is needed.
- Avoid permanent glue for electronics.
- Label important cables.
- Leave a small service loop.
- Keep model files, `.env`, logs, data, and backups documented.

The mirror should survive normal updates and part replacement without a rebuild.
