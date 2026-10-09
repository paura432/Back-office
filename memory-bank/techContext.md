# TrackFlow — Technical context

## Estructura real del repositorio

El repositorio es un monorepo de plantilla para proyectos transversales de AI Engineering, adaptado a TrackFlow mediante `CONTEXT.md`. En la rama de infraestructura observada existen estas áreas:

- `/uis`: website y backoffice en Next.js 16.4.0, React 19.3.0, TypeScript y App Router; un Dockerfile y supervisor Node ejecutan ambos en `ui`.
- `/services`: `api/` contiene FastAPI minimo con `GET /health`, sin funcionalidades de negocio; un Dockerfile crea el contenedor `api`.
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

- La raiz incluye `docker-compose.yml` para desarrollo con dos servicios, `ui` y `api`. No hay runner de workspace global ni despliegue productivo.
- Existe un backend FastAPI minimo; solo implementa `/health`. No se han implementado las necesidades de negocio descritas en el contexto.
- `packages/shared` ya es un paquete TypeScript de tipos compartidos; su presencia no define el stack de las aplicaciones.
- Los agentes tienen una plantilla en `/agents/_template`; los skills, una estructura reusable bajo `/skills`.
- No hay metadatos de workspace ni runner global en la raíz descritos por el README. No asumir frameworks, proveedor cloud, base de datos, ORM, autenticación, hosting, LLM ni herramientas de build que no estén comprobados.

## Restricciones del proyecto

- `CONTEXT.md` es fuente de verdad para el dominio TrackFlow; conservar sus datos y discrepancias, y no sustituirlo por este resumen.
- Cierre Docker #infra-40: migracion autorizada a Next.js App Router conservando diseno y contenido. No implementar funcionalidades de negocio ni cambiar dependencias globales.
- Ubicar trabajo según el propósito de las carpetas y respetar su README. Evitar duplicar módulos existentes; extender/reusar antes de crear duplicados.
- Las necesidades operativas son transfronterizas (Los Ángeles y Zaragoza, EE. UU. y España); no introducir requisitos técnicos o regulatorios concretos que el contexto no especifique.
- La carpeta `/.agents` contiene configuración y reglas para agentes del repositorio. No confundirla con `/agents` (código de agentes) ni con `/skills` (capacidades reutilizables de producto/agente). La skill de revisión solicitada vive en `/.agents/skills` como infraestructura de agentes, no como nueva skill de producto en `/skills`.

## Evidencia consultada

`README.md`, `CONTEXT.md`, `uis/README.md`, `services/README.md`, `packages/README.md`, `packages/shared/package.json`, `packages/shared/types/index.ts`, `agents/README.md`, `agents/_template/README.md`, `agents/tools/README.md`, `skills/README.md`, `mcps/README.md`, `data/{raw,pipelines,process,eval}/README.md`, `workflows/README.md`, `shared/README.md`, `docs/README.md`, `infra/README.md`, `scripts/README.md` e `internal/README.md`.

## Entorno Docker en fase Vite (historico, 2026-10-09)

- Codespaces reconstruido con Docker Engine 28.1.1-1 y Compose v5.6.0. El hotfix de Yarn permite instalar docker-in-docker:4 sin desactivar GPG.
- Bootstrap: Corepack/pnpm y herramientas Python conservados. `uv sync` solo para TOML de proyecto valido en raiz o `services/api`; si no hay ninguno se omite sin error. Locks existentes usan `--frozen`. No existe `pyproject.toml` ficticio en raiz.
- `ui`: Node 22.14.0, `npm ci` con los locks existentes, Vite 6.4.4 resuelto, puertos 3000/3001. `dev.mjs` supervisa ambos procesos y sus grupos, con apagado por senales y salida no cero si un frontend termina inesperadamente.
- `api`: Python 3.12.10, uv 0.6.17, FastAPI 0.115.12 y Uvicorn 0.34.2; transitivas y hashes en `services/api/uv.lock`. Dependencias congeladas en `/opt/venv`, Uvicorn con `--reload`.
- Fuentes bind-mounted y dependencias frontend en dos volumenes nombrados independientes. Polling de Vite/WatchFiles para recarga en Docker. Instalacion automatica de dependencias en build y arranque.
- Red Compose predeterminada: Vite usa `http://api:8000` en el servidor y retira `/api`; el navegador usa URLs relativas `/api/...`. Publicaciones limitadas a `127.0.0.1`, con defaults 3000, 3001 y 8000 sin `.env`.
- `.env` local sin secretos y excluido de Git; `.env.example` solo contiene puertos. No hay credenciales hardcodeadas, acceso a socket Docker ni configuracion privilegiada en el stack de aplicaciones.
- Evidencia ejecutada: hello-world, config, build, up, ps, HTTP directo/proxy, DNS interno, HMR WebSocket en ambos Vite, reload de Uvicorn, builds frontend, logs, fallo supervisado y apagado normal con salidas 0; `down` deja el stack detenido.
- **GAP Next.js pendiente de decidir:** el enunciado menciona Next.js, pero el repositorio usa Vite. No se migra en esta fase ni se declara cumplimiento total del enunciado.
- Pendiente: decidir GAP Next.js, funcionalidades backend de negocio y una estrategia de produccion; el stack actual es exclusivamente de desarrollo.

## Estado actual: Next.js y evidencias (2026-10-09)

- Migracion retomada sobre `b12f289` sin descartar trabajo local. Ambos frontends usan Next.js 16.4.0 estable, React 19.3.0 y TypeScript App Router con locks. CSS, contenido, anclas y menu movil conservados; entry points Vite eliminados.
- `ui` ejecuta ambos `next dev --webpack` en 3000/3001. Bind mounts de fuentes y cuatro volumenes: dependencias y `.next` independientes por app. Instalacion automatica con `npm ci`; polling webpack para cambios.
- Rewrites `/api/:path*` hacia el destino server-only `http://api:8000`; localhost, 127.0.0.1 y Codespaces permitidos como origenes dev. FastAPI separado y sin cambios de negocio; puertos solo loopback.
- `.next`, `node_modules`, tsbuildinfo y variantes de `.env` excluidos de Git/contexto UI. `.env.example` conserva solo puertos, sin secretos.
- Recarga automatica comprobada en navegadores abiertos y FastAPI sin reiniciar contenedores. Algunos cambios recargan el documento; no se garantiza conservar todo el estado React transitorio.
- Comparacion visual previa contra seis referencias Vite a 1440/390/320 px: 0.0000% de diferencia de pixeles, contenido/enlaces/secciones e interacciones conservados.
- Cinco capturas originales del usuario en `docs/screenshots/infra-40-{build,compose,website,backoffice,fastapi}.png`, extraidas del ZIP sin modificar bytes. CRC/decodificacion PNG y SHA-256 verificados. Indice en `docs/README.md`; complementan pruebas reales, no las sustituyen.
- **GAP Next.js resuelto.** API de negocio, auth, persistencia y estrategia de produccion siguen fuera del alcance; no se afirma que esten implementados.