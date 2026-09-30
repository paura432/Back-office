# Implementation Plan — TrackFlow Incident Manager

> Plan versionado ANTES del código. Cada paso debe completarse antes de pasar al siguiente.

---

## Paso 1 — Tipos compartidos del dominio

**Archivo:** `packages/shared/types/incident.ts`

Crear los tipos TypeScript del dominio de incidencias usando los catálogos cerrados del CONTEXT:

- Enums para: `Channel`, `IncidentType`, `Severity`, `ResponsibleArea`, `IncidentStatus`
- Interface `Incident` con todos los campos mínimos del modelo
- Constantes array con todos los valores de catálogo (para validación)

**No tocar** `packages/shared/package.json`.

---

## Paso 2 — Scaffold FastAPI + SQLite

**Crear:** `services/api/` con estructura mínima:

- `services/api/pyproject.toml` (uv)
- `services/api/main.py` — FastAPI app
- `services/api/database.py` — conexión SQLite (`sqlite3`)
- `services/api/seed.py` — script de seed

**No usar ORM**, solo `sqlite3` estándar.

---

## Paso 3 — Modelo Incident + audit log

**Archivos:** `services/api/models/incident.py`, `services/api/models/audit_log.py`

- Tabla `incidents` con todos los campos del modelo
- Tabla `incident_audit_log` con: `id`, `incident_id`, `field_changed`, `old_value`, `new_value`, `changed_by`, `changed_at`
- Funciones `init_db()` que crean ambas tablas al arrancar

---

## Paso 4 — 12+ seeds del CONTEXT

**Archivo:** `services/api/seed.py`

12+ incidencias que cubran:
- Las 4 severidades
- Ambos almacenes (`los_angeles`, `zaragoza`)
- Al menos 4 canales distintos
- Al menos 1 incidencia `reopened`
- Al menos 1 incidencia con `client_name = null`

---

## Paso 5 — CRUD de incidencias

**Archivo:** `services/api/routers/incidents.py`

Endpoints:
- `GET /incidents` — listar (con filtros opcionales)
- `GET /incidents/{id}` — detalle
- `POST /incidents` — crear
- `PUT /incidents/{id}` — actualizar campos permitidos
- `PATCH /incidents/{id}/status` — transición de estado (con validación)

---

## Paso 6 — Validación del ciclo de estados

En el endpoint `PATCH /incidents/{id}/status`:

- Mapa de transiciones válidas:
  - `open → assigned`
  - `assigned → in_progress`
  - `in_progress → resolved`
  - `resolved → closed`
  - `resolved → reopened`
- Rechazar cualquier otra transición con 422
- Regla especial: `critical` no puede saltar de `in_progress` (o cualquier estado anterior) directamente a `closed` sin pasar por `resolved`

---

## Paso 7 — Auditoría

En cada cambio de `status`, `assigned_to` o `responsible_area`:

1. Detectar el campo cambiado (comparar valor anterior vs nuevo)
2. Insertar registro en `incident_audit_log` con: `field_changed`, `old_value`, `new_value`, `changed_by`, `changed_at`

---

## Paso 8 — Filtros

Endpoint `GET /incidents` acepta query params:
- `status` (opcional)
- `severity` (opcional)
- `responsible_area` (opcional)

---

## Paso 9 — Endpoint volumen abierto por severidad

`GET /incidents/open-by-severity`

Devuelve conteo de incidencias abiertas (no `resolved` ni `closed`) agrupadas por severidad.

---

## Paso 10 — UI

**Crear:** `uis/backoffice/` con Vite + TypeScript vanilla:

- `dashboard/` — resumen: tarjetas con totales, tabla de últimas, gráfico open-by-severity
- `list/` — listado completo con filtros (status, severity, responsible_area)
- `create/` — formulario de alta
- `edit/` — edición de incidencia
- `detail/` — detalle + historial de auditoría
- `history/` — timeline de cambios

Proxy Vite: `/api` → `http://localhost:8000`

---

## Paso 11 — Tests backend y validación frontend

- pytest para backend: test de creación, transiciones, validación de catálogos, auditoría, regla critical, filtros
- Validación manual de frontend: navegación, CRUD, transiciones, visualización de historial

---

## Paso 12 — Actualización final del memory-bank

Actualizar `current-status.md` con el estado post-implementación.

---

## Paso 13 — Pull Request

Crear PR con resumen de cambios y referencias a reglas aplicadas.