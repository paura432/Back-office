# trackflow-incident-domain.md

> Regla derivada del contexto oficial de TrackFlow y del contexto funcional del Incident Manager.
> Define los catálogos, campos y reglas de negocio del dominio de incidencias. Los valores son cerrados y no extensibles sin decisión explícita.

---

- **Aplicación:** `always_active`
- **Ámbito/patrón de archivos:** `packages/shared/types/incident.ts`, `services/api/routers/incidents.py`, `services/api/schemas/incident.py`, `services/api/models/incident.py`, `uis/backoffice/src/**/*.ts`, `data/raw/incidents_seed.json`, `data/pipelines/seed_incidents.py`

## Evidencia de origen

- `docs/incident-manager/reconnaissance.md` — Sección 5 "Contexto funcional del Incident Manager" extraída del contexto oficial externo `4GeeksAcademy/ai-engineering-syllabus/content/contexts/4-devs/incident-manager-for-devs/CONTEXT-trackflow.es.md`.
- `CONTEXT.md` — Briefing de TrackFlow que confirma la existencia de los departamentos, almacenes y operaciones que justifican estos catálogos.

## Qué se debe hacer

### Catálogos obligatorios (cerrados)

**Canales:**
```
carrier_portal_alert | client_email | wms_alert | warehouse_call | dashboard
```

**Tipos de incidencia:**
```
lost_parcel | inventory_discrepancy | carrier_failure | system_outage | return_dispute | sla_breach
```

**Severidades:**
```
critical | high | medium | low
```

**Áreas responsables:**
```
warehouse_operations | last_mile_carrier | reverse_logistics | customer_experience | commercial | technology
```

**Estados y transiciones:**
```
open → assigned → in_progress → resolved → closed
reopened  (desde resolved)
```

### Campos mínimos del modelo

| Campo | Tipo | Detalle |
|---|---|---|
| `warehouse_location` | `"los_angeles" \| "zaragoza" \| null` | Opcional |
| `client_name` | `string \| null` | Opcional |
| `channel` | enum canales | Obligatorio |
| `type` | enum tipos | Obligatorio |
| `severity` | enum severidades | Obligatorio |
| `responsible_area` | enum áreas | Obligatorio |
| `title` | `string` | Obligatorio |
| `description` | `string` | Obligatorio |
| `status` | enum estados | Obligatorio |
| `assigned_to` | `string \| null` | Opcional |
| `created_at` | `datetime` | Obligatorio |
| `updated_at` | `datetime` | Obligatorio |

### Reglas de negocio

1. **Grafo de estados:** Las transiciones válidas son `open → assigned → in_progress → resolved → closed`. `reopened` solo puede activarse desde `resolved`.
2. **Severidad critical:** Una incidencia `critical` no puede transicionar directamente a `closed`. Debe pasar por `resolved` primero.
3. **Auditoría obligatoria:** Cada cambio de `status`, `assigned_to` o `responsible_area` debe registrar un *timestamp* y el *autor* del cambio.
4. **Responsible_area dinámico:** Puede cambiar en cualquier momento. El cambio queda auditado (misma regla que punto 3).
5. **Cobertura de datos semilla:** Mínimo 12 incidencias semilla con: las 4 severidades, ambos almacenes (`los_angeles`, `zaragoza`), al menos 4 canales distintos, al menos 1 incidencia `reopened`, y al menos 1 incidencia con `client_name = null`.

## Qué NO se debe hacer

- ❌ Usar un valor de canal, tipo, severidad o área que no esté en los catálogos cerrados anteriores. Ejemplo prohibido: `severity = "urgent"`, `channel = "sms"`, `type = "fraud"`.
- ❌ Permitir transiciones de estado no definidas en el grafo. Ejemplo prohibido: `open → closed` directamente.
- ❌ Saltarse la regla de critical: permitir `critical → closed` sin pasar por `resolved`.
- ❌ Omitir la auditoría en cambios de estado, asignación o área responsable.
- ❌ Cambiar `warehouse_location` a un valor que no sea `los_angeles`, `zaragoza` o `null`.
- ❌ Inventar nuevos campos obligatorios sin documentarlos y sin justificación en el dominio.

## Cómo verificar su cumplimiento

- Los enums/tipos en `packages/shared/types/incident.ts` deben coincidir exactamente con los catálogos.
- Los schemas Pydantic en `services/api/schemas/` deben validar contra los mismos catálogos.
- El endpoint de transición de estado debe rechazar transiciones no válidas con error 422.
- El endpoint de transición para incidencias `critical` debe rechazar `critical → closed` sin paso intermedio por `resolved`.
- La tabla de auditoría (o estructura equivalente) debe existir y poblarse en cada cambio de `status`, `assigned_to` o `responsible_area`.
- El dataset semilla debe tener exactamente 12+ registros que cumplan la cobertura especificada.