# Tech Stack — TrackFlow Incident Manager

## Stack / convenios preexistentes (del monorepo)

| Capa | Tecnología | Gestor | Evidencia |
|---|---|---|---|
| JS/TS | TypeScript | pnpm (Corepack) | `.devcontainer/post-create.sh` |
| Python | Python 3 | uv | `.devcontainer/post-create.sh` |
| Backend | FastAPI (centralizado) | uv | `services/README.md` |
| Frontend | Pendiente de decidir por proyecto | pnpm | `uis/README.md` |
| Tipos compartidos | `packages/shared/@repo/shared-types` | pnpm | `packages/shared/package.json` |
| Infra | Sin definir | — | `infra/` solo READMEs |
| Tests | Sin decisión previa | — | No hay tests implementados |

## Decisiones técnicas nuevas para el Incident Manager

### Backend — `services/api/`

| Decisión | Valor | Justificación |
|---|---|---|
| Framework | FastAPI (ya establecido) | Convención del monorepo |
| Gestor Python | uv | Convención del monorepo |
| Base de datos | SQLite (`sqlite3` estándar) | Desarrollo local, sin infra desplegada |
| ORM | **No** — `sqlite3` directo | Fase inicial. Sin ORM. Evaluar SQLAlchemy en fase posterior si se migra a PostgreSQL |
| Auditoría | Tabla separada `incident_audit_log` | Requisito de trazabilidad no negociable |
| Tests | pytest | Elección nueva para este proyecto |

### Frontend — `uis/backoffice/`

| Decisión | Valor | Justificación |
|---|---|---|
| Framework UI | **Ninguno** — HTML/CSS/TypeScript vanilla | Mantener complejidad cero. Sin React, Vue ni Svelte |
| Lenguaje | TypeScript + Vite | Build tool mínima, compatible con tipos compartidos |
| Gestor | pnpm (Corepack) | Convención del monorepo |
| Proxy API | Vite proxy → backend en desarrollo | Evitar CORS en desarrollo |
| Consumo tipos | Ruta relativa desde `packages/shared/types/` | El entrypoint del package está roto (documentado), no depender de `@repo/shared-types` todavía |
| Tests | Validación manual + test de tipos | Sin framework de tests frontend en esta fase |

### Integración

| Aspecto | Decisión |
|---|---|
| Prefijo API | `/api` desde frontend |
| Orchestación | No usar Docker Compose. Los dos procesos se ejecutan manualmente (Vite dev server + uvicorn) |
| Puerto API | 8000 (por defecto FastAPI) |
| Puerto frontend | 5173 (por defecto Vite) |