# Almacenamiento de eventos de telemetría

`POST /telemetry/events` ya no se limita a escribir en el log: guarda los eventos en la tabla `public.telemetry_events` de Supabase (PostgreSQL). La URL, el sobre de [`event-schemas.json`](./event-schemas.json) y el cliente de la backoffice descrito en [`frontend-capture.md`](./frontend-capture.md) no cambian.

**Bloqueo:** `empresa-BRIEFING.md` sigue sin existir. Las métricas obligatorias no están verificadas y esta fase no añade ni da por buena ninguna.

**Entorno:** solo Supabase local (CLI 2.122.0, Postgres 17). Ninguno de los proyectos remotos de Supabase a los que tenemos acceso es de TrackFlow y no hay ninguno de desarrollo autorizado, así que la migración no se ha aplicado en remoto (ver [Limitaciones](#limitaciones)).

## Tabla `public.telemetry_events`

Migración versionada: [`services/api/supabase/migrations/20261026190259_create_telemetry_events.sql`](../../services/api/supabase/migrations/20261026190259_create_telemetry_events.sql).

| Columna | Tipo | Origen en el sobre |
|---|---|---|
| `event_id` | `uuid` PK | `eventId`. Clave de idempotencia. |
| `event_type` | `text` | `event_type` |
| `timestamp` | `timestamptz` | `timestamp` (UTC del origen) |
| `service` | `text` | La calcula la API: `properties.app` si el evento la trae (`backoffice`/`website`), si no, el `x-source` del catálogo (`backend`, `job`, `integration`…). El contrato no tiene un campo de servicio y no lo hemos añadido. |
| `session_id` | `uuid` null | `sessionId` |
| `user_id` | `text` null | `userId` (seudónimo `usr_…`, hoy siempre `null`) |
| `request_id` | `uuid` null | `requestId` |
| `tags` | `jsonb` | `properties` tal cual (dimensiones de negocio: `sku`, `warehouse`, `carrier`, `destination_country`…) más la clave `schemaVersion`. Las propiedades del contrato son `snake_case`, así que esa clave no puede chocar con ninguna. Las propiedades opcionales que no se envían no se guardan. |

La lista de 8 columnas sale del sobre del contrato. El enunciado del ejercicio no está en el repositorio: si exige otros nombres hay que ajustar la migración.

- **Índices:** `telemetry_events_timestamp_idx` (btree), `telemetry_events_event_type_idx` (btree) y `telemetry_events_tags_idx` (GIN sobre `tags`, para consultas `@>`). Aparte está el índice de la PK.
- **Inmutabilidad:** los triggers `BEFORE UPDATE OR DELETE` (por fila) y `BEFORE TRUNCATE` lanzan un error para cualquier rol, también para el propietario. Ningún rol tiene `UPDATE`, `DELETE` ni `TRUNCATE`, salvo el propietario, al que frenan los triggers.
- **Permisos:** `public` está expuesto por la Data API, por eso RLS está activado y forzado. A `anon`, `authenticated` y `service_role` les hemos quitado todos los permisos: desde el navegador no se puede ni leer ni escribir. El backend usa el rol de grupo `telemetry_writer` (`NOLOGIN`), que solo tiene `INSERT` y una política `FOR INSERT`. El rol de login de cada entorno y su contraseña no van en el repositorio.
- **Idempotencia:** `insert … on conflict do nothing`. No ponemos `(event_id)` como destino del conflicto porque PostgreSQL pediría `SELECT` sobre esa columna, y el rol del backend no puede leer. Funciona porque la PK es la única clave única de la tabla, y un test lo comprueba.

## Endpoint

`POST /telemetry/events` recibe `{ "events": [...] }` como lote crudo (máximo 100) y:

1. valida cada elemento por separado con `TypeAdapter(TelemetryEvent)`. El modelo de evento no cambia; los inválidos (incluidos los que no son objetos) se rechazan uno a uno;
2. descarta los `eventId` repetidos dentro del lote (se queda con el primero);
3. inserta todos los válidos en **una sola sentencia** (`jsonb_to_recordset`, una transacción) y devuelve `200 {"received": N, "stored": N, "rejected": N}`.

| Contador | Significado |
|---|---|
| `received` | Elementos de `events` |
| `stored` | Filas insertadas por esta petición (`rowcount`) |
| `rejected` | Elementos que no cumplen el contrato |

**Duplicados:** un evento válido cuyo `eventId` ya estaba guardado, o que se repite en el lote, no cuenta ni en `stored` ni en `rejected`. Por tanto, `received − stored − rejected` es el número de duplicados ignorados. Un reintento de un lote ya guardado devuelve `stored: 0`.

**Errores:** si el cuerpo no tiene la forma esperada (sin `events`, no es una lista, tiene campos extra o más de 100 elementos), la API responde `422` y no escribe nada. Si la base de datos falla o falta `TELEMETRY_DATABASE_DSN`, responde `503 {"detail": "Telemetry storage unavailable"}` sin contadores y no guarda nada del lote. El cliente reintenta los 5xx con los mismos `eventId`. Un lote vacío, o que solo contiene inválidos, responde 200 sin tocar la base de datos.

**Credenciales:** `TELEMETRY_DATABASE_DSN` solo existe en el entorno del backend, y ni los logs ni las respuestas incluyen la DSN. El frontend sigue llamando a `/api/telemetry/events` en el mismo origen.

## Ejecución local

Ver [`services/api/README.md`](../../services/api/README.md#telemetry-storage-local-supabase).

## Verificación

| Comprobación | Resultado |
|---|---|
| `uv run --frozen --extra dev pytest -q` con `TELEMETRY_TEST_*_DSN` (repetido el 2026-11-06) | **187 passed**, 0 skipped. Incluye 44 tests de `test_telemetry.py` (almacén simulado: lote válido, vacío, 100 elementos en una escritura, 13 inválidos individuales, restricciones numéricas, mixto, todos inválidos, duplicado en lote y ya guardado, fallo de BD → 503, falta de configuración → 503, error sin DSN, una sola sentencia, 5 formas de lote → 422, cuerpo no JSON y paridad con el contrato; y para `inventory_movement_recorded`: evento válido tras el 201, `requestId` reutilizado o generado si falta o no es válido, fallo de telemetría sin efecto en el movimiento, y 404/409 sin evento) y 21 de `test_telemetry_storage.py` contra Postgres real |
| Mismo comando sin esas variables | 166 passed, 21 skipped (los de integración) |
| `test_telemetry_storage.py` (BD `telemetry_test` de Supabase local) | Persistencia de todas las columnas, reenvío idempotente, 503 real con credenciales erróneas sin filas, **atomicidad** (lote con una fila que viola un `CHECK` → no se guarda ninguna), UPDATE/DELETE/TRUNCATE bloqueados para el propietario, `telemetry_writer` sin SELECT/UPDATE/DELETE, `anon`/`authenticated`/`service_role` sin lectura ni escritura, RLS forzado, PK como única clave única, uso de cada índice en `EXPLAIN` y persistencia de un evento emitido por el backend |
| `supabase db lint --local --schema public` | Sin errores |
| `npm test`, `npm run typecheck`, `npm run build` (backoffice, sin cambios) | 7 passed; PASS; PASS (con el aviso ya conocido de vulnerabilidad de Next.js 16.4.0) |

### Flujo frontend → FastAPI → Supabase local

Un script de Playwright 1.64.1 (Chromium 156, headless) abrió la backoffice servida con `next start` en :3001. La API corría con Uvicorn en :8000 y `TELEMETRY_DATABASE_DSN` apuntaba a la BD `postgres` del Supabase local con un rol que solo tiene `telemetry_writer`. Registro: [`evidence/storage-browser-run.json`](./evidence/storage-browser-run.json) y [`evidence/storage-browser-api.log`](./evidence/storage-browser-api.log).

1. A los 30 s, el primer flush (`page_viewed`, `web_vitals_measured` FCP y TTFB) devolvió `200 {"received":3,"stored":3,"rejected":0}`.
2. El script detuvo Uvicorn. El sondeo de `/api/status` devolvió 500 y la página registró un `frontend_error_occurred` (`fetch_failed`) con el mismo `requestId` que el `X-Request-Id` de ese sondeo. Después volvió a arrancar la API.
3. Con el contenedor de Postgres pausado (`docker pause`), el siguiente flush devolvió `503 {"detail":"Telemetry storage unavailable"}`. Al reanudarlo, el reintento a 1 s, con el mismo `eventId`, devolvió `200 {"received":1,"stored":1,"rejected":0}`.
4. Al ocultar la página, el CLS salió por `sendBeacon` y la API respondió `200 {"received":1,"stored":1,"rejected":0}`.

Resultado en la BD de desarrollo: **5 eventos, 5 `event_id` distintos** (1 `page_viewed`, 3 `web_vitals_measured`, 1 `frontend_error_occurred`, todos con `service = backoffice`). Al reenviar el primer lote real por el proxy de Next.js, la API respondió `{"received":3,"stored":0,"rejected":0}`. Filas, consultas y planes en [`evidence/storage-checks.txt`](./evidence/storage-checks.txt).

En esa ejecución (2026-10-26) todavía no había eventos de negocio. El primero se añadió después y se describe en [Evento de negocio desde el backend](#evento-de-negocio-desde-el-backend).

### Lote mixto

[`evidence/storage-mixed-batch.json`](./evidence/storage-mixed-batch.json) se envió con curl a una segunda instancia de la API en :8001, conectada a la BD `telemetry_test`, para no mezclar datos de prueba con los del flujo real. Contiene un `page_viewed` válido, un `inventory_movement_recorded` válido con datos de prueba, el mismo `page_viewed` repetido, uno con la propiedad no permitida `email` y uno con un `event_type` inexistente:

```json
{"received":5,"stored":2,"rejected":2}
```

El mismo lote enviado otra vez devuelve `{"received":5,"stored":0,"rejected":2}`. Un lote de 101 da 422 y uno vacío, `{"received":0,"stored":0,"rejected":0}`.

### Frontend intacto

`git diff main -- uis/` está vacío: no hemos tocado ninguna línea de `uis/` ni la URL del endpoint.

## Evento de negocio desde el backend

`POST /inventory/movements` emite `inventory_movement_recorded` cuando el movimiento ya está confirmado en la base de inventario. Es el único evento de negocio con disparador real hoy (demo local, `APP_ENV` development/test + `INVENTORY_DEMO_ENABLED`).

| Campo | Valor |
|---|---|
| `properties` | `sku`, `warehouse`, `quantity_delta` (el de la petición) y `quantity_after` (stock derivado tras el movimiento) |
| `timestamp` | `occurred_at` del movimiento en la base de inventario, en UTC con milisegundos |
| `requestId` | El `X-Request-Id` de la petición si es un UUID válido del contrato (se normaliza a minúsculas); si falta o no es válido, uno nuevo |
| `sessionId` / `userId` | `null` (no hay sesión de navegador ni Auth) |
| `service` | `backend` (el `x-source` del catálogo) |

- **Cuándo se guarda:** se programa como `BackgroundTask`, así que se escribe después de enviar la respuesta, con la misma inserción idempotente que el endpoint de ingesta (`emit_event` en `app/services/telemetry_store.py`). El evento se valida contra el contrato antes de guardarlo.
- **Rechazos:** un 404 (SKU/almacén inexistente), 409 (stock negativo) o 422 (cuerpo inválido) no emite nada. `inventory_movement_rejected` sigue sin implementar.
- **Fallos:** si falta `TELEMETRY_DATABASE_DSN`, la BD no responde o el evento no cumple el contrato, el movimiento no se ve afectado. La API registra `telemetry_emit_failed event_type=… error=<clase>` (sin DSN) y descarta el evento, **sin reintento**.

### Flujo real: movimiento → FastAPI → Supabase local

Ejecutado el 2026-11-06 con un `docker compose run` puntual del servicio `api` (sin modificar `docker-compose.yml`): el inventario demo en el Postgres de Compose y `TELEMETRY_DATABASE_DSN` pasada con `-e` hacia la BD `postgres` del Supabase local, con un rol de login temporal que solo tenía `telemetry_writer` y que se borró al terminar. Registro completo: [`evidence/business-event-checks.txt`](./evidence/business-event-checks.txt).

| Caso | Respuesta | Evento guardado |
|---|---|---|
| Salida válida con `X-Request-Id` | 201 | Sí, con ese `request_id` |
| Entrada válida con `X-Request-Id` en mayúsculas | 201 | Sí, con el `request_id` en minúsculas |
| Entrada válida sin `X-Request-Id` | 201 | Sí, con un `request_id` generado |
| SKU inexistente, con y sin `X-Request-Id` | 404 | No |
| Stock insuficiente | 409 | No |
| `quantity_delta: 0` | 422 | No |
| Salida válida con el Postgres de Supabase pausado (`docker pause`) | 201 en 16 ms | No; el movimiento sí queda confirmado y el log muestra `telemetry_emit_failed … error=TelemetryStoreError` |

Resultado: 4 movimientos confirmados en el inventario y 3 eventos `inventory_movement_recorded` en Supabase, uno por cada movimiento con la telemetría disponible. En cada fila, `quantity_after` coincide con el stock que devolvió la API y `timestamp` con `occurred_at` truncado a milisegundos.

## Limitaciones

- **Supabase remoto:** no hay un proyecto de desarrollo de TrackFlow autorizado. La migración solo se ha aplicado y verificado en local. Para aplicarla en remoto hace falta autorización y crear allí el rol de login del backend.
- **Compose:** `docker-compose.yml` no pasa `TELEMETRY_DATABASE_DSN` al contenedor `api` (es configuración de infraestructura y no la hemos tocado). Con el stack de Compose, el endpoint responde 503 y el cliente agota sus 3 reintentos. Para conectarlo hay que autorizar el cambio y apuntar la DSN al Postgres de Supabase.
- **Lista de columnas:** el enunciado del ejercicio no está en el repositorio; hemos derivado las 8 columnas del sobre del contrato.
- **Retención:** la retención de 30/90 días que propone el plan obliga a borrar filas, y los triggers lo impiden. Hará falta un procedimiento de mantenimiento controlado por el propietario que no está implementado.
- **Conexiones:** se abre una conexión por lote, sin pool. Sirve en desarrollo, pero para más volumen habría que usar el pooler de Supabase o un pool en la API.
- **Eventos del backend sin reintento:** si el almacén no está disponible, `inventory_movement_recorded` se pierde (solo queda el aviso en el log). El cliente de la backoffice sí reintenta; el backend no tiene cola ni buffer.
- **`X-Request-Id`:** de momento solo lo lee `POST /inventory/movements`. El middleware no lo valida ni lo devuelve en la respuesta, así que el cliente no conoce el `requestId` que se genera cuando no lo envía.
- Siguen pendientes los demás eventos backend con disparador real (`inventory_movement_rejected`, `inventory_stock_low_detected`, `inventory_items_viewed`, `api_request_failed`, `api_request_completed`, `service_status_changed`, `inventory_seed_executed`) y la lectura de los datos (no hay rol lector ni endpoint de consulta).
