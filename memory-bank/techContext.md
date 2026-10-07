# TrackFlow — Technical context

## Estructura real del repositorio

El repositorio es un monorepo de plantilla para proyectos transversales de AI Engineering, adaptado a TrackFlow mediante `CONTEXT.md`. En la rama de infraestructura observada existen estas áreas:

- `/uis`: contiene su README y define interfaces; identifica como proyectos principales el sitio público `website` y la aplicación interna `backoffice`. **Aún no hay subcarpetas de aplicación.**
- `/services`: reservado para APIs y workers backend. El README habla de centralizar los servicios backend de la compañía. **Aún no hay servicio implementado.**
- `/packages`: contiene paquetes compartidos versionables; hay `packages/shared` con `@repo/shared-types` versión `0.0.1`, `private`, sin scripts y con tipos TypeScript de ejemplo (`Id`, `BaseEntity`).
- `/agents`: contiene guía, una plantilla vacía y `tools/` reservado a herramientas reutilizables; todavía no hay agentes de producto implementados.
- `/skills`: capacidades reutilizables para agentes; contiene plantillas y ejemplos de análisis de datos/investigación/revisión de código.
- `/mcps`: lugar documentado para servidores MCP.
- `/data`: `raw`, `pipelines`, `process` y `eval` para fuentes, transformación, salidas y evaluación.
- `/workflows`: automatizaciones y orquestación.
- `/shared`: recursos compartidos sin empaquetar.
- `/docs`: documentación transversal y decisiones.
- `/infra`, `/scripts` e `/internal`: infraestructura/despliegue, scripts auxiliares y herramientas internas estructuradas.
- En la raíz también hay `CONTEXT.md`, READMEs, `company-choice.md` y `.devcontainer/`.

Los README locales definen la responsabilidad de cada carpeta y piden documentar los nuevos componentes. Revisarlos antes de añadir contenido allí.

## Decisiones y configuración técnicas existentes

- `README.md` indica que la plantilla base es principalmente una estructura y documentación, no una aplicación ejecutable con scripts globales.
- Las instrucciones para `services/` recomiendan un backend FastAPI centralizado y evitar microservicios prematuros; es una guía del repositorio, no evidencia de que ya exista ese backend.
- `packages/shared` ya es un paquete TypeScript de tipos compartidos; su presencia no define el stack de las aplicaciones.
- Los agentes tienen una plantilla en `/agents/_template`; los skills, una estructura reusable bajo `/skills`.
- No hay metadatos de workspace ni runner global en la raíz descritos por el README. No asumir frameworks, proveedor cloud, base de datos, ORM, autenticación, hosting, LLM ni herramientas de build que no estén comprobados.

## Restricciones del proyecto

- `CONTEXT.md` es fuente de verdad para el dominio TrackFlow; conservar sus datos y discrepancias, y no sustituirlo por este resumen.
- Esta fase crea solo infraestructura de instrucciones y documentación de agentes. Website, backoffice y backend siguen pendientes; no añadir dependencias globales ni implementar aplicaciones como parte de esta tarea.
- Ubicar trabajo según el propósito de las carpetas y respetar su README. Evitar duplicar módulos existentes; extender/reusar antes de crear duplicados.
- Las necesidades operativas son transfronterizas (Los Ángeles y Zaragoza, EE. UU. y España); no introducir requisitos técnicos o regulatorios concretos que el contexto no especifique.
- La carpeta `/.agents` contiene configuración y reglas para agentes del repositorio. No confundirla con `/agents` (código de agentes) ni con `/skills` (capacidades reutilizables de producto/agente). La skill de revisión solicitada vive en `/.agents/skills` como infraestructura de agentes, no como nueva skill de producto en `/skills`.

## Evidencia consultada

`README.md`, `CONTEXT.md`, `uis/README.md`, `services/README.md`, `packages/README.md`, `packages/shared/package.json`, `packages/shared/types/index.ts`, `agents/README.md`, `agents/_template/README.md`, `agents/tools/README.md`, `skills/README.md`, `mcps/README.md`, `data/{raw,pipelines,process,eval}/README.md`, `workflows/README.md`, `shared/README.md`, `docs/README.md`, `infra/README.md`, `scripts/README.md` e `internal/README.md`.