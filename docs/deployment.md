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

- Raspberry Pi 5, Intel N100 mini PC, or similar always-on Linux machine
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

## Software Requirements

- Ubuntu Server/Desktop, Raspberry Pi OS, Debian, or another systemd-based Linux
- Docker Engine and Docker Compose plugin
- Git
- Optional: Ollama if using a local model provider

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

## Verification Checklist

- `/api/health` returns `online`
- `/api/health/full` returns JSON with backend, memory, AI runtime, providers,
  presence, weather, Calendar, and Spotify checks
- frontend `/health` returns `ok`
- containers show healthy or running
- logs are being written to `logs/backend.log`
- `data/mirrage-memory.sqlite3` exists after memory is used
- backup command creates a file in `backups/`

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
