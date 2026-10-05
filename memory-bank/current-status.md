# Current Status — TrackFlow Incident Manager + Inventory Manager

## Incident Manager — Completado

- [x] Fase 1 — Reconocimiento del monorepo (`docs/incident-manager/reconnaissance.md`)
- [x] Fase 1 — Contexto funcional del Incident Manager documentado
- [x] Fase 2 — Reglas del proyecto creadas en `.agents/rules/`
- [x] Fase 2.1 — Reglas refinadas tras validación
- [x] Validación 5/5 simulaciones en `docs/incident-manager/rules-validation.md`
- [x] Decisiones técnicas cerradas en `memory-bank/tech-stack.md`
- [x] Plan de implementación creado en `memory-bank/implementation-plan.md`
- [x] Tipos compartidos del dominio (`packages/shared/types/incident.ts`)
- [x] Scaffold FastAPI + SQLite (`services/api/`)
- [x] Modelo Incident + audit log (tablas SQL: `incidents`, `incident_audit_log`, `metadata`)
- [x] 12+ seeds del CONTEXT (cobertura completa: canales, tipos, severidades, almacenes)
- [x] CRUD de incidencias (GET list, GET detail, POST create, PUT update)
- [x] Validación del ciclo de estados (grafo de transiciones + regla crítica)
- [x] Auditoría de status, assigned_to, responsible_area
- [x] Filtros (status, severity, responsible_area) con validación 422
- [x] Endpoint volumen abierto por severidad (`/api/incidents/open-by-severity`)
- [x] **FASE A** — Hardening backend:
  - [x] Fix regla crítica: critical permite resolved→closed
  - [x] Seeds auto-ejecutados en startup
  - [x] PUT con campos nullables (model_fields_set + auditoría)
  - [x] Validación de filtros inválidos → 422
  - [x] Limpieza de código muerto (seed, schemas)
  - [x] Tests backend — 67 tests (pytest, todos pasando)
- [x] **FASE B** — Frontend (Vite + TypeScript vanilla):
  - [x] Dashboard con tarjetas de severidad y tabla de incidents abiertos
  - [x] Listado con filtros (status, severity, responsible_area)
  - [x] Formulario de creación con selects del catálogo
  - [x] Detalle con timeline de auditoría y botones de transición
  - [x] Formulario de edición con PUT nullable
  - [x] Router cliente con history.pushState
  - [x] Capa API client con tipado y manejo de errores
  - [x] Proxy Vite /api → http://localhost:8000
  - [x] TypeScript strict mode, 0 errores de tipo
  - [x] Build producción OK (13 módulos, 17.55 kB JS)
- [x] **FASE C** — Verificación E2E:
  - [x] 52/52 assertions pasando (0 fallos)
  - [x] Dashboard, listado, filtros, CRUD, transiciones, auditoría, regla crítica, persistencia
  - [x] Documentación en `docs/incident-manager/verification.md`
  - [x] Tests backend: 67/67 pasando

## Inventory Manager — Completado (INV-T01 → INV-T20)

- [x] **INV-T01** — Tipos compartidos de inventario (`packages/shared/types/inventory.ts`)
- [x] **INV-T02** — Esquema/conexión SQLite (`services/api/database_inventory.py`)
- [x] **INV-T03** — Lógica de cálculo de stock derivado (`services/api/inventory_core.py`)
- [x] **INV-T04** — CRUD de items (endpoints en `services/api/routers/inventory.py`)
- [x] **INV-T05** — Creación atómica cosmetics + initial_lot
- [x] **INV-T06** — CRUD de lotes (POST/GET/GET expired)
- [x] **INV-T07** — Registro transaccional de movimientos (BEGIN IMMEDIATE)
- [x] **INV-T08** — Endpoint low-stock
- [x] **INV-T09** — Seeds idempotentes (`services/api/seed_inventory.py`)
- [x] **INV-T10** — Integración en FastAPI (`services/api/main.py`)
- [x] **INV-T11** — Tipos y API client frontend (`uis/backoffice/src/types.ts`, `api.ts`)
- [x] **INV-T12** — Navegación y routing (`uis/backoffice/src/main.ts`, `header.ts`)
- [x] **INV-T13** — Página de listado (`uis/backoffice/src/pages/inventory-list.ts`)
- [x] **INV-T14** — Alta/edición/baja (`inventory-create.ts`, `inventory-edit.ts`)
- [x] **INV-T15** — Detalle con lotes y movimientos (`inventory-detail.ts`)
- [x] **INV-T16** — Registro de movimientos desde UI (`inventory-movement.ts`)
- [x] **INV-T17** — Vista low-stock y dashboard (`inventory-low-stock.ts`, `inventory-dashboard.ts`)
- [x] **INV-T18** — Tests backend items/lots/stock/cosmetics (48 tests)
- [x] **INV-T19** — Tests backend movimientos/rechazos/seeds (29 tests)
- [x] **INV-T20** — Verificación final y trazabilidad

### Invariantes clave del Inventory Manager

- **Stock derivado**: Nunca columna `stock` en `items` — calculado desde `stock_movements`
- **Sin endpoint de stock**: No existe forma de editar stock directamente
- **Decimales**: `reorder_point REAL`, `quantity REAL` — soporta kg fraccionarios
- **Cosmetics atómico**: Item + lote inicial en misma transacción SQLite
- **Warehouse isolation**: Stock de `los_angeles` y `zaragoza` nunca se combinan
- **BEGIN IMMEDIATE**: Protege validación de stock contra race conditions
- **Seeds idempotentes**: Flag `seed_inventory_applied` en `inventory_metadata`

## Lo que NO se ha completado

- [ ] Pull Request (pendiente de instrucciones del usuario — "NO merge. NO PR todavía.")

## Estado del repositorio

- Rama: `feature/inventory-manager` (20 commits INV-T01→INV-T20)
- Incident Manager: 9 commits en `feature/incident-manager`
- Backend: FastAPI + SQLite — 144 tests pasando (77 inventory + 67 incident)
- Frontend: Vite + TypeScript vanilla — build OK, 0 errores TS
- Verificación: `specs/inventory-manager/verification.md` — INV-001..INV-055 con cobertura completa

## Próximo paso

Esperar instrucciones del usuario sobre Pull Request o nuevos desarrollos.