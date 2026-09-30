# backoffice-stack.md

> Regla derivada del plan aprobado para el TrackFlow Incident Manager, no del código preexistente.
> Documenta las decisiones técnicas cerradas para el stack del backoffice y su backend asociado.

---

- **Aplicación:** `manual` (aplica solo al desarrollo del Incident Manager y proyectos que sigan su plan aprobado)
- **Ámbito/patrón de archivos:** `services/api/**`, `uis/backoffice/**`, `packages/shared/types/**/*incident*.ts`

## Evidencia de origen

- `memory-bank/tech-stack.md` — Decisiones técnicas cerradas para el Incident Manager.
- `memory-bank/implementation-plan.md` — Plan de implementación aprobado antes del código.
- `relevant existing rules`: `repository-structure.md`, `dependency-management.md`, `shared-types.md`.

## Qué se debe hacer

### Backend — `services/api/`
- Usar **FastAPI** como framework (convención del monorepo).
- Usar **uv** para gestión de dependencias Python.
- Usar **SQLite** con la librería estándar `sqlite3` (sin ORM en esta fase).
- Usar **pytest** para tests backend.
- Guardar la auditoría en una tabla separada `incident_audit_log`.

### Frontend — `uis/backoffice/`
- Usar **TypeScript + Vite** sin framework UI (sin React, Vue, Svelte).
- Usar **pnpm** (vía Corepack) para gestión de dependencias JS/TS.
- Consumir los tipos compartidos desde `packages/shared/types/` con ruta relativa (no depender aún del entrypoint `@repo/shared-types`).

### Integración
- Prefijo `/api` desde el frontend hacia el backend.
- Proxy de Vite al backend en desarrollo (`localhost:8000`).
- No introducir Docker Compose si no es necesario para ejecutar ambos procesos.

## Qué NO se debe hacer

- ❌ Introducir React, Vue, Svelte u otro framework UI en `uis/backoffice/` sin una decisión explícita y documentada que justifique el cambio.
- ❌ Usar un ORM (SQLAlchemy, Prisma, etc.) sin evaluar primero si se migra a PostgreSQL.
- ❌ Usar yarn o npm como gestor de dependencias — usar siempre pnpm (Corepack).
- ❌ Depender de `@repo/shared-types` como alias de import hasta que el entrypoint de `packages/shared/package.json` esté alineado con la estructura real.
- ❌ Cambiar los catálogos del dominio de incidencias (canales, tipos, severidades, áreas, estados) sin modificar también el CONTEXT y el resto de reglas.

## Cómo verificar su cumplimiento

- `services/api/` debe existir con `pyproject.toml` (uv), `main.py` (FastAPI), y `database.py` (sqlite3).
- `uis/backoffice/` debe existir con `package.json` (pnpm), `vite.config.ts`, y código TypeScript sin imports a React/Vue/Svelte.
- `grep -r "react\|vue\|svelte" uis/backoffice/ --include="*.ts" --include="*.tsx" --include="*.json"` no debe devolver resultados (salvo dependencias en devDependencies si se añaden).
- No debe existir `package-lock.json` ni `yarn.lock` en el proyecto.