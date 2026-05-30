# Mirrage Backend

FastAPI service for Mirrage.

## Run

```powershell
# from the repository root, with the venv active
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Health check: http://127.0.0.1:8000/health — interactive docs: http://127.0.0.1:8000/docs

## Develop

```powershell
pip install -r backend/requirements-dev.txt
ruff check .          # lint
ruff format .         # format
pytest                # run the test suite
```

## Layout

- `app/main.py` — FastAPI app and middleware
- `app/routes.py` — route definitions
- `app/schemas.py` — request/response models
- `app/services/` — system, voice, and assistant service boundaries
- `tests/` — pytest suite
