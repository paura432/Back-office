# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

> _Spanish version: [README.es.md](./README.es.md)._

## Current Service

`api/` contains the minimal FastAPI development service. Its only application
endpoint is `GET /health`, returning `{"status":"ok"}`. See [api/README.md](api/README.md)
for local usage and dependency updates. No business logic, database or auth is added.

From the repository root, `docker compose up --build -d --wait` builds this folder's
Dockerfile and starts the `api` container on loopback port 8000 with Uvicorn reload.
The service uses Python 3.12.10, uv 0.6.17 and frozen dependencies from `api/uv.lock`.
Sources are bind-mounted at `/app`; dependencies are installed outside the mount.
Other containers use `api:8000`; browsers use the Next.js frontend's `/api` rewrite.
