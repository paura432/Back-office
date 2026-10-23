# Auditoría de serialización backend — cierre de implementación

**Proyecto:** TrackFlow / 4Geeks Academy  
**Rama:** `feature/serialization-audit`  
**Fecha de verificación:** 2026-10-23  
**Alcance:** revisar y cerrar auditoría de serialización, integrar `origin/main` preservando `/health`, `/status` y PostgreSQL, estabilizar dependencias, validar OpenAPI y pruebas HTTP. No se implementa lógica de negocio nueva.

> Inventario endpoint-por-endpoint recuperado de `12feda2` y ampliado con la ruta `/status`. Las clasificaciones heredadas describen el diseño de schemas y riesgos, no el funcionamiento: el estado HTTP actual se indica explícitamente en cada fila. `✅` no equivale a endpoint funcional.

## Resultado ejecutivo

- Se fusionó `origin/main`; se conservaron la ruta `/health`, `/status` y la comprobación PostgreSQL (`SELECT 1` mediante `psycopg`).
- 32 rutas de aplicación FastAPI están registradas y declaran `response_model` Pydantic explícito, incluido `/status`. Los endpoints preexistentes de negocio/auth permanecen claramente como stubs `501 Not Implemented`; no se inventaron respuestas de éxito ni resultados de negocio.
- Las rutas automáticas `/openapi.json`, `/docs`, `/docs/oauth2-redirect` y `/redoc` son endpoints de infraestructura de FastAPI y no rutas de aplicación con payload de negocio.
- Requests y responses tienen schemas distintos en las operaciones de entrada/salida. Las respuestas tipadas limitan los campos a la allowlist declarada; se verificó en una respuesta HTTP real que se excluyen password, hash, salt, reset token y metadata extra.
- Los schemas de resumen siguen separados y ligeros frente a detalles; relaciones anidadas intencionales (`OrderDetail.items`, `ShipmentDetail.events`, KPIs) están tipadas explícitamente. No hay ORM ni datos reales que serializar.
- Dependencias runtime y de tests están fijadas y `uv.lock` fue regenerado; `uv sync --frozen --extra dev --check` pasa.
- Resultado real final: **91 tests PASS, 0 FAIL, 0 skipped** y cobertura **100%** del código medido (`app`, `main.py`, `db.py`). Incluye los dos casos del test parametrizado de `/status` (`True → operational`, `False → degraded`); pytest los cuenta como nodos separados.

## Inventario exhaustivo

Los esquemas reales de salida y entrada se consultaron en los ficheros `services/api/app/schemas/*.py`. “Necesita” se refiere a los campos del contrato que requiere el propósito explícito de la ruta; no se detectan consumidores UI de las rutas de negocio (el backoffice sí consulta `/status`). “Propuesta” es una recomendación documental, no una modificación de contrato o un requisito inventado. “No observable” indica que la ruta siempre lanza 501 y no retorna un objeto de éxito.

| # | Método y ruta | Propósito y entrada actual | `response_model` declarado → salida real actual | Consumidor UI y campos necesarios | Campos excluidos / recomendación de contrato | Estado y evidencia |
|---:|---|---|---|---|---|---|
| 1 | `GET /health` | Liveness. Sin entrada. Status declarado 200. | `HealthResponse` → `{"status":"ok"}` (real). | Docker y documentación describen health; `status`. No se encontró una llamada UI específica a `/health`. | Excluir detalles internos de runtime, host, entorno y credenciales. Mantener `HealthResponse{status}`. | ✅ funcional. `routers/health.py:8-11`; `schemas/health.py`; test HTTP ASGI. |
| 2 | `POST /auth/register` | Registro. Body `RegisterRequest{email,password,full_name}`. Status declarado 201. | `MessageResponse` → no observable: 501. | Sin consumidor UI detectado. Para confirmar registro basta `message` genérico. | Nunca retornar password, hash/salt, token, estado secreto ni datos internos. Propuesta: respuesta genérica sin revelar si un email ya existe; éxito real pendiente. | ⚠️. `routers/auth.py:15-19`; `schemas/auth.py:RegisterRequest,MessageResponse`. |
| 3 | `POST /auth/login` | Inicio de sesión. Body `LoginRequest{email,password}`. Status declarado 200. | `TokenResponse` → no observable: 501. | Sin consumidor UI; cuando haya login, cliente autenticado requerirá `access_token`, `token_type`, `expires_in`. | Contraseña y hash nunca en salida/logs. Token solo aquí; requiere auth real antes de confiar en contrato. | ⚠️. `routers/auth.py:22-25`; `schemas/auth.py:LoginRequest,TokenResponse`. |
| 4 | `GET /auth/me` | Perfil de usuario autenticado. Sin entrada explícita. Status declarado 200. | `UserProfileResponse` → no observable: 501. | Sin consumidor UI. Perfil mínimo declarado: `id,email,full_name,is_active`. | Excluir password/hash/salt, token y claims internos. Ruta no implementa autenticación/autorización; protección es requisito antes de exposición. | ⚠️. `routers/auth.py:28-31`; `schemas/auth.py:UserProfileResponse`. |
| 5 | `POST /auth/password-recovery` | Solicitar recuperación. Body `PasswordRecoveryRequest{email}`. Status declarado 200. | `MessageResponse` → no observable: 501. | Sin consumidor UI; necesita mensaje genérico de confirmación. | No retornar ni confirmar existencia del email; nunca emitir token de recuperación. Token de reset de entrada no debe quedar expuesto en logs. | ⚠️. `routers/auth.py:34-37`; `schemas/auth.py:PasswordRecoveryRequest,MessageResponse`. |
| 6 | `POST /auth/password-reset` | Cambiar contraseña con token. Body `PasswordResetRequest{token,new_password}`. Status declarado 200. | `MessageResponse` → no observable: 501. | Sin consumidor UI; necesita confirmación genérica. | Excluir token, nueva contraseña y hashes de salida. Token/password deben ser secretos de entrada. | ⚠️. `routers/auth.py:40-43`; `schemas/auth.py:PasswordResetRequest,MessageResponse`. |
| 7 | `GET /inventory/items` | Lista inventario. Sin entrada. | `list[InventoryItemSummary]` → no observable: 501. | Sin consumidor UI. Esquema de lista: `sku,name,warehouse,quantity,low_stock_threshold`. | No hay ORM ni payload excesivo observable; revisión futura debe excluir metadatos/logística internos no usados. | ✅. `routers/inventory.py:8-11`; `schemas/inventory.py:InventoryItemSummary`. |
| 8 | `GET /inventory/items/{sku}` | Detalle SKU. Path `sku:str`. | `InventoryItemDetail` → no observable: 501. | Sin consumidor UI. `sku,name,description,warehouse,quantity,low_stock_threshold,last_updated`. | Mantener metadatos internos de persistencia fuera; no observables. | ✅. `routers/inventory.py:14-17`; `schemas/inventory.py:InventoryItemDetail`. |
| 9 | `GET /inventory/alerts` | Alertas bajo umbral. Sin entrada. | `list[InventoryAlert]` → no observable: 501. | Sin consumidor UI. `sku,name,warehouse,current_quantity,threshold`. | Excluir metadatos internos/relaciones no necesarias; no se observa ORM. | ✅. `routers/inventory.py:20-23`; `schemas/inventory.py:InventoryAlert`. |
| 10 | `GET /orders/` | Lista pedidos. Sin entrada. | `list[OrderSummary]` → no observable: 501. | Sin consumidor UI. `id,client_name,status,item_count,created_at`. | No incluir dirección ni líneas completas en lista. Sin payload real que confirmar. | ✅. `routers/orders.py:12-16`; `schemas/orders.py:OrderSummary`. |
| 11 | `GET /orders/{order_id}` | Detalle pedido. Path `order_id:int`. | `OrderDetail` → no observable: 501. | Sin consumidor UI. `id,client_id,client_name,items[{sku,name,quantity}],status,shipping_address,notes,created_at,updated_at`. | Direcciones/notas son datos de detalle potencialmente sensibles; restringir acceso y no añadir relación ORM completa. Propuesta mantiene el detalle ya declarado, mínimo aún por validar con consumidor. | ⚠️. `routers/orders.py:19-22`; `schemas/orders.py:OrderDetail`. |
| 12 | `POST /orders/` | Crear pedido. Body `OrderCreateRequest{client_id,items[{sku,quantity}],shipping_address,notes?}`. Status declarado 201. | `OrderDetail` → no observable: 501. | Sin consumidor UI. Respuesta declarada es detalle anterior. | Entrada tiene modelo separado de la salida (no declara `id,status,created_at,updated_at,client_name`); `notes`/dirección se devuelven solo en schema de detalle. Los campos extra no están configurados para rechazo estricto. | ✅. `routers/orders.py:25-28`; `schemas/orders.py:OrderCreateRequest,OrderDetail`. |
| 13 | `PATCH /orders/{order_id}/status` | Cambiar estado. Path `order_id:int`; body `OrderStatusUpdate{status:str}`. | `OrderDetail` → no observable: 501. | Sin consumidor UI; estado actualizado (y detalle si el cliente lo necesita) no comprobado. | `status` acepta cualquier cadena no vacía hasta 50 caracteres; restricciones de transición/enum y otros campos no están definidas. Confirmar estados con producto antes de endurecer. | ⚠️. `routers/orders.py:31-34`; `schemas/orders.py:OrderStatusUpdate`. |
| 14 | `GET /shipments/` | Lista envíos. Sin entrada. | `list[ShipmentSummary]` → no observable: 501. | Sin consumidor UI. `id,tracking_number,carrier,recipient,status,estimated_delivery`. | Evitar dirección completa, eventos e información de transportista no necesaria en listado. Destinatario/seguimiento necesitan política de acceso cuando se implemente. | ⚠️. `routers/shipments.py:12-17`; `schemas/shipments.py:ShipmentSummary`. |
| 15 | `GET /shipments/{shipment_id}` | Detalle de envío. Path `shipment_id:int`. | `ShipmentDetail` → no observable: 501. | Sin consumidor UI. Detalle declarado: `id,tracking_number,carrier,carrier_tracking_url,recipient,destination,weight_kg,status,estimated_delivery,events[{timestamp,location,status,description}]`. | Dirección/destino, peso, URL externa e historial son payload sensible/relación anidada a justificar. La UI no da requisitos para ello. | ⚠️. `routers/shipments.py:20-23`; `schemas/shipments.py:ShipmentDetail,TrackingEvent`. |
| 16 | `GET /shipments/tracking/{tracking_number}` | Tracking por número. Path `tracking_number:str`. | `ShipmentDetail` → no observable: 501. | Sin consumidor UI; el contexto de negocio desea tracking público, pero no fija campos UI. | No exponer automáticamente `recipient`, destino completo, peso ni eventos internos del proveedor. Propuesta mínima: `tracking_number,carrier,status,estimated_delivery,events` con ubicación/descripción publicable definida por negocio. Auth y privacidad pendientes de decisión; no aplicar como contrato ahora. | ⚠️. `routers/shipments.py:26-29`; `schemas/shipments.py:ShipmentDetail`. |
| 17 | `POST /shipments/carrier-recommendation` | Recomendar carrier. `CarrierRecommendationRequest{destination,weight_kg,urgency}`. | `list[CarrierRecommendation]` → no observable: 501. | Sin consumidor UI; salida declarada `carrier,estimated_cost,estimated_days,confidence_score`. | No se incluyen campos internos en schema; `destination` es libre, validar política de datos con implementación. | ✅. `routers/shipments.py:32-35`; `schemas/shipments.py:CarrierRecommendationRequest,CarrierRecommendation`. |
| 18 | `GET /returns/` | Lista devoluciones. Sin entrada. | `list[ReturnRequestSummary]` → no observable: 501. | Sin consumidor UI. `id,order_id,sku,status,created_at`. | No incluir motivo/notas de inspección en lista. | ✅. `routers/returns.py:12-16`; `schemas/returns.py:ReturnRequestSummary`. |
| 19 | `GET /returns/{return_id}` | Detalle devolución. Path `return_id:int`. | `ReturnRequestDetail` → no observable: 501. | Sin consumidor UI. `id,order_id,sku,product_name,quantity,reason,status,inspection_notes,created_at,updated_at`. | Motivo y observaciones pueden contener texto libre; autorizaciones y redacción no definidas. No se ve entidad ORM/relación. | ⚠️. `routers/returns.py:19-23`; `schemas/returns.py:ReturnRequestDetail`. |
| 20 | `POST /returns/` | Crear devolución. Body `ReturnRequestInput{order_id,sku,quantity,reason}`. Status declarado 201. | `ReturnRequestDetail` → no observable: 501. | Sin consumidor UI. Detalle declarado en respuesta. | Entrada separada del schema de detalle (no declara `id,status,inspection_notes,created_at`); campos extra no se configuran para rechazo estricto. Validar autorización de pedido/SKU al implementar. | ✅. `routers/returns.py:26-29`; `schemas/returns.py:ReturnRequestInput,ReturnRequestDetail`. |
| 21 | `POST /returns/{return_id}/approve` | Aprobar/rechazar. Path `return_id:int`; `ReturnApproval{approved,notes?}`. | `ReturnRequestDetail` → no observable: 501. | Sin consumidor UI; quizá necesita estado resultante, contrato no confirmado. | Estado está correctamente fuera de body; la autorización del actor y transición de estado no están implementadas. Nota libre potencialmente sensible. | ⚠️. `routers/returns.py:32-35`; `schemas/returns.py:ReturnApproval`. |
| 22 | `POST /returns/{return_id}/inspect` | Registrar inspección. Path `return_id:int`; `ReturnInspectionResult{condition,notes?}`. | `ReturnRequestDetail` → no observable: 501. | Sin consumidor UI; contrato declarado refleja detalle actualizado. | `condition` enum limitado; `notes` libre. No se admiten ID/orden/estado por body. | ✅. `routers/returns.py:38-41`; `schemas/returns.py:ReturnInspectionResult`. |
| 23 | `GET /customers/` | Lista clientes. Sin entrada. | `list[CustomerSummary]` → no observable: 501. | Sin consumidor UI. `id,company_name,contact_email,country,is_active`. | Contacto/email es PII empresarial, limitar acceso; no debe incorporar direcciones/notas. | ⚠️. `routers/customers.py:8-11`; `schemas/customers.py:CustomerSummary`. |
| 24 | `GET /customers/{customer_id}` | Detalle cliente. Path `customer_id:int`. | `CustomerDetail` → no observable: 501. | Sin consumidor UI. `id,company_name,contact_name,contact_email,contact_phone,country,address,is_active,notes`. | Teléfono, dirección y notas libres son datos personales/operativos potenciales; detalle debe ser autorizado y minimizarse por necesidad confirmada. | ⚠️. `routers/customers.py:14-17`; `schemas/customers.py:CustomerDetail`. |
| 25 | `GET /customers/{customer_id}/health` | Score de salud/riesgo. Path `customer_id:int`. | `CustomerHealthScore` → no observable: 501. | Sin consumidor UI. `customer_id,company_name,health_score,risk_level,contract_end_date`. | Excluir datos de cálculo y relaciones subyacentes; limitar riesgo comercial a usuarios autorizados. | ✅. `routers/customers.py:20-23`; `schemas/customers.py:CustomerHealthScore`. |
| 26 | `GET /dashboard/executive` | KPIs ejecutivos. Sin entrada. | `ExecutiveDashboard` → no observable: 501. | Sin consumidor UI. Seis KPIs: `total_shipments,on_time_rate,operational_cost,return_rate,active_customers,customer_satisfaction`, cada uno `{label,value,unit,previous_value,trend}`. | No incluir datos por persona/cliente ni registros fuente sin necesidad. Acceso ejecutivo no está implementado. | ✅. `routers/dashboard.py:8-11`; `schemas/dashboard.py:ExecutiveDashboard,DashboardKPI`. |
| 27 | `GET /dashboard/weekly-report` | Informe semanal. Sin entrada. | `WeeklyReport` → no observable: 501. | Sin consumidor UI. `week,generated_at,summary,highlights,metrics`. | `metrics:dict[str,float]` permite cualquier clave y no expresa unidades ni vocabulario; acordar métricas y cerrar tipo antes de producción. | ⚠️. `routers/dashboard.py:14-17`; `schemas/dashboard.py:WeeklyReport`. |
| 28 | `GET /users/` | Lista usuarios. Sin entrada. | `list[UserSummary]` → no observable: 501. | Sin consumidor UI. `id,email,full_name,role,is_active`. | Emails/nombres son información personal; restringir listado. Excluir credenciales/hash/salt/tokens. | ⚠️. `routers/users.py:8-11`; `schemas/users.py:UserSummary`. |
| 29 | `GET /users/{user_id}` | Detalle usuario. Path `user_id:int`. | `UserDetail` → no observable: 501. | Sin consumidor UI. `id,email,full_name,role,is_active,created_at`. | Excluye password, pero requiere autorización y no incluye hashes/tokens. | ✅. `routers/users.py:14-17`; `schemas/users.py:UserDetail`. |
| 30 | `POST /users/` | Crear usuario. Body `UserCreate{email,password,full_name,role}`. Status declarado 201. | `UserDetail` → no observable: 501. | Sin consumidor UI. Salida `UserDetail`. | Entrada incluye `password` deliberadamente; no retornarlo ni persistirlo en claro. Validación de rol restringe a admin/operator/viewer. No hay autenticación admin. Los campos extra no están configurados para rechazo estricto. | ✅*. `routers/users.py:20-23`; `schemas/users.py:UserCreate,UserDetail`. |
| 31 | `PATCH /users/{user_id}` | Actualizar usuario. Path `user_id:int`; `UserUpdate{full_name?,role?,is_active?}`. | `UserDetail` → no observable: 501. | Sin consumidor UI. Salida `UserDetail`. | Lista de entrada excluye email, password, id y `created_at`, evitando modificación masiva de estos campos. Restringe rol por patrón. Autoría/autorización no implementada. | ✅*. `routers/users.py:26-29`; `schemas/users.py:UserUpdate,UserDetail`. |

| 32 | `GET /status` | Estado de disponibilidad de la API y PostgreSQL; sin entrada. `SELECT 1`. | `StatusResponse{status: operational|degraded}` → HTTP 200, JSON tipado, según éxito/fallo de conexión. | Backoffice solicita `/api/status` desde `uis/backoffice/app/backend-status.tsx`; requiere `status`. No se devuelve diagnóstico de conexión. | Excluir DSN, host, credenciales, errores/excepciones y metadatos internos. La respuesta degradada no es HTTP 503. | ✅ funcional. `services/api/main.py` (`status`, `check_database`); `app/schemas/status.py`; `tests/test_status.py` prueba ambas ramas y ausencia de datos sensibles. |

`✅*` significa que la frontera del schema evita credenciales/campos protegidos pero no implica que la ruta sea segura: autenticación/autorización falta y la operación es 501.

**Clasificación y estado operativo (no confundir):** ✅ / ⚠️ en las 31 entradas históricas evalúan la frontera del schema y sus riesgos, no que la ruta ejecute una operación funcional. De las 32 rutas de aplicación, solo `GET /health` y `GET /status` tienen respuestas funcionales (2); las otras 30 rutas de negocio/autenticación son stubs HTTP 501. En las filas marcadas ⚠️, la recomendación indica una mejora pendiente y no una modificación ya aplicada. El inventario individual procede de `12feda2`; `/status` se añade con evidencia del código y pruebas actuales.

## Cambios y decisiones

### Integración y estado

La integración incorporó de `main` `services/api/db.py`, la dependencia de PostgreSQL y `/status`. La resolución dejó todos los routers de la rama de auditoría y las rutas operativas de main. `/health` sigue respondiendo `{"status":"ok"}`. `/status` responde `{"status":"operational"}` cuando PostgreSQL completa `SELECT 1`, o `{"status":"degraded"}` cuando falla; no expone DSN, credenciales, detalles de conexión ni excepciones. La respuesta degradada es HTTP 200 y no se declara un 503 inexistente.

Se añadió `StatusResponse` con `Literal["operational", "degraded"]`. No se alteró el acceso a base de datos más allá de conservar su helper existente y probar sus caminos de éxito y fallo.

### Dependencias reproducibles

`services/api/pyproject.toml` declara versiones fijas de FastAPI, Pydantic/email-validator, psycopg binary, Uvicorn y dependencias de pruebas HTTP/pytest/asyncio/cobertura. `services/api/uv.lock` se regeneró con uv 0.6.17, incluyendo versiones, resolución transitiva y hashes. Instalación verificada usando `uv sync --frozen --extra dev`; `uv sync --frozen --extra dev --check` no propone cambios.

### Contratos, privacidad y alcance funcional

- Todos los 32 `APIRoute` tienen un `response_model` no nulo y documentación OpenAPI con schema de respuesta. `/health` usa `HealthResponse`; `/status`, `StatusResponse`.
- `/auth/register`, `/auth/login`, `/auth/me`, recuperación/reset y endpoints de inventario, pedidos, envíos, devoluciones, clientes, usuarios y dashboard conservan los `501 Not Implemented`. No hay nuevas implementaciones de negocio. El status 201 declarado para futuros endpoints create no significa que existan respuestas exitosas hoy.
- Separación: los modelos de request (por ejemplo, `RegisterRequest`, `OrderCreateRequest`, `UserCreate`) no reutilizan el response model; los response models declaran solo campos aprobados del contrato y no contienen credenciales.
- Listados usan tipos `*Summary` con menos campos que detalles. No se cargan relaciones ORM porque no hay ORM ni repositorios. Detalles anidados están acotados por Pydantic a `OrderItemSummary`, `TrackingEvent` y tipos KPI explícitos, no entidades recursivas o crudas.
- PII declarada en detalle (contacto, dirección, notas, destinatario y tracking) permanece limitada a los esquemas ya existentes; no se afirma que sea segura para todos los roles. La autorización no existe aún y es un bloqueo para habilitar datos de negocio.

## Evidencia ejecutada

Inventario histórico de cobertura recuperado de `12feda2` y contrastado en esta
verificación: `main.py` incluye los nueve routers (`health`, `auth`, `inventory`,
`orders`, `shipments`, `returns`, `customers`, `dashboard`, `users`) más `/status`;
son **32** operaciones de aplicación (31 históricas + `/status`). FastAPI agrega
cuatro rutas de documentación (`/openapi.json`, `/docs`, `/docs/oauth2-redirect`,
`/redoc`), por lo que hay **36** rutas contando infraestructura. Las cuatro
automáticas no son endpoints de aplicación ni se les requiere `response_model`
Pydantic de negocio. En el conteo de los 32 de aplicación, **2 son funcionales**
(`/health`, `/status`) y **30 responden 501**. La UI consulta `/api/status`; no
se hallaron consumers UI de los 30 endpoints de negocio.

No se observaron rutas custom de middleware/mount/websocket, streaming ni
respuestas sin cuerpo.

Comandos ejecutados desde `services/api`:

```text
uv 0.6.17 lock
uv sync --frozen --extra dev
uv run --frozen --extra dev pytest -q --cov=app --cov=main --cov=db --cov-report=term-missing
uv run --frozen --extra dev python (assert de OpenAPI: 32 rutas, todos response_model; HealthResponse y StatusResponse)
uv sync --frozen --extra dev --check
```

`uv sync --frozen --extra dev --check` informó `Would make no changes`. La
recolección con `pytest --collect-only -q` devolvió **91 casos**; en concreto,
`test_status_endpoint_reports_database_state` produce dos nodos:
`[True-operational]` y `[False-degraded]`. La primera ejecución sin el plugin de
pytest-asyncio activo omitió corutinas (55 passed / 36 skipped), no se considera
resultado válido y no se usa para las conclusiones; la suite final se repitió con
el entorno dev frozen y plugin activo, obteniendo 91/91.

Resultados finales:

| Verificación | Resultado |
|---|---|
| pytest, suite completa incluyendo todas las pruebas async y parámetros expandidos | **91 passed, 0 failed, 0 skipped**; 91 casos recolectados |
| Cobertura (`app`, `main.py`, `db.py`) | **100% (404 statements, 0 missing)** |
| Superficie FastAPI | **32 rutas de aplicación; 32/32 con response_model** |
| OpenAPI `/health` y `/status` | **PASS**, referencia HealthResponse/StatusResponse comprobada |
| HTTP real de `/health` | **200**, JSON exacto `{"status":"ok"}` (test ASGI) |
| HTTP real `/status` con base de datos disponible/no disponible | **200**, `operational` / `degraded`; helper invocado; sin detalles sensibles |
| Serialización HTTP con datos señuelo secretos | **PASS**, response model retiró password/hash/salt/reset_token/internal_metadata |
| PostgreSQL | **PASS aislado**, test mock confirma conexión, `SELECT 1`, fila 1; fallo de conexión retorna false y no propaga excepción |
| Respuestas de negocio | **PASS**, tests verifican 501; no hay éxitos ficticios |
| Lock congelado | **PASS**, sincronización exacta sin cambios |

La comprobación HTTP se hizo contra ASGI (`httpx.ASGITransport`) y rutas de aplicación, no contra un servidor externo. La prueba de PostgreSQL usa mock y **no acredita conectividad a un servidor PostgreSQL real** en esta ejecución.

## Alcance 4Geeks: criterios y estado

| Criterio evaluable | Evidencia / estado |
|---|---|
| Leer instrucciones/contexto/auditoría y conservar trabajo local | `AGENTS.md`, `CONTEXT.md`, Memory Bank, reglas activas, READMEs y auditoría previa inspeccionados. Se conservaron cambios de auditoría y documentación existentes durante el merge. |
| Integrar `origin/main` y resolver conflictos | Integración realizada; conservación de routers feature, `/health`, `/status`, PostgreSQL y ambas entradas Memory Bank. |
| Dependencias runtime/test reproducibles | Versiones directas fijadas, lock regenerado, instalación congelada comprobada. |
| `response_model` en cada endpoint de aplicación | PASS: test runtime recorre 32 APIRoute y exige modelo; OpenAPI inspeccionado. |
| Separación request/response, campos secretos | PASS en schemas existentes y respuesta HTTP real con campos sensibles señuelo excluidos. |
| Listas ligeras y relaciones anidadas | Schemas Summary separados y modelos anidados explícitos inspeccionados. Payloads de negocio reales no observables dado 501/ausencia de storage. |
| Mantener 501 y no declarar éxito inexistente | PASS: stubs conservados y tests de 501; no se implementó negocio ni se añadieron respuestas HTTP de error ficticias. |
| pytest, OpenAPI, HTTP y exclusión sensible | PASS, 91 tests; assertions de OpenAPI y rutas HTTP ASGI descritas arriba. Los 2 escenarios parametrizados de `/status` se cuentan individualmente. |
| Documentar resultados/limitaciones/evidencia | Este documento. |
| Revisión pre-commit | **PASS**: diff completo de los cuatro archivos previstos revisado; reglas y README comprobados; suite, lock, OpenAPI y `git diff --check` pasan; Memory Bank actualizado; estado Git contiene solo `.gitignore`, esta auditoría, `memory-bank/progress.md` y eliminación de `services/api/.coverage`. No se hace merge ni despliegue. |

## Limitaciones y bloqueos funcionales

1. Las 30 rutas de negocio/auth existentes siguen devolviendo 501. Por tanto no hay payloads de éxito de negocio, serialización de ORM, autorización ni persistencia que probar; implementarlos queda fuera del alcance expreso.
2. No se conectó con PostgreSQL real. `/status` usa el helper real de conexión en producción/código, pero esta prueba automatizada reemplaza el helper por mocks; la prueba de `db.py` valida `SELECT 1` con una conexión simulada.
3. No existe autenticación/autorización. No habilitar PII de clientes, usuarios, pedidos, envíos o notas hasta definir permisos y pruebas por rol.
4. Hay datos personales/operativos y texto libre en algunos schemas de detalle; la definición de campos públicos/roles y retención no está establecida. Los contratos se preservan sin inventar política de negocio.
5. Los schemas permiten el comportamiento Pydantic por defecto para campos extra (no se ha establecido `extra="forbid"`); la decisión de rechazo estricto se aplaza por no estar acordada.
6. Las rutas framework de documentación son generadas por FastAPI, no endpoints de datos de aplicación; no se les asigna `response_model` Pydantic de negocio.

## Archivos clave del cambio de serialización

- `services/api/main.py`: routers, `/status` tipado y conexión PostgreSQL.
- `services/api/app/schemas/status.py`: respuesta operacional/degradada.
- `services/api/pyproject.toml`, `services/api/uv.lock`: dependencias directas y lock reproducible.
- `services/api/tests/test_status.py`, `test_serialization_contracts.py`, `test_db.py` y tests de schemas: OpenAPI, HTTP, exclusión de campos secretos, base de datos mock y contratos.
- `memory-bank/progress.md`: reconciliación de entradas preexistentes y progreso integrado.
