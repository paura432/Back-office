# Performance Optimisation: Caching — TrackFlow

- **Fecha de verificación:** 2026-10-26
- **Rama:** `feature/caching-optimisation`
- **Entorno de verificación:** WSL2 (kernel 6.6.87.2), 16 CPU lógicas, Docker 29.1.3, PostgreSQL 16.15 (`postgres:16-alpine`), Python 3.12.10 en el contenedor `api`, Node 24.14.0 / Next.js 16.4.0 en host.
- **Datos:** exclusivamente el seed sintético local (`seed_inventory.py`) sobre el PostgreSQL del Compose de desarrollo. No se accedió a producción ni a credenciales reales.

## Resumen

- Dos lecturas de inventario cacheadas con TTL de 30 s e invalidación tras escritura: `GET /inventory/items` y `GET /inventory/alerts` (el detalle `GET /inventory/items/{sku}` comparte la misma caché).
- Medición real antes/después con `bench_inventory.py`: la mediana baja de ~10–28 ms (lectura PostgreSQL) a ~0,02–0,04 ms (hit de caché) según endpoint y corrida.
- Tests FastAPI: **122 passed**. Builds de website y backoffice: **PASS**.
- Lazy loading y `useMemo` se descartan de forma justificada: no hay componentes pesados ni cálculos derivados que optimizar (detalle abajo).

## Implementación

| Pieza | Archivo | Comportamiento |
|---|---|---|
| Caché TTL | `services/api/app/services/ttl_cache.py` | Caché in-process, thread-safe (`RLock`), reloj monotónico, TTL configurable; entrada expirada en `now >= expires_at`. Devuelve copias profundas para que el llamante no mute la entrada cacheada. |
| Lecturas de inventario | `services/api/app/services/demo_inventory.py` | `INVENTORY_TTL_SECONDS = 30`. Claves tipadas por lectura y filtros normalizados: `("items", warehouse, sku, q)`, `("alerts", warehouse)`, `("item", sku, warehouse)`. `warehouse`/`q` se normalizan a minúsculas y `sku` a mayúsculas, así que variantes de mayúsculas comparten entrada. |
| Modelo de stock | mismo archivo | Tablas locales `inventory_items` (metadatos, umbral) e `inventory_movements` (deltas firmados). La cantidad es `SUM(quantity_delta)`; no hay endpoint para fijarla. |
| Invalidación | `register_inventory_movement` | `POST /inventory/movements` inserta el movimiento (404 si el SKU/almacén no existe, 409 si dejaría stock negativo) y, tras confirmar la transacción, vacía todas las entradas de inventario. |
| Gate de demo | `services/api/app/services/inventory_demo_gate.py` | Todas las rutas `/inventory/*` responden 404 salvo `APP_ENV ∈ {development, test}` **y** `INVENTORY_DEMO_ENABLED` verdadero. Compose de desarrollo activa ambas. |
| Guard de BD local | `demo_inventory._assert_local_database`, `seed_inventory.validate_local_dsn` | Rechazan cualquier DSN que no apunte a la BD `trackflow` en `db`, `localhost`, `127.0.0.1` o `::1`, antes de conectar. |
| Seeder | `services/api/seed_inventory.py` | 12 pares SKU/almacén ficticios (6 SKU × Los Ángeles/Zaragoza), con stock cero y casos de alerta en ambos almacenes. Movimientos identificados por `seed_key` estable y UPSERT; nunca borra filas. |
| Benchmark | `services/api/bench_inventory.py` | 200 llamadas por endpoint y fase sobre el mismo proceso y dataset. |
| Instrumentación | `services/api/main.py` | Middleware que registra método, plantilla de ruta, status y `duration_ms`, sin URL raw, query string ni payload. |

### Correcciones aplicadas en esta revisión

1. **UPSERT del seeder.** El índice único `inventory_movements_seed_key_idx` es parcial (`WHERE seed_key IS NOT NULL`). `ON CONFLICT (seed_key)` sin predicado fallaba contra PostgreSQL real con `InvalidColumnReference: there is no unique or exclusion constraint matching the ON CONFLICT specification` (reproducido con la versión anterior; la transacción se revirtió completa). Ahora usa `ON CONFLICT (seed_key) WHERE seed_key IS NOT NULL`, y el test lo exige.
2. **Filtros opcionales en SQL.** `(%s IS NULL OR …)` con parámetro `None` fallaba en PostgreSQL real con `IndeterminateDatatype: could not determine data type of parameter $1` (HTTP 500 en `GET /inventory/items` sin filtros). Se añadió `%s::text IS NULL` en las tres lecturas y un test de regresión. Los tests previos usaban mocks y no lo detectaban.

## Verificación ejecutada

| Comprobación | Comando / método | Resultado |
|---|---|---|
| Suite FastAPI | `cd services/api && uv run --frozen --extra dev pytest -q` | **PASS** — 122 passed, 0 failed (cobertura de `app`, `main`, `db`, `seed_inventory`: 96 %) |
| Build website | `cd uis/website && npm ci && npm run build` | **PASS** (exit 0). La primera invocación se detuvo con exit 1 solo para mostrar un aviso de vulnerabilidad de Next.js 16.4.0; al repetir compila sin errores. Ver limitaciones. |
| Build backoffice | `cd uis/backoffice && npm ci && npm run build` | **PASS** (exit 0), mismo aviso. |
| Stack local | `docker compose up --build -d --wait db api` | `db` y `api` healthy |
| Seeder ×2 | `docker compose exec api python seed_inventory.py` (dos veces) | Tras ambas: 12 ítems, 22 movimientos (11 pares con stock > 0 × 2), 0 `seed_key` duplicados, mismo hash de `(id, seed_key, delta)` → actualiza en sitio, no reinserta |
| Conservación de movimientos | Ítem y movimiento ajenos al seed creados por SQL, luego reseed | Movimiento ajeno intacto; recuentos y hash sin cambios |
| Movimientos sin `seed_key` en pares demo | Reseed tras un `POST` de API y un `INSERT` externo | El seeder se niega (`RuntimeError … origin is ambiguous`), revierte y no altera ninguna fila (diseño intencionado, ver limitaciones) |

### Comportamiento de caché por HTTP real (API en Compose, puerto 8000)

| Caso | Observado |
|---|---|
| Miss inicial | `GET /inventory/items?sku=DEMO-BOX-001&warehouse=los-angeles` → quantity 38 |
| Hit | Tras `INSERT` externo de +5 por SQL, misma clave a t=0,2 s → 38 (servido desde caché) |
| Aislamiento de filtros | `?warehouse=los-angeles` (otra clave) → 43 en la misma ventana |
| Normalización | `?sku=demo-box-001&warehouse=LOS-ANGELES` → 38 (misma entrada que la clave original) |
| TTL vigente | t=28,0 s → 38 |
| Expiración | t=30,5 s → 43 |
| Invalidación de alertas | `GET /inventory/alerts?warehouse=zaragoza` incluía `DEMO-BOX-001` (8 ≤ 10); `POST` +5 → 201 (quantity 13); la lectura inmediata ya no la incluye |
| Invalidación de listado | `GET /inventory/items?warehouse=zaragoza` pasa de 8 a 13 inmediatamente tras el `POST` |
| Aislamiento entre almacenes | Alertas Zaragoza: BOX, FILL, TAPE; Los Ángeles: LABEL (0), MAILER, PALLET |
| Validaciones de escritura | Delta que deja stock negativo → 409; SKU inexistente → 404 |

### Bloqueo de rutas demo fuera de desarrollo (Uvicorn real)

Las cuatro rutas (`GET /inventory/items`, `GET /inventory/items/{sku}`, `GET /inventory/alerts`, `POST /inventory/movements`) devolvieron **404 `Inventory demo is not enabled`** con: `APP_ENV=production` + flag activo, `APP_ENV=staging` + flag activo, sin variables y `APP_ENV=development` sin flag. Los tests `test_inventory_demo_gate.py` cubren los mismos casos.

## Mediciones antes/después

`bench_inventory.py` ejecutado dentro del contenedor `api` contra el dataset canónico del seed (hash verificado igual al de la primera siembra). **Antes** = caché vaciada antes de cada llamada (lectura PostgreSQL, incluida la apertura de conexión que hace `_connect()` por lectura). **Después** = caché precalentada, se miden hits. 200 llamadas por endpoint y fase. Mide tiempo de llamada al servicio, no transporte HTTP. Salida bruta en `audit/caching/bench-run-1.json` y `audit/caching/bench-run-2.json`.

| Endpoint | Filas | Corrida | Antes mediana | Antes p95 | Después mediana | Después p95 |
|---|---:|---|---:|---:|---:|---:|
| `GET /inventory/items` | 12 | 1 (16:22:08Z) | 28,122 ms | 57,491 ms | 0,043 ms | 0,096 ms |
| `GET /inventory/items` | 12 | 2 (16:22:26Z) | 10,149 ms | 14,045 ms | 0,036 ms | 0,052 ms |
| `GET /inventory/alerts` | 6 | 1 (16:22:08Z) | 22,297 ms | 44,723 ms | 0,022 ms | 0,040 ms |
| `GET /inventory/alerts` | 6 | 2 (16:22:26Z) | 9,829 ms | 16,302 ms | 0,019 ms | 0,042 ms |

La fase "antes" varía bastante entre corridas consecutivas (la primera es ~2–3× más lenta); no se descarta ninguna. En ambas, el hit es más de dos órdenes de magnitud más rápido. Con 12 y 6 filas el coste dominante es la ida a PostgreSQL, no el tamaño del resultado; estas cifras no extrapolan a volúmenes reales ni incluyen HTTP/serialización.

## Decisiones

- **TTL 30 s.** Ventana corta porque el stock es volátil; la invalidación explícita cubre las escrituras por API y el TTL acota la antigüedad ante cambios SQL externos (verificado arriba).
- **Invalidación total de inventario.** Un movimiento vacía todas las claves (listados, alertas y detalle). Es más simple y seguro que calcular qué combinaciones de filtros se ven afectadas; con este volumen el coste del miss posterior es bajo.
- **Caché in-process.** Suficiente para el ejercicio y sin nuevas dependencias ni infraestructura. No se añadió Redis ni otra pieza de arquitectura.
- **Endpoints no cacheados.** `/health` y `/status` (monitorización: una respuesta cacheada ocultaría una caída) y los 15 GET restantes, que siguen siendo stubs 501 (no se cachean errores). Rutas con datos personales o por tenant (`/auth/me`, `/users/*`, `/customers/*`, `/orders/*`, `/returns/*`, `/shipments/*`) no deben usar caché compartida cuando se implementen.
- **Seeder conservador.** Solo inserta o actualiza sus filas con `seed_key`; nunca borra. Si encuentra movimientos sin `seed_key` en sus pares, no puede distinguir datos de prueba de movimientos legítimos y se detiene sin cambios.

### Lazy loading y `useMemo`: no aplicados

Revisión del código y del build de producción de esta rama:

- Ambas apps dependen únicamente de `next`, `react` y `react-dom`; el código de `app/` suma 226 líneas.
- Los chunks propios de página son de 1 416 B (website) y 872 B (backoffice). Los chunks grandes (~200–240 KB) son el runtime de React/Next, que el lazy loading de componentes no elimina.
- Solo hay dos Client Components: `SiteHeader` (19 líneas, estado del menú móvil, visible en la carga inicial) y `BackendStatus` (49 líneas, fetch a `/api/status` cada 15 s, visible arriba del todo). Diferirlos retrasaría contenido visible sin ahorro medible.
- No hay cálculos derivados en render: las listas (4 servicios, 5 áreas, 4 prioridades) son constantes de módulo. `useMemo` añadiría trabajo de comparación sin evitar ningún cómputo.

Aplicar `dynamic()`/`lazy()` o `useMemo` aquí sería artificial. Se reevaluará si se añaden tablas grandes, gráficos, filtrado o dependencias pesadas en cliente.

## Limitaciones

- La caché es por proceso: con varios workers cada uno tiene la suya y una escritura solo invalida la del worker que la atiende; los demás convergen por TTL (≤ 30 s). No sirve como coordinación de inventario en producción.
- `get_or_set` mantiene el lock durante la consulta, así que los misses concurrentes se serializan (sin estampida, pero sin paralelismo). Aceptable para la demo.
- Cada miss abre una conexión PostgreSQL nueva (sin pool), lo que infla la fase "antes".
- Tras registrar movimientos por API en pares demo, el seeder se niega a reejecutarse; para volver al dataset canónico hay que recrear la BD local.
- El benchmark mide la llamada al servicio en proceso, no latencia HTTP de extremo a extremo ni carga concurrente.
- Next.js 16.4.0 muestra un aviso de vulnerabilidad conocida en `next build`. Actualizar dependencias globales queda fuera del alcance de esta práctica y requiere decisión aparte.
- Los tests usan uv 0.11.16 en host; el contenedor fija uv 0.6.17. `uv.lock` no cambió.

## Requisitos de la práctica

| Requisito | Estado | Evidencia |
|---|---|---|
| Seeder local reproducible | ✅ Cumplido | Dos ejecuciones idempotentes, sin duplicados, conservando movimientos ajenos |
| 2 endpoints con caché TTL | ✅ Cumplido | `/inventory/items` y `/inventory/alerts`, TTL 30 s verificado por HTTP |
| Invalidación al modificar datos | ✅ Cumplido | `POST /inventory/movements` invalida listado y alertas al instante |
| Medición antes/después | ✅ Cumplido | Tabla anterior y `audit/caching/*.json` |
| Sin exposición fuera de desarrollo | ✅ Cumplido | Gate 404 verificado en producción/staging/sin flag |
| 2 casos de lazy loading | ⚠️ No aplicado, justificado | Sin componentes pesados ni diferibles (sección anterior) |
| 1 uso de `useMemo` | ⚠️ No aplicado, justificado | Sin cálculos derivados en render |
| Tests y builds | ✅ PASS | 122 tests; website y backoffice compilan |

## Reproducción

Desde la raíz, solo contra el stack local:

```sh
docker compose up --build -d --wait db api
docker compose exec api python seed_inventory.py
docker compose exec api python bench_inventory.py
cd services/api && uv run --frozen --extra dev pytest -q
cd uis/website && npm ci && npm run build
cd uis/backoffice && npm ci && npm run build
```
