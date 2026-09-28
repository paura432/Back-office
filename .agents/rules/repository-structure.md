# repository-structure.md

> Regla derivada de la estructura del monorepo y sus READMEs.
> Garantiza que cada componente se ubique en la carpeta correcta según su responsabilidad.

---

- **Aplicación:** `always_active`
- **Ámbito/patrón de archivos:** `*` (todo el repositorio)

## Evidencia de origen

- `README.md` — tabla "How to think about this monorepo": asigna cada tipo de componente a una carpeta raíz específica.
- `README.md` — "Rule of thumb": "if it has a UI → `uis/`. If it exposes an API or runs in the background → `services/`."
- `uis/README.md` — "Main purpose: to centralize in a single place all frontend applications."
- `services/README.md` — "Main purpose: to centralize all the backend logic, APIs, and queue consumers."
- `packages/README.md` — "Shared packages for the monorepo: internal libraries, utilities, types, shared components."

## Qué se debe hacer

- Colocar **aplicaciones con interfaz de usuario** (webs, backoffices, dashboards con UI) dentro de `uis/`.
- Colocar **APIs y workers en segundo plano** dentro de `services/`.
- Colocar **librerías y tipos compartidos versionables** dentro de `packages/`.
- Colocar **agentes de IA** dentro de `agents/`. Un agente = una subcarpeta.
- Colocar **pipelines de datos** dentro de `data/pipelines/`.
- Colocar **documentación transversal** dentro de `docs/`.
- Colocar **configuración de infraestructura** dentro de `infra/`.
- Colocar **automatización y flujos** dentro de `workflows/`.
- Ante la duda, consultar la tabla de responsabilidades en `README.md`.

## Qué NO se debe hacer

- ❌ Crear una aplicación UI en la raíz del repositorio, en `/app`, o en cualquier lugar fuera de `uis/`.
- ❌ Crear un backend o API fuera de `services/`.
- ❌ Duplicar tipos compartidos en múltiples carpetas en lugar de extraerlos a `packages/`.
- ❌ Crear nuevos directorios raíz sin justificación documentada (el monorepo ya tiene 13 carpetas con responsabilidad definida).
- ❌ Mezclar responsabilidades: no poner lógica de backend dentro de `uis/` ni código de UI dentro de `services/`.

## Cómo verificar su cumplimiento

- `ls -d uis/*/` debe contener solo subcarpetas de frontend.
- `ls -d services/*/` debe contener solo subcarpetas de backend.
- Ningún archivo `.tsx`, `.vue`, `.svelte` o HTML debe existir fuera de `uis/`.
- Ninguna definición de router API debe existir fuera de `services/`.
- Los imports entre carpetas deben seguir la direccionalidad del flujo de datos (README.md).