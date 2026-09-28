# Reconocimiento — TrackFlow Incident Manager

> Documento de reconocimiento del monorepo antes de comenzar la implementación.
> Fase 1: solo lectura e inspección. No se ha modificado ni creado funcionalidad.

---

## 1. Resumen inicial del agente

Hipótesis inicial sobre arquitectura, stack y convenciones del monorepo:

- **Monorepo multi-lenguaje** con JS/TS (pnpm + Corepack) y Python (uv + pip). El devcontainer instala ambos entornos.
- **Backend centralizado**: FastAPI en `services/` como único backend oficial, según README. Sin microservicios.
- **Frontend separado por audiencia**: `uis/website` (público) + `uis/backoffice` (interno). Stack sin decidir.
- **Tipos compartidos**: `packages/shared/` con `@repo/shared-types` (TypeScript). Ya existe `BaseEntity` como interfaz base.
- **Agentes Python**: `agents/` con `_template/agent.py` vacío. `uv sync` sugiere proyectos Python.
- **Infra sin definir**: `infra/` vacío. No hay `docker-compose.yml` en raíz (documentado como deseable pero ausente).
- **Convenciones implícitas**:
  - Linting/formato: Prettier + ESLint como extensiones VS Code. Sin archivos de configuración propios.
  - Formato al guardar (`editor.formatOnSave: true`).
  - Python con `uv` como gestor de dependencias.
  - Sin `pyproject.toml`, `requirements.txt`, ni `tsconfig.json` en ningún nivel.
  - Sin tests automatizados implementados (solo README de tests en la plantilla de agente).

---

## 2. Contraste con el repositorio real

| Elemento | Estado real | Detalle |
|---|---|---|
| `uis/` | Solo READMEs | Sin `website/` ni `backoffice/` |
| `services/` | Solo READMEs | Sin API, routers ni workers |
| `packages/shared/` | ✅ `package.json` + `types/index.ts` | `@repo/shared-types v0.0.1` con `BaseEntity` e `Id` |
| `agents/` | Solo estructura de directorios | `_template/agent.py` vacío. `tools/` solo README |
| `data/raw/`, `data/pipelines/`, `data/process/`, `data/eval/` | Solo READMEs | Sin datos ni scripts |
| `skills/` | Parcial | `data-analysis/` con `pandas_clean.py` y `common_metrics.md`. Otras skills vacías |
| `mcps/` | Solo READMEs | Sin servidores MCP |
| `workflows/` | Solo READMEs | Sin flujos |
| `docs/` | Solo READMEs | Sin ADRs, diagramas ni documentación técnica |
| `infra/` | Solo READMEs | Sin Dockerfiles, Terraform ni manifests |
| `scripts/` | Solo READMEs | Sin scripts utilitarios |
| `internal/` | Solo READMEs | Sin CLIs internas |
| `shared/` (raíz) | Solo READMEs | Sin schemas, plantillas ni assets |
| `CONTEXT.md` | ✅ Contenido real de TrackFlow | Documento interno detallado de la empresa |
| `CONTEXT.es.md` | ❌ Placeholder genérico | Dice "Sustituye este archivo por el CONTEXT de tu empresa" |
| `.devcontainer/` | ✅ `devcontainer.json` + `post-create.sh` | Python, uv, pnpm, extensiones VS Code |
| `.gitignore` | ✅ Vacío | Sin reglas definidas |
| `docker-compose.yml` | ❌ No existe | Solo mencionado en README |
| Tests automatizados | ❌ No existen | Solo README de tests en `agents/_template/tests/` |
| Linters configurados | ❌ Sin archivos de configuración | ESLint y Prettier como extensiones, sin `.eslintrc` ni `.prettierrc` |

---

## 3. Discrepancias detectadas

| Discrepancia | Evidencia | Impacto |
|---|---|---|
| **API FastAPI documentada pero no implementada** | `services/README.md` describe FastAPI centralizado; `services/` solo contiene READMEs | El backend del Incident Manager debe crearse desde cero |
| **Backoffice documentado pero no implementado** | `uis/README.md` describe `backoffice/` como aplicación admin; `uis/` solo contiene READMEs | La UI del dashboard de incidencias debe crearse desde cero |
| **docker-compose.yml mencionado pero ausente** | README raíz (tabla + sección "Keep at repo root") referencia `docker-compose.yml`; no existe en el directorio raíz | La orquestación local no está definida. Se creará cuando haya servicios que orquestar |
| **CONTEXT.md contiene TrackFlow pero CONTEXT.es.md sigue siendo placeholder** | `CONTEXT.md` tiene el briefing completo de TrackFlow; `CONTEXT.es.md` dice "Sustituye este archivo por el CONTEXT de tu empresa" | Inconsistencia entre idiomas. El contexto español debería reflejar el mismo contenido |
| **`packages/shared/package.json` declara `"main": "index.ts"` pero el código está en `types/index.ts`** | `package.json` apunta a `index.ts`; el archivo real existente es `types/index.ts` | Discrepancia en la declaración del punto de entrada del paquete |
| **Sin `.gitignore` poblado** | `.gitignore` existe pero está vacío | Archivos temporales, dependencias y artefactos no están excluidos del control de versiones |

---

## 4. Convenciones existentes

Cada convención está respaldada por evidencia en el repositorio.

| # | Convención | Evidencia (ruta) | Descripción |
|---|---|---|---|
| C1 | **Monorepo con carpetas por responsabilidad única** | `README.md` (tabla "How to think about this monorepo") | 13 directorios raíz con responsabilidad explícita y no solapada |
| C2 | **Backend centralizado FastAPI en `services/`** | `services/README.md` | "One centralized FastAPI backend for the whole company" |
| C3 | **Tipos compartidos TypeScript en `packages/shared/` como `@repo/shared-types`** | `packages/shared/package.json` + `packages/shared/types/index.ts` | Package `@repo/shared-types`. Interfaz `BaseEntity` e `Id` |
| C4 | **Python vía `uv` para gestión de dependencias** | `.devcontainer/post-create.sh` | `python -m pip install --upgrade pip uv` + `uv sync` |
| C5 | **JS/TS vía `pnpm` (Corepack)** | `.devcontainer/post-create.sh` | `corepack enable && corepack prepare pnpm@latest --activate` |
| C6 | **Editor: formato al guardar + Prettier + ESLint** | `.devcontainer/devcontainer.json` | `editor.formatOnSave: true`, extensiones `esbenp.prettier-vscode`, `dbaeumer.vscode-eslint` |
| C7 | **Python como lenguaje principal del proyecto** | `.devcontainer/devcontainer.json` | Extensiones `ms-python.python`, `ms-python.vscode-pylance`. Intérprete `/usr/local/python/current/bin/python` |
| C8 | **Agentes: un subdirectorio por agente, heredan de `_template/`** | `agents/README.md` + `agents/_template/README.md` | "One subfolder per agent". Template con `agent.py`, README y `tests/` |
| C9 | **Tests de agente en `agents/<name>/tests/`** | `agents/_template/tests/README.md` | "Test skeleton for AI agents". Solo documentado, no implementado |
| C10 | **Documentación por carpeta: cada subdirectorio tiene su README** | Patrón en todas las carpetas raíz + subcarpetas | `README.md` + `README.es.md` por carpeta |
| C11 | **CONTEXT.md como fuente única de verdad del dominio** | `README.md` | "Single source of truth for your company". Remplazar placeholder por briefing asignado |
| C12 | **Flujo de datos: raw → pipelines → process → servicios/agentes** | `README.md` raíz (sección "How to think about this monorepo") | "Flow: raw → pipelines → process → consumed by services/, uis/, or agents/" |
| C13 | **Docker socket montado para uso docker dentro del contenedor** | `.devcontainer/devcontainer.json` | `mounts: source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind` |
| C14 | **Documentación transversal en `docs/`** | `docs/README.md` | "Cross-cutting documentation: architecture guides, technical decisions, conventions, processes" |

---

## 5. Contexto funcional del Incident Manager

Fuente oficial externa:
`4GeeksAcademy/ai-engineering-syllabus/content/contexts/4-devs/incident-manager-for-devs/CONTEXT-trackflow.es.md`

### Catálogos obligatorios

**Canales:**
`carrier_portal_alert`, `client_email`, `wms_alert`, `warehouse_call`, `dashboard`

**Tipos de incidencia:**
`lost_parcel`, `inventory_discrepancy`, `carrier_failure`, `system_outage`, `return_dispute`, `sla_breach`

**Severidades:**
`critical`, `high`, `medium`, `low`

**Áreas responsables:**
`warehouse_operations`, `last_mile_carrier`, `reverse_logistics`, `customer_experience`, `commercial`, `technology`

**Estados y transiciones:**
`open → assigned → in_progress → resolved → closed`
`reopened` puede aparecer desde `resolved`.

### Campos mínimos del modelo

| Campo | Tipo / valores | Opcional |
|---|---|---|
| `warehouse_location` | `los_angeles` \| `zaragoza` \| `null` | Sí (nullable) |
| `client_name` | string \| `null` | Sí (nullable) |
| `channel` | enum del catálogo | No |
| `type` | enum del catálogo | No |
| `severity` | enum del catálogo | No |
| `responsible_area` | enum del catálogo | No |
| `title` | string | No |
| `description` | string | No |
| `status` | enum del grafo | No |
| `assigned_to` | string | Sí (nullable) |
| `created_at` | datetime | No |
| `updated_at` | datetime | No |

### Reglas de negocio

1. **Transición de estados:** open → assigned → in_progress → resolved → closed. `reopened` puede aparecer desde `resolved`.
2. **Severidad critical:** no puede pasar a `closed` sin pasar antes por `resolved`.
3. **Auditoría obligatoria:** los cambios de `status`, `assigned_to` y `responsible_area` deben guardar *timestamp* + *autor*.
4. **Responsible_area dinámico:** puede cambiar en cualquier momento y el cambio debe quedar auditado.
5. **Mínimo 12 incidencias semilla** con la siguiente cobertura:
   - Las 4 severidades representadas.
   - Ambos almacenes (`los_angeles`, `zaragoza`).
   - Al menos 4 canales diferentes.
   - Al menos 1 incidencia con estado `reopened`.
   - Al menos 1 incidencia sin `client_name` (`null`).
6. **Estos catálogos y reglas son la fuente funcional única del Incident Manager.**

### Alcance de este ticket

Este ticket cubre exclusivamente la funcionalidad del **TrackFlow Incident Manager**:
- Modelo de datos y persistencia (a decidir).
- API REST de incidencias.
- UI dashboard de incidencias.
- Semillas de datos iniciales.

**Quedan explícitamente fuera del alcance:**
- Agentes de IA (viven en `agents/`).
- Workflows de automatización (viven en `workflows/`).
- Hasta nuevo aviso, estos componentes no forman parte del Incident Manager.

---

## 6. Decisiones técnicas pendientes

Cuestiones que **no pueden resolverse con la evidencia actual del repositorio**. Son decisiones nuevas, no convenciones existentes.

| # | Decisión | Contexto | Opciones posibles |
|---|---|---|---|
| D1 | **ORM y base de datos** | `services/` no tiene dependencias declaradas. `uv sync` existe pero no hay `pyproject.toml` ni `requirements.txt`. | SQLite (desarrollo) / PostgreSQL (producción). SQLAlchemy + Alembic vs alternativa. |
| D2 | **Estrategia de semillas** | No existe `data/raw/` con datos ni pipeline. Propuesta anterior de `data/raw` + pipeline era prematura. | Decidir junto con la persistencia: script de seed, fixture, o migración. |
| D3 | **Stack frontend para `uis/backoffice/`** | No hay evidencia de stack frontend. `@repo/shared-types` sugiere TypeScript, pero no stack UI. | React, Vue, Svelte, o vanilla. La decisión debe ser compatible con el consumo de `@repo/shared-types`. |
| D4 | **Framework de testing** | No hay tests implementados en ninguna carpeta. Solo README de tests en plantilla de agente. | pytest para Python, vitest/jest para TypeScript. Sin evidencia de elección previa. |
| D5 | **Estructura de la auditoría** | Las reglas del dominio (R3-R6) requieren guardar timestamp + autor por cada cambio de estado, assigned_to y responsible_area. | Tabla separada `incident_audit_log` vs array embedded `audit_trail[]` en cada incidencia. |
| D6 | **Validación del grafo de estados** | Las transiciones del grafo (R1) y la regla de critical (R2) deben validarse en backend. | Lógica en Python (FastAPI validator/dependency) vs constraints en base de datos. |
| D7 | **Separación de entornos** | Sin infra definida, sin `.env`, sin configuración de entornos. | Diferido hasta que exista despliegue. De inicio, todo local. |
| D8 | **Workspace monorepo npm/pnpm** | README dice "no workspace runner is configured at root". Solo existe `package.json` en `packages/shared/`. | Evaluar si configurar workspace npm/pnpm ahora o al añadir frontend. |
| D9 | **Inconsistencia CONTEXT.es.md** | `CONTEXT.es.md` es placeholder; `CONTEXT.md` tiene TrackFlow. | Decidir si sincronizar ambos o dejar CONTEXT.es.md como está. |

---

## 7. Propuesta de mejora no aplicada

### Entrypoint inconsistente en `packages/shared/package.json`

- **Evidencia:** `packages/shared/package.json` declara `"main": "index.ts"` y `"types": "index.ts"`. El archivo `index.ts` no existe en `packages/shared/`. El código TypeScript real está en `packages/shared/types/index.ts`.
- **Riesgo:** Cualquier consumo del paquete `@repo/shared-types` que resuelva el entrypoint (`import ... from "@repo/shared-types"`) fallará porque el punto de entrada declarado no existe. Esto afectará tanto a `uis/` como a `services/` cuando comiencen a consumir los tipos compartidos.
- **Propuesta de alineación futura:** Renombrar o ajustar el campo `main` en `package.json` para que apunte a `types/index.ts`, o crear un `index.ts` en la raíz de `packages/shared/` que re-exporte desde `./types`.
- **Estado:** NO APLICADA

> Esta corrección no se aplica en esta fase para mantener el principio de no modificar archivos existentes durante el reconocimiento. Se aplicará cuando se inicie la implementación que consuma `@repo/shared-types`.

---

*Documento generado en Fase 1 de reconocimiento. Ninguna funcionalidad ha sido implementada todavía.*