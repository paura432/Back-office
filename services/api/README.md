# TrackFlow Development API

Minimal FastAPI service for the development stack. `GET /health` returns
`{"status":"ok"}`. No business endpoints, authentication or database are implemented.

## Local Development

Requires Python 3.12 and uv 0.6.17 or compatible newer version:

```sh
uv sync --frozen
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Dependencies, including transitive packages and hashes, are recorded in `uv.lock`.
To intentionally update them, edit `pyproject.toml` and run `uv lock`.

## Docker Development

From the repository root, run `docker compose up --build -d`. Compose installs
locked dependencies automatically, mounts this directory and runs Uvicorn with
`--reload`. The virtual environment is outside the bind mount at `/opt/venv`.

The service is available internally at `http://api:8000/health` and locally at
`http://localhost:8000/health`. Browser clients use `/api/health` on either Next.js
frontend; Next.js rewrites proxy to the API and strip `/api`.