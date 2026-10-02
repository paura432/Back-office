# TrackFlow Inventory Manager — Plan de Implementación

> Plan versionado ANTES del código. Cada paso debe completarse antes de pasar al siguiente.
> Basado en `specs/inventory-manager/spec.md`. No modifica ni rompe el Incident Manager existente.

---

## Stack

| Capa | Tecnología | Gestor |
|---|---|---|
| Backend | FastAPI + SQLite (`sqlite3`) | uv |
| Frontend | Vite + TypeScript vanilla | pnpm (Corepack) |
| Tipos compartidos TS | `packages/shared/types/` (ruta relativa) | — |
| Tests backend | pytest | uv |

No se introducen nuevas dependencias ni frameworks.

---

## 1. Tipos compartidos — `packages/shared/types/inventory.ts`

Crear catálogos e interfaces TypeScript para el dominio de inventario.

### Catálogos cerrados

| Campo | Valores |
|---|---|
| `warehouse` | `los_angeles` \| `zaragoza` |
| `category` | `fashion` \| `electronics` \| `cosmetics` |
| `unit_of_measure` | `unit` \| `box` \| `kg` |
| `movement_type` | `inbound` \| `outbound` \| `adjustment` |

### Interfaces

- `Item` — todos los campos del artículos (sin columna stock)
- `Lot` — lote vinculado a un artículo
- `StockMovement` — movimiento de inventario
- `ItemWithStock` — Item + `stock: number` + `is_low_stock: boolean`
- `ItemCreatePayload`, `ItemUpdatePayload`
- `MovementCreatePayload`

Se exportan desde `packages/shared/types/index.ts`.

---

## 2. Backend — nueva base de datos (SQLite)

Usar una base de datos separada del Incident Manager, definida por la variable de entorno `INVENTORY_DB_PATH` (por defecto `inventory.db`).

### 2.1 Tabla `items`

```sql
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    warehouse TEXT NOT NULL CHECK (warehouse IN ('los_angeles', 'zaragoza')),
    client_name TEXT NOT NULL,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('fashion', 'electronics', 'cosmetics')),
    unit_of_measure TEXT NOT NULL CHECK (unit_of_measure IN ('unit', 'box', 'kg')),
    reorder_point INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (client_name, sku, warehouse)
);
```

### 2.2 Tabla `lots`

```sql
CREATE TABLE IF NOT EXISTS lots (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(id),
    lot_code TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    received_at TEXT NOT NULL
);
```

### 2.3 Tabla `stock_movements`

```sql
CREATE TABLE IF NOT EXISTS stock_movements (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(id),
    lot_id TEXT REFERENCES lots(id),
    movement_type TEXT NOT NULL CHECK (movement_type IN ('inbound', 'outbound', 'adjustment')),
    quantity INTEGER NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);
```

---

## 3. Lógica de stock — sin columna stock

### 3.1 Función `get_stock(conn, item_id) -> int`

```sql
SELECT COALESCE(SUM(
    CASE movement_type
        WHEN 'inbound' THEN quantity
        WHEN 'outbound' THEN -quantity
        WHEN 'adjustment' THEN quantity   -- quantity ya es firmado (+/-)
    END
), 0) AS stock
FROM stock_movements
WHERE item_id = ?;
```

- `inbound`: quantity positiva → incrementa.
- `outbound`: quantity positiva → se convierte en negativa → decrementa.
- `adjustment`: quantity es firmada (+ incrementa, - decrementa). **No hay ambigüedad**: adjustment usa el signo directamente.

### 3.2 Función `get_items_with_stock(conn, warehouse=None)`

Devuelve la lista de artículos con stock derivado y `is_low_stock` calculado (stock ≤ reorder_point).

### 3.3 `is_low_stock(item) -> bool`

`return get_stock(conn, item_id) <= item.reorder_point`

---

## 4. Validación de movimientos — transaccional

Cada creación de movimiento se ejecuta dentro de una transacción SQLite:

1. Verificar que `item_id` existe → si no, rechazar (INV-035, INV-036).
2. Si `lot_id` no es nulo:
   - Verificar que el lote existe → si no, rechazar (INV-037).
   - Verificar que el lote pertenece al mismo `item_id` → si no, rechazar (INV-038).
3. Si `movement_type` == `outbound`:
   - Calcular stock actual vía `get_stock()`.
   - Si `stock - quantity < 0` → rechazar (INV-034).
4. Si `category` del item es `cosmetics` y `lot_id` es nulo → rechazar (INV-039). *(El requerimiento de lote al crear el artículo ya garantiza que cosmetics tenga lote; esta validación protege movimientos.)*
5. Si `movement_type` == `adjustment` y `reason` es nulo o vacío → rechazar (INV-023).
6. Insertar el movimiento.
7. `COMMIT`.

---

## 5. Endpoints backend

Router: `/api/inventory/` en `services/api/routers/inventory.py`

### Items

| Endpoint | Método | Descripción | INV cubiertos |
|---|---|---|---|
| `/api/inventory/items` | GET | Listar artículos (con stock derivado, `is_low_stock`, filtro opcional por warehouse) | INV-044 |
| `/api/inventory/items/{id}` | GET | Detalle de artículo (con stock derivado, `is_low_stock`, lotes, últimos movimientos) | INV-002–009 |
| `/api/inventory/items` | POST | Crear artículo (UNIQUE client_name + sku + warehouse) | INV-010, INV-011, INV-042 |
| `/api/inventory/items/{id}` | PUT | Editar artículo (rechazar cambio de warehouse si tiene movimientos) | INV-009, INV-043 |
| `/api/inventory/items/{id}` | DELETE | Borrar artículo (rechazar si tiene movimientos) | INV-045, INV-046 |

### Lotes

| Endpoint | Método | Descripción | INV cubiertos |
|---|---|---|---|
| `/api/inventory/items/{item_id}/lots` | POST | Crear lote para un artículo | INV-012–015, INV-016, INV-017, INV-018 |
| `/api/inventory/items/{item_id}/lots` | GET | Listar lotes de un artículo | — |
| `/api/inventory/lots/expired` | GET | Listar lotes expirados | — |

### Movimientos

| Endpoint | Método | Descripción | INV cubiertos |
|---|---|---|---|
| `/api/inventory/items/{item_id}/movements` | POST | Crear movimiento (toda la validación transaccional) | INV-019–024, INV-030–039 |
| `/api/inventory/items/{item_id}/movements` | GET | Listar movimientos de un artículo | — |

### Low stock

| Endpoint | Método | Descripción | INV cubiertos |
|---|---|---|---|
| `/api/inventory/low-stock` | GET | Listar artículos con stock ≤ reorder_point, agrupados por almacén | INV-041 |

No existe endpoint para editar stock directamente (INV-027). No existe formulario de edición de stock (INV-028). No existe campo stock en el modelo de artículo (INV-026, INV-029).

---

## 6. Frontend — nuevas páginas en `uis/backoffice/`

### 6.1 Navegación

Añadir enlaces al nav: **Inventory**, **Low Stock** (con indicador visual si hay artículos con stock bajo).

### 6.2 Tipos — `src/types.ts`

Añadir catálogos e interfaces del dominio de inventario (importados o copiados de `packages/shared/types/inventory.ts` mientras el entrypoint del paquete compartido no esté resuelto).

### 6.3 API client — `src/api.ts`

Añadir métodos:

- `listItems(warehouse?)`
- `getItem(id)`
- `createItem(payload)`
- `updateItem(id, payload)`
- `deleteItem(id)`
- `createLot(itemId, payload)`
- `listLots(itemId)`
- `createMovement(itemId, payload)`
- `listMovements(itemId)`
- `getLowStock()`

### 6.4 Páginas

| Página | Ruta | Archivo | Contenido |
|---|---|---|---|
| Inventory Dashboard | `/inventory` | `src/pages/inventory-dashboard.ts` | Resumen: total items por almacén, low-stock alerts, últimos movimientos |
| Item List | `/inventory/items` | `src/pages/inventory-list.ts` | Tabla con filtro por almacén, columna stock derivado, badge low-stock |
| Item Detail | `/inventory/items/detail` | `src/pages/inventory-detail.ts` | Información del artículo, stock, lotes, historial de movimientos |
| Create Item | `/inventory/items/create` | `src/pages/inventory-create.ts` | Formulario con selects para warehouse, category, unit_of_measure. Si category=cosmetics, campo lotes obligatorio |
| Edit Item | `/inventory/items/edit` | `src/pages/inventory-edit.ts` | Edición, bloquea warehouse si tiene movimientos |
| Low Stock | `/inventory/low-stock` | `src/pages/inventory-low-stock.ts` | Artículos con stock ≤ reorder_point, agrupados por almacén |

### 6.5 Router (`src/main.ts`)

Añadir rutas para `/inventory*` que cargan las nuevas páginas. No romper las rutas existentes del Incident Manager.

---

## 7. Seeds

Archivo: `services/api/seed_inventory.py`

Ejecutado en startup (igual que Incident Manager) si la flag `seed_inventory_applied` no existe en tabla `metadata`.

| Requisito | Cobertura mínima | INV |
|---|---|---|
| ≥15 items | 15+ artículos | INV-047 |
| Ambos almacenes | Algunos en `los_angeles`, otros en `zaragoza` | INV-048 |
| ≥3 clientes | `StyleMart`, `MundoModa`, `QuickShip`, etc. | INV-049 |
| 3 categorías | `fashion`, `electronics`, `cosmetics` | INV-050 |
| ≥3 cosmetics con lote | 3+ artículos `cosmetics`, cada uno con ≥1 lote | INV-051 |
| ≥1 lote expirado | Un lote con `expiry_date` anterior a `now()` | INV-052 |
| ≥2 low stock | Stock derivado ≤ reorder_point | INV-053 |
| inbound, outbound, adjustment | Al menos uno de cada tipo | INV-054 |
| ≥1 return_restock | Adjustment con reason = `return_restock` | INV-055 |

---

## 8. Tests — pytest

Archivo: `services/api/tests/test_inventory.py`

### 8.1 Fixtures

- Base de datos temporal aislada (`INVENTORY_DB_PATH`).
- `client`: TestClient con la app de inventario.
- `sample_item`: crea un item de prueba.
- `sample_lot`: crea un lote de prueba.
- `sample_movement(type, quantity)`: crea un movimiento de prueba.

### 8.2 Estrategia de mapeo INV → tests

| INV | Test | Tipo |
|---|---|---|
| INV-001 | Crear item con warehouse válido / inválido | unit |
| INV-002 – INV-009 | GET item detail expone todos los campos | unit |
| INV-010 | POST item con duplicado client+sku+warehouse → 422 | unit |
| INV-011 | Mismo sku + distinto client_name son distintos; mismo client+sku en distinto warehouse son distintos | unit |
| INV-012 – INV-015 | Crear lote con campos correctos | unit |
| INV-016 | Crear item cosmetics sin lote → 422 | unit |
| INV-017 | Crear item fashion/electronics sin lote → ok | unit |
| INV-018 | Crear lote con item_id inexistente → 422 | unit |
| INV-019 – INV-024 | Crear movimiento con campos correctos | unit |
| INV-023 | Crear adjustment sin reason → 422 | unit |
| INV-025 – INV-029 | Verificar que GET item no devuelve columna stock; que no hay endpoint de stock directo | integration |
| INV-030 – INV-033 | Calcular stock tras inbound, outbound, adjustment (positivo y negativo) | integration |
| INV-034 | Outbound que dejaría stock < 0 → 422 | unit |
| INV-035 | Outbound con item_id inexistente → 422 | unit |
| INV-036 | Adjustment con item_id inexistente → 422 | unit |
| INV-037 | Movimiento con lot_id inexistente → 422 | unit |
| INV-038 | Movimiento con lot_id de otro artículo → 422 | unit |
| INV-039 | Movimiento de item cosmetics sin lot_id → 422 | unit |
| INV-040 | Stock de LA y ZG se calculan por separado | integration |
| INV-041 | GET low-stock devuelve items con stock ≤ reorder_point | integration |
| INV-042 | POST item no asigna stock directo | integration |
| INV-043 | PUT item con movimientos no permite cambiar warehouse | integration |
| INV-044 | GET items con stock derivado | integration |
| INV-045 | DELETE item con movimientos → 422 | unit |
| INV-046 | DELETE item sin movimientos → ok | unit |
| INV-047 – INV-055 | Seeds cumplen cobertura | integration |

---

## 9. Compatibilidad con Incident Manager

- La base de datos de inventario es independiente (`inventory.db`).
- Las tablas del Incident Manager (`incidents`, `incident_audit_log`, `metadata`) no se modifican.
- El router de inventario se monta en `/api/inventory/` — no colisiona con `/api/incidents/`.
- La app FastAPI principal incluye ambos routers.
- Los tipos compartidos se añaden en nuevo archivo (`inventory.ts`), no se modifican los existentes (`incident.ts`).
- En el frontend, las nuevas páginas tienen rutas con prefijo `/inventory*` — no afectan a las rutas existentes.

---

## 10. Pasos de implementación

| Paso | Archivos | Descripción |
|---|---|---|
| 1 | `packages/shared/types/inventory.ts` | Tipos compartidos |
| 2 | `services/api/database_inventory.py` | Conexión y tablas de inventario |
| 3 | `services/api/routers/inventory.py` | Endpoints CRUD + movimientos |
| 4 | `services/api/seed_inventory.py` | Seeds (cobertura INV-047–055) |
| 5 | `services/api/main.py` | Montar router inventory + seed en startup |
| 6 | `uis/backoffice/src/types.ts` | Añadir tipos de inventario |
| 7 | `uis/backoffice/src/api.ts` | Añadir métodos API de inventario |
| 8 | `uis/backoffice/src/pages/inventory-*.ts` | Páginas del frontend |
| 9 | `uis/backoffice/src/main.ts` | Registrar rutas de inventario |
| 10 | `uis/backoffice/src/utils.ts`, `components/header.ts` | Badges low-stock, nav items |
| 11 | `services/api/tests/test_inventory.py` | Tests (pytest) |

---

## Trazabilidad de decisiones

| Decisión | INV cubiertos | Justificación |
|---|---|---|
| Stock derivado por SQL aggregation (sin columna stock) | INV-025, INV-026, INV-027, INV-028, INV-029, INV-030 | El stock se calcula siempre desde movimientos; no hay estado mutable que pueda desincronizarse |
| `adjustment.quantity` firmado (+/-) | INV-033 | No hay ambigüedad: positivo incrementa, negativo decrementa. El cálculo general es `inbound - outbound + adjustment` |
| UNIQUE(client_name, sku, warehouse) en items | INV-010, INV-011 | Identidad por tupla completa: mismo SKU puede existir en distinto cliente o distinto almacén |
| Validación transaccional en cada movimiento | INV-034, INV-035, INV-036, INV-037, INV-038, INV-039 | Cada movimiento se valida y ejecuta en una transacción; si alguna condición falla, rollback |
| `get_stock()` reutilizable en validación y en listados | INV-030, INV-031, INV-032, INV-033, INV-041, INV-044 | Una única lógica de cálculo evita inconsistencias entre el stock mostrado y el validado |
| Base de datos separada (`inventory.db`) | — | Aísla completamente el nuevo dominio del Incident Manager; permite evolucionar cada uno sin riesgo de regresiones |
| Router separado (`/api/inventory/`) | — | No colisiona con `/api/incidents/`; la app FastAPI principal incluye ambos |
| Frontend con prefijo `/inventory*` | — | Las rutas nuevas no interfieren con las del Incident Manager |
| Cosmetics requiere lote al crear artículo | INV-016 | La validación está en el momento de creación; si ya tiene lote, los movimientos pueden exigir lot_id |
| Lote opcional para fashion/electronics | INV-017 | Se permite crear artículos sin lotes; el lote puede añadirse después |
| No permitir DELETE con movimientos | INV-045 | Preserva la trazabilidad del histórico de movimientos; el artículo queda como referencia para los movimientos existentes |
| Warehouse bloqueado en PUT si hay movimientos | INV-043 | Cambiar el almacén reasignaría el histórico de movimientos a otra ubicación física, violando INV-040 |