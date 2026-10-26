# Plan de telemetría — TrackFlow

> **Estado: diseño en borrador, bloqueado parcialmente.** No incluye instrumentación, endpoints ni infraestructura.
> **Bloqueo:** `empresa-BRIEFING.md` no existe en el repositorio ni en el workspace. Las métricas obligatorias del BRIEFING **no se han verificado**; este plan usa `CONTEXT.md` como contexto y marca como *núcleo candidato* (Núcleo\*) lo que sería obligatorio si el BRIEFING lo confirma.

Esquema validable: [`event-schemas.json`](./event-schemas.json) (JSON Schema 2020-12). Catálogo: **39 eventos**, cada uno con su esquema (1:1).

## 1. Punto de partida real

| Disponibilidad | Qué significa en el código actual | Ejemplos |
|---|---|---|
| Disponible hoy | El punto de disparo existe y funciona (sin instrumentar) | `GET /health`, `GET /status` (`SELECT 1`), middleware `log_request_timing`, website y backoffice Next.js, sondeo `BackendStatus` cada 15 s |
| Demo local | Funciona solo con `APP_ENV` development/test + `INVENTORY_DEMO_ENABLED` | `/inventory/items`, `/items/{sku}`, `/alerts`, `POST /inventory/movements`, `seed_inventory.py` |
| Stub 501 | Endpoint y schema Pydantic declarados, sin lógica | `/auth/*`, `/orders`, `/shipments`, `/returns`, `/customers`, `/dashboard`, `/users` |
| Futuro | Sin endpoint ni código | Ingesta de emails, agregador de tracking, tickets CX, encuestas, backups |

No hay autenticación funcional ni Supabase: `userId` será `null` hasta que exista Auth.

**Contradicciones de `CONTEXT.md` conservadas (no resueltas):**
- CEO: “Thomas Harry” (organización) frente a “Daniel Espinoza” (Dirección Ejecutiva y creación de TrackFlow Tech).
- Transportistas: “entre ellos UPS, FedEx, MRW y SEUR” frente a la lista por país (UPS, FedEx, DHL / MRW, SEUR, DHL + dos locales). Por eso `carrier` es un código validado por patrón, no un enum.
- No se indica qué almacén usa el SGA comercial y cuál la hoja de cálculo: se usan `commercial_wms` / `spreadsheet_wms`, no ciudades.

## 2. Métricas

### 2.1 Métricas obligatorias del BRIEFING

**NO VERIFICADAS — BRIEFING ausente.** No se enumeran para no inventarlas. Acción: incorporar `empresa-BRIEFING.md`, contrastar con 2.2 y reclasificar `Núcleo*` → obligatorio/adicional.

### 2.2 Métricas candidatas (de `CONTEXT.md`) → eventos → entidades reales

| Métrica candidata | Fuente | Eventos | Entidad real en el repo | ¿Medible hoy? |
|---|---|---|---|---|
| Volumen de envíos | Dirección | `shipment_created` | `ExecutiveDashboard.total_shipments`, `ShipmentDetail` | No (sin alta de envíos) |
| Tasa de entrega a tiempo | Dirección, Transportistas | `shipment_delivered.on_time` | `ExecutiveDashboard.on_time_rate`, `ShipmentDetail.estimated_delivery` | No |
| Coste operativo | Dirección | `shipment_delivered.shipping_cost` (solo transporte) | `ExecutiveDashboard.operational_cost` | No; el coste total vive en el ERP, fuera de telemetría |
| Devoluciones (tasa) | Dirección, Logística inversa | `return_requested` ÷ `shipment_delivered` | `ExecutiveDashboard.return_rate`, `ReturnRequestDetail` | No (stub 501) |
| Satisfacción del cliente | Dirección | `customer_satisfaction_submitted` | `ExecutiveDashboard.customer_satisfaction` | No; método de medición no definido |
| Clientes activos | Código (`ExecutiveDashboard.active_customers`) | `customer_id` distintos en `order_created` | `CustomerSummary.is_active` | No |
| Stock en tiempo real por SKU/almacén | Almacén | `inventory_movement_recorded` | Tablas `inventory_items`, `inventory_movements`; `InventoryItemDetail` | Solo demo local |
| Alertas de stock bajo | Almacén | `inventory_stock_low_detected` | `InventoryAlert`, `low_stock_threshold` | Solo demo local |
| Incidencias por ruta | Transportistas | `shipment_delivery_failed` | `ShipmentDetail`, `TrackingEvent` | No |
| Coste por kg | Transportistas | `shipment_delivered` (`shipping_cost`, `weight_kg`) | `ShipmentDetail.weight_kg` | No |
| % consultas resueltas sin humano | CX (80 % automatizable) | `support_ticket_resolved` | Sin entidad en código | No |
| Riesgo de renovación | Comercial | `customer_health_scored`, `customer_contract_alert_triggered` | `CustomerHealthScore` | No (stub 501) |
| Disponibilidad y errores de API | Tecnología | `service_status_changed`, `api_request_failed`, `api_request_completed` | `/status` (`StatusResponse`), middleware de timing | Sí, disparo existe; falta emitir |

## 3. Resumen del catálogo

| Categoría | Eventos | Núcleo* | Adicional | Disponible hoy | Demo local | Stub 501 | Futuro | stream | batch |
|---|---|---|---|---|---|---|---|---|---|
| Inventario | 5 | 2 | 3 | 0 | 4 | 0 | 1 | 2 | 3 |
| Órdenes | 3 | 1 | 2 | 0 | 0 | 2 | 1 | 2 | 1 |
| Envíos | 7 | 3 | 4 | 0 | 0 | 2 | 5 | 4 | 3 |
| Devoluciones | 4 | 2 | 2 | 0 | 0 | 3 | 1 | 2 | 2 |
| Clientes | 5 | 1 | 4 | 0 | 0 | 1 | 4 | 0 | 5 |
| Autenticación | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 1 | 2 |
| Navegación | 3 | 0 | 3 | 2 | 0 | 1 | 0 | 0 | 3 |
| Errores | 3 | 1 | 2 | 2 | 0 | 0 | 1 | 3 | 0 |
| Rendimiento | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| Procesos internos | 4 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 3 |
| **Total** | **39** | **11** | **28** | **7** | **5** | **13** | **14** | **15** | **24** |

- **Núcleo candidato (obligatorio no verificado) (11):** `inventory_movement_recorded`, `inventory_stock_low_detected`, `order_created`, `shipment_created`, `shipment_delivered`, `shipment_delivery_failed`, `return_requested`, `return_decided`, `customer_satisfaction_submitted`, `api_request_failed`, `service_status_changed`.
- **Adicionales (28):** `inventory_movement_rejected`, `inventory_items_viewed`, `inventory_discrepancy_detected`, `order_status_changed`, `order_ingested`, `shipment_status_updated`, `shipment_tracking_viewed`, `carrier_recommendation_requested`, `carrier_selected`, `return_inspected`, `return_pickup_scheduled`, `customer_health_scored`, `customer_contract_alert_triggered`, `support_ticket_created`, `support_ticket_resolved`, `auth_login_succeeded`, `auth_login_failed`, `auth_password_reset_completed`, `page_viewed`, `cta_clicked`, `dashboard_viewed`, `frontend_error_occurred`, `integration_call_failed`, `api_request_completed`, `web_vitals_measured`, `report_weekly_generated`, `inventory_seed_executed`, `backup_completed`.
- **Futuros (sin endpoint o con stub 501) (27):** `inventory_discrepancy_detected`, `order_created`, `order_status_changed`, `order_ingested`, `shipment_created`, `shipment_status_updated`, `shipment_delivered`, `shipment_delivery_failed`, `shipment_tracking_viewed`, `carrier_recommendation_requested`, `carrier_selected`, `return_requested`, `return_decided`, `return_inspected`, `return_pickup_scheduled`, `customer_health_scored`, `customer_contract_alert_triggered`, `customer_satisfaction_submitted`, `support_ticket_created`, `support_ticket_resolved`, `auth_login_succeeded`, `auth_login_failed`, `auth_password_reset_completed`, `dashboard_viewed`, `integration_call_failed`, `report_weekly_generated`, `backup_completed`.
- **Con disparador disponible hoy (incluida demo local) (12):** `inventory_movement_recorded`, `inventory_movement_rejected`, `inventory_stock_low_detected`, `inventory_items_viewed`, `page_viewed`, `cta_clicked`, `api_request_failed`, `frontend_error_occurred`, `api_request_completed`, `web_vitals_measured`, `service_status_changed`, `inventory_seed_executed`.

\* Núcleo = candidato a obligatorio derivado de `CONTEXT.md`; pendiente del BRIEFING.

## 4. Catálogo de eventos

Prioridad: **P0** alimenta un KPI o una alerta crítica; **P1** decisión operativa; **P2** optimización/UX.

### Inventario (5)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `inventory_movement_recorded` | backend · `POST /inventory/movements` → 201 | Un stock unificado por SKU/almacén reduce discrepancias detectadas tarde. → **Reponer o reasignar stock entre almacenes.** | `sku`*, `warehouse`*, `quantity_delta`*, `quantity_after`* | Sin datos personales. | P0 | Núcleo* | Demo local | `stream` |
| `inventory_movement_rejected` | backend · `POST /inventory/movements` → 404/409/422 | Rechazos repetidos revelan maestros de SKU erróneos o stock desincronizado. → **Corregir maestros o auditar el almacén.** | `sku`, `warehouse`, `rejection_reason`*, `status_code`* | Sin datos personales. | P2 | Adicional | Demo local | `batch` |
| `inventory_stock_low_detected` | backend · Movimiento deja `quantity_after` ≤ `low_stock_threshold` (hoy solo se calcula en `GET /inventory/alerts`) | Avisar al cruzar el umbral evita roturas de stock. → **Notificar a cliente y compras; priorizar reposición.** | `sku`*, `warehouse`*, `current_quantity`*, `threshold`* | Sin datos personales. | P0 | Núcleo* | Demo local | `stream` |
| `inventory_items_viewed` | backend · `GET /inventory/items` → 200 | Consultas frecuentes demuestran demanda del dashboard de almacén. → **Priorizar el dashboard y ajustar el TTL de 30 s.** | `warehouse`, `has_text_query`, `result_count`*, `cache_status`* | Sin `q` en claro; solo booleano. | P2 | Adicional | Demo local | `batch` |
| `inventory_discrepancy_detected` | job · Conciliación SGA comercial / hoja de cálculo vs. stock TrackFlow | Las discrepancias se concentran en ciertos SKU/almacén. → **Programar recuentos cíclicos dirigidos.** | `sku`*, `warehouse`*, `system_quantity`*, `counted_quantity`*, `source_system`* | Sin datos personales. | P1 | Adicional | Futuro | `batch` |

### Órdenes (3)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `order_created` | backend · `POST /orders` → 201 | El volumen por cliente y país anticipa la carga de almacén. → **Dimensionar turnos de picking por almacén.** | `order_id`*, `customer_id`*, `item_count`*, `total_units`, `ingestion_channel`*, `destination_country` | Excluye `shipping_address` y `notes`; solo país derivado. | P0 | Núcleo* | Stub 501 | `stream` |
| `order_status_changed` | backend · `PATCH /orders/{order_id}/status` | El cuello de botella está en transiciones concretas. → **Reasignar operarios a la fase lenta.** | `order_id`*, `from_status`*, `to_status`*, `seconds_in_previous_status` | Sin datos personales. | P1 | Adicional | Stub 501 | `stream` |
| `order_ingested` | pipeline · Pipeline de ingesta procesa un email de pedido | Parsear emails elimina la transcripción manual. → **Qué formatos priorizar; cuándo retirar la transcripción.** | `customer_id`*, `order_id`, `parse_status`*, `attachment_type`*, `item_count` | Nunca remitente, asunto ni cuerpo. | P1 | Adicional | Futuro | `batch` |

### Envíos (7)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `shipment_created` | backend · Asignación de transportista y etiqueta (no existe `POST /shipments`) | El volumen de envíos por país/transportista es el KPI base de dirección. → **Negociar capacidad y tarifas.** | `shipment_id`*, `order_id`*, `carrier`*, `origin_warehouse`*, `destination_country`*, `weight_kg`*, `urgency`, `promised_delivery_date` | Excluye `recipient`, `destination` y `tracking_number`. | P0 | Núcleo* | Futuro | `stream` |
| `shipment_status_updated` | integration · Agregador de tracking recibe un cambio de estado | Unificar 8 APIs elimina la consulta manual de portales. → **Webhook vs. polling por transportista.** | `shipment_id`*, `carrier`*, `status`*, `update_source`* | Sin `location` ni `description` libres. | P1 | Adicional | Futuro | `stream` |
| `shipment_delivered` | integration · Estado entregado normalizado | La entrega a tiempo varía por transportista y ruta. → **Reponderar la selección; revisar contratos.** | `shipment_id`*, `carrier`*, `destination_country`*, `on_time`*, `transit_hours`*, `weight_kg`, `shipping_cost`, `currency` | Sin datos personales. | P0 | Núcleo* | Futuro | `stream` |
| `shipment_delivery_failed` | integration · Incidencia de entrega del transportista | Las incidencias se concentran por ruta/transportista. → **Escalar a CX o cambiar transportista en la ruta.** | `shipment_id`*, `carrier`*, `destination_country`*, `failure_reason`*, `attempt_number` | Sin datos personales. | P0 | Núcleo* | Futuro | `stream` |
| `shipment_tracking_viewed` | backend · `GET /shipments/tracking/{tracking_number}` | Muchas consultas a CX son "¿dónde está mi paquete?". → **Dimensionar portal público y agente de CX.** | `lookup_result`*, `channel`*, `carrier` | Nunca `tracking_number`. | P2 | Adicional | Stub 501 | `batch` |
| `carrier_recommendation_requested` | backend · `POST /shipments/carrier-recommendation` | Una recomendación explicable puede sustituir la asignación manual. → **Ajustar el modelo de selección.** | `destination_country`*, `weight_kg`*, `urgency`*, `candidates_count`*, `recommended_carrier`, `confidence_score` | `destination` libre → solo país. | P1 | Adicional | Stub 501 | `batch` |
| `carrier_selected` | backoffice · Coordinador confirma transportista | Alta aceptación de la recomendación permite automatizar. → **Automatizar o no la asignación.** | `shipment_id`*, `selected_carrier`*, `recommended_carrier`, `accepted_recommendation`* | `userId` seudónimo. | P1 | Adicional | Futuro | `batch` |

### Devoluciones (4)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `return_requested` | backend · `POST /returns` → 201 | Las devoluciones (18-25 %) se concentran por SKU/cliente/motivo. → **Reglas de aprobación por cliente; feedback a marcas.** | `return_id`*, `order_id`*, `customer_id`, `sku`*, `quantity`*, `reason_code`* | `reason` libre excluido; solo código. | P0 | Núcleo* | Stub 501 | `stream` |
| `return_decided` | backend · `POST /returns/{return_id}/approve` | Muchas decisiones manuales son repetibles. → **Qué reglas automatizar por cliente.** | `return_id`*, `approved`*, `decision_mode`*, `hours_to_decision` | `notes` excluido. | P0 | Núcleo* | Stub 501 | `stream` |
| `return_inspected` | backend · `POST /returns/{return_id}/inspect` | La inspección es subjetiva; la IA puede homogeneizarla. → **Validar el clasificador; reacondicionar o desechar.** | `return_id`*, `sku`*, `condition`*, `inspection_mode`*, `ai_suggested_condition`, `operator_overrode_ai` | Sin fotos ni `notes`. | P1 | Adicional | Stub 501 | `batch` |
| `return_pickup_scheduled` | backend · Flujo aprobación → etiqueta → recogida | Automatizar la recogida acorta el ciclo. → **Medir y reducir el tiempo hasta recogida.** | `return_id`*, `carrier`*, `hours_since_approval`* | Sin datos personales. | P2 | Adicional | Futuro | `batch` |

### Clientes (5)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `customer_health_scored` | job · Cálculo de salud (`GET /customers/{customer_id}/health`) | El riesgo de no renovar depende de la calidad de servicio. → **Priorizar acciones de account management.** | `customer_id`*, `health_score`*, `risk_level`*, `days_to_contract_end` | Sin contactos de la marca. | P1 | Adicional | Stub 501 | `batch` |
| `customer_contract_alert_triggered` | job · 90 y 30 días antes del vencimiento | Avisar con antelación mejora la renovación. → **Planificar la renovación por cuenta.** | `customer_id`*, `days_before_expiry`*, `risk_level` | Sin datos personales. | P1 | Adicional | Futuro | `batch` |
| `customer_satisfaction_submitted` | frontend · Encuesta tras entrega, devolución o ticket (método no definido en CONTEXT) | La satisfacción cae con retrasos e incidencias. → **KPI ejecutivo; detectar clientes frustrados.** | `score`*, `segment`*, `context`*, `customer_id`, `country` | Sin comentario libre; B2C sin identificador. | P0 | Núcleo* | Futuro | `batch` |
| `support_ticket_created` | backend · Ticket desde email, WhatsApp o teléfono | El 80 % de las consultas podría automatizarse. → **Qué temas automatiza primero el agente de CX.** | `ticket_id`*, `segment`*, `channel`*, `topic`*, `language` | Sin texto del mensaje ni teléfono/email. | P1 | Adicional | Futuro | `batch` |
| `support_ticket_resolved` | backend · Cierre de ticket | El agente de IA resuelve sin escalar consultas repetitivas. → **Ampliar o limitar el agente; dimensionar el equipo.** | `ticket_id`*, `resolution_mode`*, `first_response_minutes`, `resolution_minutes`*, `escalated` | Sin datos personales. | P1 | Adicional | Futuro | `batch` |

### Autenticación (3)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `auth_login_succeeded` | backend · `POST /auth/login` → 200 | La adopción del backoffice varía por área. → **Qué áreas formar o priorizar.** | `method`* | Sin email; `userId` seudónimo. | P2 | Adicional | Stub 501 | `batch` |
| `auth_login_failed` | backend · `POST /auth/login` → 401/422 | Ráfagas de fallos indican fuerza bruta o mala UX. → **Limitar intentos o mejorar el flujo.** | `failure_reason`*, `consecutive_failures` | `userId` null; sin email ni IP en claro. | P1 | Adicional | Stub 501 | `stream` |
| `auth_password_reset_completed` | backend · `POST /auth/password-reset` | Tokens caducados/inválidos frecuentes indican fricción o abuso. → **Ajustar caducidad del token o el flujo.** | `outcome`* | Nunca token ni contraseña. | P2 | Adicional | Stub 501 | `batch` |

### Navegación (3)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `page_viewed` | frontend · Carga de ruta en website o backoffice | Solo algunas secciones del backoffice se usan. → **Priorizar funcionalidades.** | `app`*, `route_template`*, `referrer_type`, `viewport_class`*, `locale` | Sin URL completa, query ni IP. | P2 | Adicional | Disponible hoy | `batch` |
| `cta_clicked` | frontend · Clic en CTA del website (cabecera, hero, servicios, red, contacto) | Algunos mensajes generan más interés comercial. → **Ajustar copy; decidir formulario de contacto (hoy solo anclas).** | `cta_id`*, `target_anchor`*, `viewport_class` | Sin datos personales. | P2 | Adicional | Disponible hoy | `batch` |
| `dashboard_viewed` | frontend · Apertura de un dashboard (`GET /dashboard/executive`) | Si dirección usa el dashboard, sobra el informe manual de los domingos. → **Retirar el informe manual.** | `dashboard`*, `country_filter`, `data_age_minutes` | `userId` seudónimo. | P1 | Adicional | Stub 501 | `batch` |

### Errores (3)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `api_request_failed` | backend · Middleware HTTP: status ≥ 500 o excepción | Hoy los fallos se conocen por WhatsApp. → **Alertar y abrir incidente automáticamente.** | `method`*, `route_template`*, `status_code`*, `error_class`, `duration_ms`* | Sin payload, params ni mensaje de excepción. | P0 | Núcleo* | Disponible hoy | `stream` |
| `frontend_error_occurred` | frontend · Excepción JS, rechazo no gestionado o fetch fallido (p. ej. `BackendStatus` → `/api/status`) | Hay errores de cliente invisibles para backend. → **Priorizar correcciones por impacto.** | `app`*, `route_template`*, `error_kind`*, `http_status`, `error_fingerprint`* | Sin mensaje ni stack crudos; solo hash. | P1 | Adicional | Disponible hoy | `stream` |
| `integration_call_failed` | integration · Fallo al llamar APIs de transportistas, SGA, ERP o buzón | Las integraciones no documentadas fallan en silencio. → **Priorizar reescritura y reintentos.** | `integration`*, `carrier`, `error_kind`*, `retryable`* | Sin credenciales ni cuerpos de respuesta. | P1 | Adicional | Futuro | `stream` |

### Rendimiento (2)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `api_request_completed` | backend · Middleware `log_request_timing` (hoy solo log local) | La latencia por plantilla de ruta detecta regresiones. → **Definir SLO; optimizar o cachear endpoints.** | `method`*, `route_template`*, `status_code`*, `duration_ms`* | Igual que el log actual: sin URL raw. | P1 | Adicional | Disponible hoy | `batch` |
| `web_vitals_measured` | frontend · Web Vitals al cargar o abandonar página | Lighthouse de laboratorio no refleja usuarios reales. → **Priorizar optimizaciones frontend.** | `app`*, `route_template`*, `metric`*, `value`*, `rating`*, `viewport_class` | Sin datos personales. | P2 | Adicional | Disponible hoy | `batch` |

### Procesos internos (4)

| `event_type` | Origen · disparador | Hipótesis → decisión | Propiedades (* requerida) | Privacidad | Prio | Tier | Disp. | Modo |
|---|---|---|---|---|---|---|---|---|
| `service_status_changed` | backend · `/status` cambia entre `operational` y `degraded` (`SELECT 1`) | La caída de BD se detecta antes que operaciones. → **Disparar alerta e incidente.** | `service`*, `dependency`*, `previous_status`*, `current_status`* | Nunca DSN ni credenciales. | P0 | Núcleo* | Disponible hoy | `stream` |
| `report_weekly_generated` | job · Informe semanal, lunes 07:00 (`GET /dashboard/weekly-report`) | Automatizar ahorra 3-4 h por director. → **Retirar la consolidación manual.** | `week`*, `outcome`*, `duration_ms`, `data_freshness_hours` | Sin datos personales. | P1 | Adicional | Stub 501 | `batch` |
| `inventory_seed_executed` | job · `seed_inventory.py` (solo BD local `trackflow`) | La demo es reproducible e idempotente. → **Detectar seeds fallidos antes de una demo.** | `items_upserted`, `movements_inserted`, `outcome`* | Datos sintéticos. | P2 | Adicional | Demo local | `batch` |
| `backup_completed` | job · Backup programado de PostgreSQL | Hoy no hay evidencia de backups. → **Alertar si falta un backup; probar restauración.** | `target`*, `outcome`*, `duration_ms`, `size_mb` | Sin datos personales. | P1 | Adicional | Futuro | `batch` |


## 5. Event Envelope

Todos los eventos comparten el sobre; `properties` solo admite la allowlist de su `event_type` (`additionalProperties: false`).

| Campo | Tipo | Regla |
|---|---|---|
| `eventId` | UUID | Generado en origen una vez; se reutiliza en reintentos. Clave de deduplicación. |
| `timestamp` | string ISO 8601 UTC | Momento del hecho en origen, con `Z` (p. ej. `2026-10-26T09:15:02.120Z`). |
| `sessionId` | UUID \| null | Aleatorio por sesión de navegador, rota tras 30 min de inactividad; `null` en jobs/integraciones. |
| `userId` | `usr_` + 32 hex \| null | Seudónimo HMAC-SHA256 del ID interno; `null` sin usuario autenticado (hoy siempre). |
| `event_type` | string `entidad_acción` | `snake_case`, acción en participio (`order_created`); enum cerrado. |
| `schemaVersion` | semver | Versión del esquema de `properties`; hoy `1.0.0`. Cambio incompatible → mayor. |
| `requestId` | UUID \| null | Correlación frontend/backend (ver §7); en jobs, ID de ejecución; `null` solo en eventos de UI sin petición. |
| `properties` | object | Allowlist por evento. |

```json
{
  "eventId": "6f1c2a3e-8b4d-4c1e-9f2a-1b2c3d4e5f60",
  "timestamp": "2026-10-26T09:15:02.120Z",
  "sessionId": "0b8e7d6c-5a4b-4c3d-8e2f-1a0b9c8d7e6f",
  "userId": null,
  "event_type": "inventory_movement_recorded",
  "schemaVersion": "1.0.0",
  "requestId": "3d2c1b0a-9f8e-4d7c-a6b5-4c3d2e1f0a9b",
  "properties": { "sku": "DEMO-BOX-001", "warehouse": "zaragoza", "quantity_delta": -3, "quantity_after": 5 }
}
```

## 6. Estrategia `stream` / `batch`

| Modo | Criterio | Latencia | Coste |
|---|---|---|---|
| `stream` | El evento dispara una acción (alerta, incidencia, escalado) o alimenta un panel operativo que pierde valor en minutos | < 1 min | Consumidor permanente; justificado solo con volumen moderado y decisión inmediata |
| `batch` | Tendencias, adopción, calidad de modelos, rendimiento agregado; volumen alto o valor solo agregado | Micro-lotes de 15 min (UI: buffer + envío al ocultar la página) o diario en jobs | Compresión y escritura por lotes; sin consumidor 24/7 |

Casos límite: `api_request_failed` va en `stream` (alerta) y `api_request_completed` en `batch` (percentiles); una petición 5xx emite ambos con el mismo `requestId` y distinto `eventId`. `return_requested`/`return_decided` van en `stream` porque abren o cierran un flujo con SLA; `return_inspected` en `batch` porque se analiza agregado. `customer_satisfaction_submitted` es Núcleo\* pero `batch`: el KPI ejecutivo no cambia minuto a minuto.

## 7. Deduplicación, correlación, retención y privacidad

**Deduplicación por `eventId`.** El productor crea el UUID al generar el evento, lo guarda en su buffer y lo reutiliza en cada reintento. La ingesta hace *upsert* idempotente con `eventId` como clave única y descarta duplicados. Para hechos externos reenviados (webhooks de transportista), `eventId` = UUIDv5 determinista de `carrier` + ID del evento del transportista, de modo que el reenvío no duplica.

**Correlación frontend/backend por `requestId`.** El frontend genera un UUID por llamada HTTP y lo envía en `X-Request-Id`; el rewrite `/api/*` de Next.js debe propagarlo; el middleware FastAPI lo valida (o genera uno si falta/es inválido), lo devuelve en la respuesta y lo añade a todos los eventos y logs de esa petición. Un `frontend_error_occurred` por `fetch_failed` lleva el mismo `requestId` que el `api_request_failed` del backend. Hoy el middleware no maneja `requestId`: es un hueco a cubrir en la implementación.

**Retención (propuesta, pendiente de validación de negocio y legal en EE. UU. y España):**

| Datos | Retención |
|---|---|
| Eventos crudos de errores y rendimiento | 30 días |
| Resto de eventos crudos (con `userId`/`sessionId`) | 90 días |
| Agregados de KPI por día/país/transportista/cliente, sin `userId`/`sessionId` | 25 meses (comparativa interanual) |

**Controles de privacidad y anonimización:**
1. Allowlist estricta: la ingesta rechaza propiedades no declaradas (`additionalProperties: false`).
2. Nombres prohibidos (`x-privacy.forbiddenPropertyNames`): email, contraseñas, tokens, nombres, teléfonos, direcciones, `recipient`, `tracking_number`, notas, texto libre, IP, user agent, URL y `q`.
3. Seudonimización: `userId` = HMAC con secreto rotado anualmente fuera del repositorio; sin él no se revierte.
4. Generalización: direcciones → país ISO; motivos libres → códigos; errores → fingerprint hash, nunca mensaje/stack.
5. IDs internos (`order_id`, `shipment_id`, `return_id`, `customer_id`, `ticket_id`) permitidos para reconstruir el embudo; los datos personales quedan en la base operativa con su control de acceso.
6. `auth_login_failed` lleva `userId: null` para no revelar si una cuenta existe.
7. Separación de entornos por destino de ingesta: los eventos de demo local nunca se mezclan con producción.

## 8. Validación del diseño

Comprobado con `jsonschema` (Draft 2020-12): el esquema es válido; catálogo Markdown y `$defs.events` coinciden 1:1 con el enum de `event_type`; todos los nombres cumplen `^[a-z]+(_[a-z]+)+$`; cada evento declara `required` ⊆ `properties` y `additionalProperties: false`; ninguna propiedad usa un nombre prohibido; categoría, tier, disponibilidad y modo coinciden entre Markdown y JSON; el ejemplo de §5 valida y una propiedad no permitida es rechazada.

## 9. Limitaciones

- Métricas obligatorias del BRIEFING no verificadas (bloqueo).
- 27 de 39 eventos dependen de funcionalidades stub o futuras; los KPI ejecutivos no son medibles hoy.
- Estados de pedido/envío sin enum en el código: se valida formato, no valores.
- El sobre solicitado no incluye `environment` ni `source`: se resuelven por destino de ingesta y por el catálogo.
- Retención y seudonimización son propuestas sin validación legal.
