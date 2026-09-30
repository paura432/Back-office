# Product — TrackFlow Incident Manager

## Qué es TrackFlow

TrackFlow es una empresa de logística de última milla y gestión de almacenes fundada en 2009 en Los Ángeles, EE.UU. Opera en dos mercados (EE.UU. y España) con almacenes en **Los Ángeles** y **Zaragoza**. ~130 empleados, ~9M€ anuales.

## Quién usa el backoffice

Operarios de almacén, coordinadores logísticos, atención al cliente, responsables de área y dirección ejecutiva de TrackFlow. El backoffice es interno, no público.

## Problema que resuelve el Incident Manager

Hoy, cuando algo falla en la operación (paquete perdido, discrepancia de inventario, caída de sistema, etc.), el equipo de tecnología se entera por WhatsApp. No hay un sistema unificado para crear, seguir, asignar y resolver incidencias. El Incident Manager centraliza el registro, trazabilidad y resolución de incidencias logísticas.

## Significado operativo de severidades

- **critical** — SLA de cara al cliente incumplido o un almacén no operativo. No puede cerrarse sin pasar por `resolved`.
- **high** — riesgo significativo para volumen de envío o plazo de un cliente.
- **medium** — impacto notable pero contenido.
- **low** — sin impacto operativo inmediato.

## Catálogos exactos (del CONTEXT)

- **Canales:** `carrier_portal_alert`, `client_email`, `wms_alert`, `warehouse_call`, `dashboard`
- **Tipos:** `lost_parcel`, `inventory_discrepancy`, `carrier_failure`, `system_outage`, `return_dispute`, `sla_breach`
- **Severidades:** `critical`, `high`, `medium`, `low`
- **Áreas:** `warehouse_operations`, `last_mile_carrier`, `reverse_logistics`, `customer_experience`, `commercial`, `technology`
- **Estados:** `open → assigned → in_progress → resolved → closed`, con `reopened` desde `resolved`

## Trazabilidad: requisito no negociable

Cada cambio de `status`, `assigned_to` y `responsible_area` debe guardar **timestamp + autor**. El `responsible_area` puede cambiar después de la creación y debe quedar auditado. No hay excepción.