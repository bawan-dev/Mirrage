# Production Deployment

This guide is for running Mirrage continuously on a dedicated home device.

The recommended production path is:

```text
Linux host
  -> systemd
  -> Docker Compose production stack
  -> backend + frontend containers
  -> persistent data, backups, logs
```

## Recommended Hardware

Minimum practical target:

- Intel N100 mini PC, Raspberry Pi 5, or similar always-on Linux machine
- 8 GB RAM preferred
- 32 GB storage minimum, 64 GB or more preferred
- wired Ethernet if possible
- reliable power adapter
- display connected over HDMI or USB-C
- USB microphone or microphone array for future wake-word testing

Better target for local AI:

- Intel N100/N305 mini PC, small Ryzen mini PC, or Jetson-class device
- 16 GB RAM if running local models
- SSD storage
- active cooling or a proven passive case

Recommended first physical build:

- 27 inch IPS monitor with VESA mount
- Intel N100 mini PC
- two-way acrylic or smart mirror glass after visibility testing
- small wired speakers
- USB conference microphone or USB mic array
- deep ventilated frame with removable back panel

See [../hardware/physical-build.md](../hardware/physical-build.md) for the full
hardware plan.

## Software Requirements

- Ubuntu Server/Desktop, Raspberry Pi OS, Debian, or another systemd-based Linux
- Docker Engine and Docker Compose plugin
- Git
- Optional: Ollama if using a local model provider
- Optional: OpenWakeWord, `sounddevice`, `numpy`, and OS audio packages if
  testing local wake word directly on the host

## Install

Clone the repo:

```bash
sudo mkdir -p /opt/mirrage
sudo chown "$USER":"$USER" /opt/mirrage
git clone https://github.com/bawan-dev/Mirrage.git /opt/mirrage
cd /opt/mirrage
```

Create the environment file:

```bash
cp .env.example .env
```

For production, set at least:

```text
MIRRAGE_APP_ENV=production
MIRRAGE_FRONTEND_URL=http://127.0.0.1:5173
MIRRAGE_ALLOWED_ORIGINS=["http://127.0.0.1:5173"]
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_MIRROR_MODE=true
```

Add Spotify, Calendar, Ollama, or OpenAI-compatible settings only if those
features are being used.

For local wake word testing, keep the engine off until the microphone and model
file are ready:

```text
MIRRAGE_WAKE_ENGINE_ENABLED=false
MIRRAGE_WAKE_ENGINE_PROVIDER=openwakeword
MIRRAGE_WAKE_ENGINE_MODEL_PATH=models/wake/hey-mirrage.onnx
```

## Start With Docker Compose

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Verify:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/health/full
curl http://127.0.0.1:5173/health
```

Open:

```text
http://127.0.0.1:5173
```

## First Boot On Mirror Hardware

Use this after the operating system is installed on the target mini PC or
Raspberry Pi:

```text
1. Install OS.
2. Install Docker and Git.
3. Clone Mirrage.
4. Copy .env.example to .env.
5. Set VITE_MIRROR_MODE=true.
6. Start production Compose.
7. Enable the systemd service.
8. Open frontend in browser kiosk mode.
9. Verify /api/health/full.
10. Check /api/wake-word/status.
11. Check /api/smart-home/status.
12. Reboot and confirm Mirrage starts automatically.
```

Do this before installing the mirror permanently on the wall.

## Start On Boot With systemd

Copy the Docker service example:

```bash
sudo cp deploy/systemd/mirrage-docker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mirrage-docker
sudo systemctl start mirrage-docker
```

Check status:

```bash
systemctl status mirrage-docker
docker compose -f /opt/mirrage/docker-compose.prod.yml ps
```

The service starts Docker Compose after Docker and the network are available.
Both containers use `restart: unless-stopped`, so crashes restart automatically.

## Non-Docker systemd Option

The repo also includes:

- `deploy/systemd/mirrage-backend.service`
- `deploy/systemd/mirrage-frontend.service`

Use these only if running Python and Node directly on the host. Docker is the
preferred production path because it keeps the runtime more predictable.

## Stop, Restart, And Update

Stop:

```bash
docker compose -f docker-compose.prod.yml down
```

Restart:

```bash
docker compose -f docker-compose.prod.yml restart
```

Rebuild after changes:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The full update process is in [updates.md](updates.md).

## Persistent State

Production Compose mounts:

- `./data` for SQLite memory
- `./backups` for local backup files
- `./logs` for backend log files

These folders are intentionally ignored by Git.

Wake model files should live outside Git too. The suggested local path is:

```text
models/wake/hey-mirrage.onnx
```

The repo includes the folder placeholder but ignores real model files.

## Microphone And Wake Word Notes

For the first hardware test, run the backend directly on the host. Confirm the
microphone works there before trying Docker audio.

On Linux, wake-word testing may require:

- the user running Mirrage to have audio device permission
- ALSA, PulseAudio, or PipeWire packages depending on the OS
- a stable USB microphone or microphone array
- `MIRRAGE_WAKE_ENGINE_MICROPHONE` set to the correct device

Docker microphone access is possible but host-specific. It may require device
mounts or PulseAudio/PipeWire socket mounts. This repo does not yet include a
final production Docker audio configuration.

## Verification Checklist

- `/api/health` returns `online`
- `/api/health/full` returns JSON with backend, memory, AI runtime, providers,
  presence, wake engine, weather, Calendar, and Spotify checks
- frontend `/health` returns `ok`
- containers show healthy or running
- logs are being written to `logs/backend.log`
- `data/mirrage-memory.sqlite3` exists after memory is used
- backup command creates a file in `backups/`
- Mirror Mode opens in kiosk mode
- display is readable through the selected mirror material
- microphone, speakers, and wake engine status have been checked
- heat testing has passed before wall mounting

## Platform Notes

Raspberry Pi OS:

- use a high-quality power supply
- prefer Ethernet for reliability
- keep the OS fully updated before installation

Ubuntu or Debian:

- the Docker Compose plugin is usually the cleanest install path
- use systemd for boot startup

Mini PC:

- set BIOS/UEFI to power on after power loss
- disable unnecessary sleep settings
- use wired networking where possible
