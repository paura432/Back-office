---
name: trackflow-repository-structure
scope: repository-wide
apply: always_active
---

# Estructura del repositorio TrackFlow

## Aplicación

**Modo explícito: `always_active`.** Esta regla aplica a todos los agentes y a cualquier cambio de archivos en el repositorio, en todo momento. Si una solicitud parece contradecirla, detente y pide confirmación antes de reubicar o crear código.

## Reglas verificables

1. Sitio web público de TrackFlow → `/uis/website`.
2. Aplicación interna/backoffice de TrackFlow → `/uis/backoffice`.
3. Backend, APIs y lógica de servicio → `/services`.
4. Configuración, instrucciones y reglas de agentes para este repositorio → `/.agents`.
5. Código de agentes de producto → `/agents`; capacidades reutilizables del producto/agentes → `/skills`.
6. No confundir `/.agents/skills` (skills/instrucciones para los agentes que trabajan en el repositorio) con `/skills` (capacidades reutilizables del proyecto TrackFlow).
7. Antes de crear o modificar contenido en una carpeta, leer y respetar su README y los README de las carpetas destino relevantes.
8. No duplicar módulos, servicios, agentes o capacidades sin necesidad: busca implementaciones existentes y reutilízalas o extiéndelas cuando sea apropiado.
9. No asumir que una ruta de aplicación ya existe; si la carpeta no existe, crearla solo cuando la tarea pida explícitamente esa aplicación.

## Evidencia de cada regla

- **Website → `/uis/website`; aplicación interna → `/uis/backoffice`:** `README.md`, sección “`uis/` — user interfaces”, y `uis/README.md`, que enumera `website` y `backoffice` como proyectos principales.
- **Backend → `/services`:** `README.md`, sección “`services/` — centralized company API”, y `services/README.md`, que reserva la carpeta para servicios backend, APIs y workers.
- **Configuración de agentes → `/.agents`:** decisión de organización de esta infraestructura del repositorio; se refleja en la ubicación de este archivo y de `AGENTS.md` en la raíz. No se atribuye a un README previo.
- **Agentes de producto → `/agents`; skills de producto → `/skills`:** `README.md`, secciones `agents/` y `skills/`, y `agents/README.md` y `skills/README.md`.
- **No confundir `/.agents/skills` con `/skills`:** separación explícita de esta regla: `/.agents/skills` aloja instrucciones de trabajo para los agentes del repositorio, mientras que `README.md` y `skills/README.md` reservan `/skills` a capacidades reutilizables del proyecto.
- **Respetar README:** `README.md`, “How to start” y “Folder guide”, pide leer el README de la carpeta antes de trabajar; los README de cada área especifican su responsabilidad.
- **No duplicar:** `README.md`, criterio de paquete compartido para interfaces requeridas por más de una carpeta y recomendación de evitar complejidad/splitting prematuro en servicios; los README de agentes/tools/skills promueven reutilización y consistencia.
