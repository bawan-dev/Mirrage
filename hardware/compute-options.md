# Compute Options

The compute device should run Mirrage reliably without making the mirror hot,
noisy, or hard to maintain.

## Options

| Option | Pros | Risks |
| --- | --- | --- |
| Raspberry Pi 5 | Small, low power, good community support | Weaker for local AI, can still need cooling |
| Intel N100 mini PC | Strong first-build target, Docker-friendly, low power | More expensive than Pi |
| Intel N305 mini PC | More headroom than N100 | Higher cost and heat |
| Older small form factor PC | Cheap used, more CPU headroom | Bigger, more power, more heat |
| Repurposed laptop | Built-in screen/keyboard for setup | Awkward mounting, battery/heat concerns |
| Jetson device | Useful for future vision/AI | Overkill for first mirror, more setup complexity |
| Dedicated AI server | Keeps heavy AI away from mirror | More infrastructure, not required for v1 |

## Recommendation

Recommended first wall build: **Intel N100 mini PC**.

Why:

- runs Linux and Docker comfortably
- enough CPU for frontend, FastAPI, health checks, logging, and wake engine
- better local service headroom than Raspberry Pi
- compact enough to mount behind or near the mirror
- lower power and heat than old desktop hardware
- keeps the first build practical without needing a GPU

## Raspberry Pi 5 Position

Raspberry Pi 5 is still useful for:

- lightweight frontend/backend
- low-power experiments
- simple wall display

But it is weaker for:

- local AI
- future local speech-to-text
- heavier background services
- running multiple containers comfortably

## Future AI Server

Preferred long-term architecture:

```text
Physical Mirror
  -> mini PC runs UI, backend, wake engine, integrations
  -> LAN connects to optional AI server for heavy local models
```

The first physical mirror does not need a workstation GPU. GPUs are future AI
infrastructure, not a requirement for the first wall-mounted prototype.

## Minimum Practical Specs

Recommended:

- Intel N100 or better
- 8 GB RAM minimum, 16 GB if budget allows
- SSD storage
- Linux support
- Ethernet port if possible
- enough USB ports for microphone and setup devices
- VESA or bracket-friendly case

## Placement

Options:

- inside a ventilated frame with service access
- behind the mirror but offset from the hottest display area
- below/near the mirror with one tidy cable bundle

For the first build, accessibility matters more than hiding everything.
