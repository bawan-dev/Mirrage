# Mirrage Backend

FastAPI service for Mirrage.

## Run

```powershell
# from the repository root, with the venv active
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Health check: http://127.0.0.1:8000/health
Interactive docs: http://127.0.0.1:8000/docs

## Identity Bootstrap

Identity mode defaults to development, but the bypass is off unless explicitly
enabled. Create the first owner and trusted device from the repository root:

```powershell
python -m backend.app.identity_cli bootstrap-owner --name "Owner Name" --device-name "Primary Mirror"
```

The command works only while the identity store has no users. It prints the
trusted-device token once; Mirrage stores only its SHA-256 hash. Production
startup requires enforced identity mode, an active owner, and no development
bypass. See [Identity and Safety](../docs/identity-safety.md) for the full model.

## Develop

```powershell
pip install -r backend/requirements-dev.txt
ruff check .
ruff format --check .
pytest
```

## Layout

- `app/main.py` - FastAPI app and middleware
- `app/routes.py` - application and integration routes
- `app/identity_routes.py` - identity, trusted-device, approval, and audit routes
- `app/identity_cli.py` - first-owner bootstrap and identity backup operations
- `app/schemas.py` - request and response models
- `app/services/` - identity, policy, system, voice, assistant, context, memory, and integration boundaries
- `tests/` - pytest suite
