# component-documentation.md

> Regla derivada del patrón de documentación del monorepo.
> Todo componente nuevo debe incluir documentación de propósito y ejecución.

---

- **Aplicación:** `always_active`
- **Ámbito/patrón de archivos:** `uis/*/`, `services/*/`, `agents/*/`, `data/pipelines/*/`, `workflows/*/`, `mcps/*/`, `shared/*/`, `scripts/*/`

## Evidencia de origen

- Patrón en todas las carpetas raíz y subcarpetas: cada una contiene `README.md` + `README.es.md` documentando propósito, estructura y uso.
- `README.md` raíz — "Document what you add: each new app, service, agent, or pipeline gets a subfolder + README."
- `agents/_template/README.md` — Template de agente incluye README con "goal, tools, prompts, memory, evaluations, and tests."
- `docs/README.md` — "Provide a single place for global project documentation (not tied to one app or agent only)."

## Qué se debe hacer

- Crear un `README.md` en la raíz de cada nuevo componente/subcarpeta que se añada.
- Incluir al menos:
  - Propósito del componente (qué problema resuelve).
  - Instrucciones de ejecución (cómo se arranca, qué puertos usa, dependencias).
  - Enlace a documentación transversal en `docs/` si aplica.
- Documentar decisiones de diseño específicas del componente en su propia carpeta o en `docs/`.

## Qué NO se debe hacer

- ❌ Añadir un nuevo servicio, UI, agente o pipeline sin su correspondiente `README.md` de entrada.
- ❌ Documentar únicamente dentro del código (comentarios) sin un punto de entrada documental para otros desarrolladores.
- ❌ Poner documentación específica de un componente en `docs/` sin referenciarla desde el README del componente — `docs/` es para documentación transversal, no para documentación de un solo componente.

## Cómo verificar su cumplimiento

- Verificar que cada subcarpeta dentro de `uis/`, `services/`, `agents/`, `data/pipelines/`, `workflows/` y `mcps/` contiene un archivo `README.md`.
- `for d in uis/*/ services/*/ agents/*/ data/pipelines/*/; do [ -f "$d/README.md" ] || echo "MISSING README in $d"; done`