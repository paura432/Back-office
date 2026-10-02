# TrackFlow Inventory Manager — Tareas de Implementación

> Descomposición atómica del plan (`plan.md`) en tareas verificables.
> Cada tarea produce un commit. No modifica ni rompe el Incident Manager existente.

---

### INV-T01 — Tipos compartidos de inventario

**Criterios:** INV-001, INV-002, INV-003, INV-004, INV-005, INV-006, INV-007, INV-008, INV-009, INV-012, INV-013, INV-014, INV-015, INV-019, INV-020, INV-021, INV-022, INV-023, INV-024  
**Dependencias:** ninguna  
**Cambios:** `packages/shared/types/inventory.ts` — catálogos (warehouse, category, unit_of_measure, movement_type), interfaces (Item, Lot, StockMovement, ItemWithStock, ItemCreatePayload con `initial_lot?`, ItemUpdatePayload, MovementCreatePayload). Exportar desde `packages/shared/types/index.ts`.  
**Verificación:** `tsc --noEmit` pasa sin errores; los tipos se importan correctamente desde el frontend.  
**Commit esperado:** `feat(INV-T01): add shared inventory domain types`

---

### INV-T02 — Esquema/conexión SQLite de inventario

**Criterios:** INV-001 (CHECK warehouse), INV-005 (CHECK category), INV-006 (CHECK unit_of_measure), INV-007 (reorder_point REAL), INV-010 (UNIQUE client_name+sku+warehouse), INV-011 (UNIQUE refuerza identidad), INV-012 (FK item_id), INV-013, INV-014, INV-015, INV-021 (CHECK movement_type), INV-022 (quantity REAL), INV-024 (created_at TEXT), INV-025 (sin columna stock), INV-026 (sin columna stock editable)  
**Dependencias:** ninguna  
**Cambios:** `services/api/database_inventory.py` — `get_inventory_db_path()`, `get_inventory_connection()` (con PRAGMA foreign_keys=ON), `init_inventory_db()` que crea tablas `items`, `lots`, `stock_movements`, `inventory_metadata`.  
**Verificación:** `init_inventory_db()` crea las 4 tablas con columnas, constraints y tipos correctos (REAL para reorder_point y quantity). No existe columna `stock` en `items`.  
**Commit esperado:** `feat(INV-T02): add inventory database schema and connection`

---

### INV-T03 — Lógica única de cálculo de stock

**Criterios:** INV-025 (stock derivado), INV-026 (no editable), INV-027, INV-028, INV-029, INV-030 (inbound − outbound + adjustment), INV-031, INV-032, INV-033 (adjustment firmado), INV-041 (is_low_stock), INV-044 (listado con stock)  
**Dependencias:** INV-T02  
**Cambios:** `services/api/routers/inventory.py` o módulo `services/api/inventory_core.py` — funciones `get_stock(conn, item_id) -> float`, `get_items_with_stock(conn, warehouse=None) -> list[dict]`, `is_low_stock(item) -> bool`. La query SQL usa `CASE movement_type WHEN 'inbound' THEN quantity WHEN 'outbound' THEN -quantity WHEN 'adjustment' THEN quantity END`.  
**Verificación:** Insertar movimientos de prueba y verificar que `get_stock()` devuelve el valor correcto con decimales; `is_low_stock()` funciona con stock fraccionario.  
**Commit esperado:** `feat(INV-T03): implement derived stock calculation logic`

---

### INV-T04 — CRUD de items (listado, detalle, creación, edición, baja)

**Criterios:** INV-001 (warehouse), INV-002 (client_name), INV-003 (sku), INV-004 (name), INV-005 (category), INV-006 (unit_of_measure), INV-007 (reorder_point), INV-008 (created_at), INV-009 (updated_at), INV-010 (UNIQUE client_name+sku+warehouse), INV-011 (identidad multi-almacén), INV-042 (crear sin stock directo), INV-043 (PUT bloquea warehouse si hay movimientos), INV-044 (listado con stock derivado), INV-045 (DELETE rechaza si hay movimientos), INV-046 (DELETE sin movimientos → borra item + lotes en transacción)  
**Dependencias:** INV-T02, INV-T03  
**Cambios:** `services/api/routers/inventory.py` — endpoints:
- `POST /api/inventory/items` — alta general de artículo. Valida catálogos (warehouse, category, unit_of_measure), rechaza duplicado UNIQUE(client_name, sku, warehouse), nunca acepta stock directo (ni campo stock en payload). La creación de cosmetics con lote se delega a INV-T05.
- `GET /api/inventory/items` — listado con filtro warehouse opcional, stock derivado por artículo.
- `GET /api/inventory/items/{id}` — detalle con stock, lotes, últimos movimientos.
- `PUT /api/inventory/items/{id}` — edición; rechaza cambio de warehouse si el artículo tiene movimientos.
- `DELETE /api/inventory/items/{id}` — rechaza si tiene movimientos; si no, borra item + lotes en una transacción.  
**Verificación:** POST con datos válidos → 201 sin stock directo; POST duplicado (client+sku+warehouse) → 422; POST con catálogo inválido → 422; GET items devuelve stock calculado; PUT con warehouse diferente → 422 si tiene movimientos; DELETE sin movimientos → 200 y item + lotes eliminados; DELETE con movimientos → 422.  
**Commit esperado:** `feat(INV-T04): implement items CRUD endpoints`

---

### INV-T05 — Creación atómica de cosmetics + initial_lot (extensión del POST)

**Criterios:** INV-016 (cosmetics requiere lote al alta), INV-017 (fashion/electronics sin lote es válido), INV-018 (lote asociado a item existente), INV-042 (alta sin stock directo)  
**Dependencias:** INV-T04 (extiende el `POST /api/inventory/items` implementado en T04)  
**Cambios:** En `POST /api/inventory/items` — añadir lógica específica: si `category=cosmetics`, validar que `initial_lot` está presente con `lot_code`, `expiry_date`, `received_at`; crear item + lote en la misma transacción SQLite; si `category=fashion|electronics`, `initial_lot` es opcional. `initial_lot` no persiste como campo del Item.  
**Verificación:** POST cosmetics sin initial_lot → 422; POST cosmetics con initial_lot válido → 201 y lote creado; POST fashion/electronics sin initial_lot → 201; POST con initial_lot inválido (falta campo) → 422.  
**Commit esperado:** `feat(INV-T05): implement atomic cosmetics creation with initial_lot`

---

### INV-T06 — CRUD/creación de lotes

**Criterios:** INV-012 (item_id), INV-013 (lot_code), INV-014 (expiry_date), INV-015 (received_at), INV-018 (rechazar item_id inexistente)  
**Dependencias:** INV-T02, INV-T04  
**Cambios:** `services/api/routers/inventory.py` — endpoints `POST /api/inventory/items/{item_id}/lots` (validar item existente, crear lote), `GET /api/inventory/items/{item_id}/lots` (listar lotes de un artículo), `GET /api/inventory/lots/expired` (lotes con expiry_date < now()).  
**Verificación:** POST lot con item_id inexistente → 422; GET lots devuelve lista; GET expired devuelve solo lotes vencidos.  
**Commit esperado:** `feat(INV-T06): implement lot creation and listing endpoints`

---

### INV-T07 — Registro transaccional de movimientos (inbound, outbound, adjustment)

**Criterios:** INV-019 (item_id), INV-020 (lot_id nullable), INV-021 (movement_type), INV-022 (quantity REAL), INV-023 (adjustment requiere reason), INV-024 (created_at), INV-030 (cálculo), INV-031 (inbound incrementa), INV-032 (outbound resta), INV-033 (adjustment firmado), INV-034 (outbound que deje stock < 0 → rechazo), INV-035 (outbound item inexistente), INV-036 (adjustment item inexistente), INV-037 (lot_id no nulo inexistente), INV-038 (lot_id de otro artículo), INV-039 (cosmetics requiere lot_id), INV-040 (stock por almacén separado)  
**Dependencias:** INV-T02, INV-T03, INV-T04, INV-T06  
**Cambios:** `services/api/routers/inventory.py` — endpoint `POST /api/inventory/items/{item_id}/movements`. Validación transaccional completa (plan.md §4): (1) item existe, (2) lot_id existe y pertenece al item si no nulo, (3) outbound no deja stock < 0, (4) cosmetics requiere lot_id, (5) adjustment requiere reason. Usa `BEGIN IMMEDIATE` para evitar race conditions en outbound (plan.md §4 — Concurrencia). Inserta movimiento y hace COMMIT.  
**Verificación:** Movimiento válido → 201; outbound que agota stock → ok; outbound que excede stock → 422; adjustment sin reason → 422; movement con lot_id inexistente → 422; cosmetics sin lot_id → 422; stock por almacén no se compensa.  
**Commit esperado:** `feat(INV-T07): implement transactional movement registration with all validations`

---

### INV-T08 — Endpoint low-stock

**Criterios:** INV-041 (señal visible cuando stock ≤ reorder_point)  
**Dependencias:** INV-T03, INV-T04  
**Cambios:** `services/api/routers/inventory.py` — endpoint `GET /api/inventory/low-stock`. Devuelve artículos donde `get_stock() <= reorder_point`, agrupados por almacén. Incluye `warehouse`, `client_name`, `sku`, `name`, `stock`, `reorder_point`.  
**Verificación:** GET low-stock devuelve solo artículos con stock ≤ reorder_point; agrupados por almacén.  
**Commit esperado:** `feat(INV-T08): implement low-stock endpoint`

---

### INV-T09 — Seeds idempotentes

**Criterios:** INV-047 (≥15 items), INV-048 (ambos almacenes), INV-049 (≥3 clientes), INV-050 (3 categorías), INV-051 (≥3 cosmetics con lote), INV-052 (≥1 lote expirado), INV-053 (≥2 low stock), INV-054 (inbound, outbound, adjustment), INV-055 (≥1 return_restock)  
**Dependencias:** INV-T02, INV-T05, INV-T06, INV-T07  
**Cambios:** `services/api/seed_inventory.py` — función `run_inventory_seed()` que consulta `inventory_metadata` (tabla propia, DB independiente). Si `seed_inventory_applied` no existe, inserta 15+ items con: 2 almacenes, 3+ clientes, 3 categorías (3+ cosmetics con lote), 1+ lote expirado, movimientos inbound/outbound/adjustment (1+ return_restock), 2+ artículos low stock. Luego inserta flag en `inventory_metadata`. Si la flag ya existe, omite (idempotente).  
**Verificación:** Primera ejecución tras DB vacía → seeds insertados y flag registrada. Segunda ejecución → sin cambios. Contar items (≥15), cosmetics con lote (≥3), lotes expirados (≥1), low stock (≥2), tipos de movimiento (3), return_restock (≥1).  
**Commit esperado:** `feat(INV-T09): implement idempotent inventory seeds`

---

### INV-T10 — Integración Inventory en FastAPI existente

**Criterios:** (compatibilidad — no abre nuevos INV)  
**Dependencias:** INV-T04, INV-T05, INV-T06, INV-T07, INV-T08, INV-T09  
**Cambios:** `services/api/main.py` — importar router de inventario y montarlo como `app.include_router(inventory_router)`. Importar `run_inventory_seed()` y ejecutarlo en el evento `startup()`. No modificar ni el router de incidencias ni la DB del Incident Manager.  
**Verificación:** La app arranca sin errores; `/api/incidents/` sigue funcionando; `/api/inventory/items` responde; `/health` sigue en pie.  
**Commit esperado:** `feat(INV-T10): integrate inventory module into existing FastAPI app`

---

### INV-T11 — Cliente API frontend (con tipos importados desde shared)

**Criterios:** (soporte — no abre nuevos INV)  
**Dependencias:** INV-T01, INV-T10  
**Cambios:** `uis/backoffice/src/types.ts` — NO replicar tipos de dominio de inventario. Importarlos desde `packages/shared/types/inventory.ts` con ruta relativa (ej. `import type { Item, Lot, StockMovement, ItemWithStock, ItemCreatePayload, ItemUpdatePayload, MovementCreatePayload, Warehouse } from '../../../../packages/shared/types/inventory'`). Únicamente declarar aquí tipos locales de presentación que no dupliquen el dominio (ej. `ItemTableRow`, `LowStockAlert`).  
`uis/backoffice/src/api.ts` — añadir métodos: `listItems(warehouse?)`, `getItem(id)`, `createItem(payload)`, `updateItem(id, payload)`, `deleteItem(id)`, `createLot(itemId, payload)`, `listLots(itemId)`, `createMovement(itemId, payload)`, `listMovements(itemId)`, `getLowStock()`.  
**Verificación:** `tsc --noEmit` pasa sin errores; los imports proceden de `packages/shared/types/`; no hay interfaces de dominio duplicadas en `uis/backoffice/src/types.ts`; los métodos API funcionan.  
**Commit esperado:** `feat(INV-T11): add inventory types and API client to frontend`

---

### INV-T12 — Navegación/routing frontend

**Criterios:** (soporte — no abre nuevos INV)  
**Dependencias:** INV-T11  
**Cambios:** `uis/backoffice/src/main.ts` — añadir rutas para `/inventory`, `/inventory/items`, `/inventory/items/detail`, `/inventory/items/create`, `/inventory/items/edit`, `/inventory/low-stock` que cargan las páginas de inventario. `uis/backoffice/src/components/header.ts` — añadir enlaces «Inventory» y «Low Stock» al nav, con indicador visual si hay artículos low-stock. No romper rutas existentes del Incident Manager.  
**Verificación:** Navegar a `/inventory` carga la página de inventario; los enlaces del nav están visibles; las rutas del Incident Manager (`/dashboard`, `/list`, `/create`) siguen funcionando.  
**Commit esperado:** `feat(INV-T12): add inventory navigation and routing`

---

### INV-T13 — Listado de inventario

**Criterios:** INV-044 (listado con stock derivado, por almacén), INV-041 (columna/badge low-stock)  
**Dependencias:** INV-T11, INV-T12  
**Cambios:** `uis/backoffice/src/pages/inventory-list.ts` — tabla con columnas: warehouse, client_name, sku, name, category, stock (derivado), reorder_point, is_low_stock (badge). Filtro por warehouse. Botón «+ New Item».  
**Verificación:** La página carga items con stock calculado; el filtro por warehouse funciona; los items low-stock muestran badge.  
**Commit esperado:** `feat(INV-T13): implement inventory list page`

---

### INV-T14 — Alta/edición/baja de item

**Criterios:** INV-016 (cosmetics requiere lote al alta), INV-017 (fashion/electronics sin lote), INV-042 (alta sin stock directo), INV-043 (edición bloquea warehouse si hay movimientos), INV-045 (baja rechaza si hay movimientos), INV-046 (baja sin movimientos → ok)  
**Dependencias:** INV-T11, INV-T12, INV-T13  
**Cambios:** `uis/backoffice/src/pages/inventory-create.ts` — formulario con selects (warehouse, category, unit_of_measure). Si category=cosmetics, mostrar campos de `initial_lot` (lot_code, expiry_date, received_at) como obligatorios.  
`uis/backoffice/src/pages/inventory-edit.ts` — formulario precargado; warehouse bloqueado (disabled) si el item tiene movimientos.  
Botón de eliminar en detalle/edición; si hay movimientos, mostrar mensaje de rechazo.  
**Verificación:** Alta de cosmetics sin lote → error visible. Alta de fashion sin lote → ok. Edición de item con movimientos no permite cambiar warehouse. Eliminar item sin movimientos → ok. Eliminar item con movimientos → error visible.  
**Commit esperado:** `feat(INV-T14): implement item create, edit, and delete pages`

---

### INV-T15 — Detalle con lotes y movimientos

**Criterios:** INV-002–009 (campos del artículo), INV-012–015 (información de lotes), INV-019–024 (información de movimientos)  
**Dependencias:** INV-T11, INV-T12  
**Cambios:** `uis/backoffice/src/pages/inventory-detail.ts` — tarjeta con datos del artículo y stock derivado. Sección de lotes (tabla con lot_code, expiry_date, received_at). Sección de movimientos (tabla con movement_type, quantity, reason, created_at). Botones para crear lote y registrar movimiento.  
**Verificación:** La página carga y muestra todos los campos del artículo, lotes y movimientos.  
**Commit esperado:** `feat(INV-T15): implement item detail page with lots and movements`

---

### INV-T16 — Registro de movimientos desde UI

**Criterios:** INV-019–024 (campos del movimiento), INV-034 (no outbound si stock < 0)  
**Dependencias:** INV-T11, INV-T12, INV-T15  
**Cambios:** Formulario inline o modal en `inventory-detail.ts` (o página separada `inventory-movement.ts`) para registrar inbound, outbound, adjustment. Select de movement_type. Campo quantity (number, step=any para decimales). Campo lot_id (select de lotes disponibles del artículo, opcional). Campo reason (obligatorio si adjustment). Validación: si outbound excede stock, mostrar error del backend.  
**Verificación:** Registrar inbound → stock se incrementa. Registrar outbound → stock se reduce. Outbound que excede stock → error. Adjustment con reason → stock se ajusta.  
**Commit esperado:** `feat(INV-T16): implement movement registration UI`

---

### INV-T17 — Vista/señal low-stock

**Criterios:** INV-041 (señal visible por artículo y almacén)  
**Dependencias:** INV-T11, INV-T12  
**Cambios:** `uis/backoffice/src/pages/inventory-low-stock.ts` — tabla de artículos con stock ≤ reorder_point, agrupados por almacén. Badge/icono rojo de alerta.  
`uis/backoffice/src/pages/inventory-dashboard.ts` — tarjeta de resumen con total de artículos low-stock y enlace a la vista detallada.  
Indicador en el nav (header.ts) si hay artículos low-stock.  
**Verificación:** La vista low-stock muestra solo artículos con stock ≤ reorder_point. El dashboard muestra el contador. El nav tiene indicador.  
**Commit esperado:** `feat(INV-T17): implement low-stock view and dashboard`

---

### INV-T18 — Tests backend por criterios EARS (items, lots, stock, cosmetics)

**Criterios:** INV-001, INV-002, INV-003, INV-004, INV-005, INV-006, INV-007, INV-008, INV-009, INV-010, INV-011, INV-012, INV-013, INV-014, INV-015, INV-016, INV-017, INV-018, INV-025, INV-026, INV-027, INV-028, INV-029, INV-030, INV-031, INV-032, INV-033, INV-041, INV-042, INV-043, INV-044, INV-045, INV-046  
**Dependencias:** INV-T02, INV-T03, INV-T04, INV-T05, INV-T06, INV-T08  
**Cambios:** `services/api/tests/test_inventory.py` — fixtures con DB temporal (`INVENTORY_DB_PATH`) y TestClient. Tests unitarios e integración para: warehouse válido/inválido, campos del item, UNIQUE client+sku+warehouse, identidad multi-almacén, creación de lotes, cosmetics obliga lote, fashion/electronics sin lote, lote con item inexistente, stock derivado (inbound suma, outbound resta, adjustment firmado), no existe columna stock editable, low-stock endpoint, CRUD (alta sin stock, PUT bloquea warehouse, DELETE con/sin movimientos, listado con stock).  
**Verificación:** `pytest services/api/tests/test_inventory.py -v` — todos los tests pasan.  
**Commit esperado:** `test(INV-T18): add backend tests for items, lots, stock, and cosmetics`

---

### INV-T19 — Tests backend (movimientos, rechazos, semilla)

**Criterios:** INV-019, INV-020, INV-021, INV-022, INV-023, INV-024, INV-034, INV-035, INV-036, INV-037, INV-038, INV-039, INV-040, INV-047, INV-048, INV-049, INV-050, INV-051, INV-052, INV-053, INV-054, INV-055  
**Dependencias:** INV-T07, INV-T08, INV-T09  
**Cambios:** Tests adicionales en `services/api/tests/test_inventory.py` para: movimiento con campos válidos, adjustment sin reason, outbound que deja stock < 0, outbound/adjustment con item inexistente, lot_id inexistente, lot_id de otro artículo, cosmetics sin lot_id, stock separado por almacén, y semilla (≥15 items, 2 almacenes, 3+ clientes, 3 categorías, 3+ cosmetics con lote, lote expirado, 2+ low stock, inbound/outbound/adjustment, return_restock).  
**Verificación:** `pytest services/api/tests/test_inventory.py -v` — todos los tests pasan (incluyendo T18).  
**Commit esperado:** `test(INV-T19): add backend tests for movements, rejections, and seeds`

---

### INV-T20 — Verificación final y trazabilidad (sin código nuevo)

**Criterios:** todos INV-001–055 (cobertura completa E2E)  
**Dependencias:** todas INV-T01–T19  
**Cambios:** Ningún archivo de código funcional. Actividades:
1. **Tests existentes** — ejecutar `pytest services/api/tests/test_inventory.py -v` y confirmar que todos los tests (T18 + T19) pasan.
2. **Build / typecheck** — ejecutar `tsc --noEmit` en el frontend y confirmar que no hay errores de tipos.
3. **Trazabilidad INV → test → commit** — comprobar que cada INV-001–055 tiene al menos un test que lo ejercita, y que cada tarea INV-T01–T19 tiene su commit.
4. **Documento de verificación** — generar o actualizar `specs/inventory-manager/verification.md` enumerando cada criterio, su test asociado y el resultado de la ejecución.
5. **Compatibilidad** — verificar que el Incident Manager sigue funcionando (health check, CRUD de incidencias).  
**Verificación:** Cada INV-001–055 tiene una aserción positiva documentada. `pytest` pasa. `tsc --noEmit` pasa. El Incident Manager pasa su propia verificación. No se ha añadido código funcional nuevo.  
**Commit esperado:** `test(INV-T20): verify complete inventory manager implementation`

---

## Trazabilidad de tareas

| Task | Criterios INV | Dependencias | Verificación | Commit esperado |
|---|---|---|---|---|
| INV-T01 | 001–009, 012–015, 019–024 | ninguna | `tsc --noEmit` sin errores | `feat(INV-T01): add shared inventory domain types` |
| INV-T02 | 001, 005–007, 010–015, 021–022, 024–026 | ninguna | Tablas creadas con columnas y constraints correctos | `feat(INV-T02): add inventory database schema and connection` |
| INV-T03 | 025–033, 041, 044 | INV-T02 | `get_stock()` devuelve float correcto con decimales | `feat(INV-T03): implement derived stock calculation logic` |
| INV-T04 | 001–011, 042–046 | INV-T02, INV-T03 | POST con CRUD completo; PUT bloquea warehouse; DELETE gestiona lotes | `feat(INV-T04): implement items CRUD endpoints` |
| INV-T05 | 016–018, 042 | INV-T04 | POST cosmetics sin initial_lot → 422; con initial_lot → 201 + lote | `feat(INV-T05): implement atomic cosmetics creation with initial_lot` |
| INV-T06 | 012–015, 018 | INV-T02, INV-T04 | POST/GET lots funcional; item_id inexistente → 422 | `feat(INV-T06): implement lot creation and listing endpoints` |
| INV-T07 | 019–024, 030–040 | INV-T02, INV-T03, INV-T04, INV-T06 | Movimiento válido → 201; outbound que excede → 422; BEGIN IMMEDIATE | `feat(INV-T07): implement transactional movement registration with all validations` |
| INV-T08 | 041 | INV-T03, INV-T04 | GET low-stock devuelve items con stock ≤ reorder_point | `feat(INV-T08): implement low-stock endpoint` |
| INV-T09 | 047–055 | INV-T02, INV-T05, INV-T06, INV-T07 | Seeds idempotentes con cobertura completa | `feat(INV-T09): implement idempotent inventory seeds` |
| INV-T10 | (compatibilidad) | INV-T04–T09 | App arranca; Incident Manager funciona; Inventory responde | `feat(INV-T10): integrate inventory module into existing FastAPI app` |
| INV-T11 | (soporte) | INV-T01, INV-T10 | `tsc --noEmit` pasa; imports desde `packages/shared/types/`; sin tipos de dominio duplicados | `feat(INV-T11): add inventory types and API client to frontend` |
| INV-T12 | (soporte) | INV-T11 | Navegación funcional; rutas Incident Manager intactas | `feat(INV-T12): add inventory navigation and routing` |
| INV-T13 | 041, 044 | INV-T11, INV-T12 | Tabla con stock derivado; filtro por warehouse; badge low-stock | `feat(INV-T13): implement inventory list page` |
| INV-T14 | 016, 017, 042, 043, 045, 046 | INV-T11, INV-T12, INV-T13 | Alta cosmetics sin lote → error; edición bloquea warehouse; DELETE condicional | `feat(INV-T14): implement item create, edit, and delete pages` |
| INV-T15 | 002–009, 012–015, 019–024 | INV-T11, INV-T12 | Detalle muestra item, lotes y movimientos | `feat(INV-T15): implement item detail page with lots and movements` |
| INV-T16 | 019–024, 034 | INV-T11, INV-T12, INV-T15 | Formulario de movimiento; outbound que excede → error | `feat(INV-T16): implement movement registration UI` |
| INV-T17 | 041 | INV-T11, INV-T12 | Vista low-stock; dashboard; indicador en nav | `feat(INV-T17): implement low-stock view and dashboard` |
| INV-T18 | 001–018, 025–033, 041–046 | INV-T02–T06, INV-T08 | pytest pasa tests de items, lots, stock, cosmetics, CRUD | `test(INV-T18): add backend tests for items, lots, stock, and cosmetics` |
| INV-T19 | 019–024, 034–040, 047–055 | INV-T07, INV-T08, INV-T09 | pytest pasa tests de movimientos, rechazos y semilla | `test(INV-T19): add backend tests for movements, rejections, and seeds` |
| INV-T20 | 001–055 | todas | pytest + tsc pasan; trazabilidad INV→test→commit documentada; sin código nuevo | `test(INV-T20): verify complete inventory manager implementation` |