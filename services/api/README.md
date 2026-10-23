# TrackFlow Development API

FastAPI service for the development stack. `GET /health` returns
`{"status":"ok"}`. `GET /status` checks PostgreSQL with `SELECT 1` and returns
`operational` or `degraded` without exposing connection details. The declared
business and authentication routes remain explicit `501 Not Implemented` stubs;
they do not implement business behavior or authentication/authorization.

## Local Development

Requires Python 3.12 and uv 0.6.17 or compatible newer version:

```sh
uv sync --frozen
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Runtime and testing dependencies, including transitive packages and hashes, are
recorded in `uv.lock`. Install tests with `uv sync --frozen --extra dev` and run
them with `uv run --frozen --extra dev pytest -q`. To intentionally update a
dependency, edit `pyproject.toml` and run the pinned project uv version's
`uv lock`.

## Docker Development

From the repository root, run `docker compose up --build -d`. Compose installs
locked dependencies automatically, mounts this directory and runs Uvicorn with
`--reload`. The virtual environment is outside the bind mount at `/opt/venv`.

The service is available internally at `http://api:8000/health` and locally at
`http://localhost:8000/health`. Browser clients use `/api/health` on either Next.js
frontend; Next.js rewrites proxy to the API and strip `/api`.