# TrackFlow — Progress

## Estado inicial

- Repositorio `paura432/Back-office`, rama `feature/agent-memory-bank`, creada desde `main` actualizado.
- Working tree limpio al comenzar.
- Repositorio en fase de plantilla/estructura; no había website, backoffice ni backend implementados.

## Infraestructura creada

- Memory Bank inicial: `projectbrief.md`, `techContext.md` y este `progress.md`.
- `AGENTS.md` con protocolo de inicio de sesión, cambios y commit.
- Regla de estructura del repositorio en `/.agents/rules/trackflow-repository-structure.md`.
- Skill de revisión pre-commit en `/.agents/skills/pre-commit-review/SKILL.md`.

## Aplicaciones implementadas

- **Website público** en `uis/website/`: Vite + TypeScript vanilla y CSS, con portada corporativa, servicios, operación internacional de Los Ángeles y Zaragoza, y llamada a la acción. Contenido público derivado de `CONTEXT.md`; no se muestran personas, información operativa interna ni métricas inventadas.
- Website: `npm install` correcto; `npm run build` correcto; smoke test HTTP de `/` respondió 200 y cargó el HTML y módulo de interfaz esperados.
- Website: revisión pre-commit PASS; commit `83c118f`.
- **Backoffice** en `uis/backoffice/`: aplicación independiente con layout administrativo y datos de contexto, sin backend ni telemetría conectados. El dashboard muestra las áreas y ubicaciones documentadas, prioridades del contexto y aviso de que no hay datos live.
- Backoffice: `npm install` y `npm run build` correctos; smoke test HTTP de `/` respondió 200 y el módulo muestra las áreas/localizaciones previstas. Revisión pre-commit PASS; commit `341dca7`.
- **Backend:** no implementado ni incluido en el alcance de esta fase.

## Entrega del hito AI-ready

- Infraestructura de agentes terminada: Memory Bank de negocio y técnico, protocolo `AGENTS.md`, regla de estructura de alcance repository-wide y skill reutilizable de revisión pre-commit.
- Website corporativo terminado en `uis/website/`, basado en el contexto documentado de TrackFlow.
- Backoffice de operaciones terminado en `uis/backoffice/`, con contenido de contexto y sin backend ni datos operativos en vivo.
- Infraestructura AI-ready: **COMPLETED**.
- Website: **COMPLETED**; build verificado en esta fase con `npm run build`: **PASS**.
- Backoffice: **COMPLETED**; build verificado en esta fase con `npm run build`: **PASS**.
- Capturas de entrega: **READY** — `docs/screenshots/trackflow-website.png` y `docs/screenshots/trackflow-backoffice.png` (PNG reales de 1920 × 1032).
- Hito: **READY FOR PR** desde `feature/agent-memory-bank` hacia `main`. No hacer merge sin autorización.

## Fase 2 Docker #infra-40 (historico, 2026-10-09)

Estado independiente del hito anterior: trabajo en `feature/infra-40-containerization`
de `paura432/Back-office`. Rama/remoto confirmados; working tree limpio al comenzar.
No se modifica main, no se crea PR y no se hace merge.

- Bootstrap corregido para omitir `uv sync` sin proyecto valido y usar `services/api` cuando procede. Siete escenarios probados: ausencia, TOML invalido, nombre vacio, proyecto API, fallback, prioridad de raiz y lock congelado. Sincronizacion real de la API con `--frozen`: PASS.
- API minima implementada: FastAPI `/health` con `{"status":"ok"}`, pyproject y lock con transitivas/hashes. No hay endpoints de negocio.
- Dockerfiles y dockerignore de `uis` y `services`; Compose con un `ui` para dos Vite y un `api` con Uvicorn reload. Fuentes montadas, dependencias instaladas automaticamente y `node_modules` aislados por aplicacion.
- `.env` local sin secretos e ignorado; `.env.example` con puertos. Defaults verificados sin archivo local; puertos solo loopback. Proxy `/api` probado en ambos frontends; DNS `api` probado desde `ui`.

### Verificacion real

| Comprobacion | Resultado |
| --- | --- |
| `docker run --rm hello-world` | PASS |
| `docker compose config` y defaults sin `.env` | PASS |
| `docker compose build` | PASS, ambas imagenes |
| `docker compose up -d`, healthchecks y `docker compose ps` | PASS, ambos healthy |
| Website 3000 y backoffice 3001 | HTTP 200 |
| API 8000 `/health` | HTTP 200, payload exacto |
| `/api/health` por ambos Vite | HTTP 200, payload exacto |
| DNS y HTTP interno `api:8000` desde `ui` | PASS |
| Recarga Vite | PASS, eventos WebSocket HMR y CSS modificado en ambos |
| Recarga Uvicorn | PASS, cambio de payload detectado sin recrear contenedor |
| `npm run build` de ambos frontends dentro de `ui` | PASS |
| Logs sin errores criticos antes de fallo controlado | PASS |
| Fallo controlado de un Vite | PASS, supervisor detiene `ui` con salida no cero 143 |
| Apagado normal SIGTERM | PASS, `ui` y `api` salen con codigo 0 |
| `docker compose down` | PASS, sin contenedores del stack ni red restantes |

Los cambios temporales de HMR se retiraron; los estilos originales y el payload
final de `/health` estan restaurados. Los volumenes de dependencias se conservan
deliberadamente tras `down`.

### Pendientes y alcance

- **GAP Next.js: OPEN.** El enunciado exige/menciona Next.js; la implementacion real usa Vite. Se requiere decidir migracion o aceptar Vite por separado. No hay cumplimiento total mientras ese GAP siga abierto.
- Backend funcional de negocio, autenticacion, persistencia y despliegue productivo no forman parte de esta fase.
- Documentacion tecnica actualizada con comandos, networking, bootstrap y limites. Commit y publicacion se verifican en el historial de la rama; no se crea PR ni se hace merge.

## Cierre Next.js y evidencias #infra-40 (2026-10-09)

- Rama `feature/infra-40-containerization`, HEAD inicial `b12f289`; migracion local existente preservada. Website/backoffice pasan a Next.js 16.4.0, React 19.3.0 y TypeScript App Router sin redisenar.
- Se corrigio el bloqueo de HMR desde loopback mediante origenes localhost/127.0.0.1/Codespaces. Contenido, CSS, menu movil y responsive conservados.
- Pruebas ejecutadas: hello-world, config/build/up con espera/ps; HTTP 200 en ambas interfaces, API y dos rewrites; DNS interno; builds Next.js de ambas apps: PASS.
- Comparacion Playwright de seis pantallas 1440/390/320 px: 0.0000% de diferencia de pixeles, texto/enlaces/secciones iguales, interacciones y ausencia de errores JavaScript: PASS.
- Recarga automatica verificada con cambios temporales de paginas y payload API, sin reiniciar contenedores. Probes retirados. No se afirma conservacion universal de estado React: algunos cambios recargan el documento.
- Cinco PNG del usuario extraidos de `trackflow_infra40_evidencias.zip` manteniendo `docs/screenshots/`, sin regenerar ni modificar capturas. ZIP/PNG CRC, decodificacion, dimensiones, SHA-256 y bytes contra ZIP: PASS. No se sobrescriben capturas previas.
- Capturas build/compose/fastapi: 1920 x 1032; website/backoffice: 1920 x 1140. Indice y alcance real en `docs/README.md`, enlazado desde README ingles y espanol.
- Builds y Compose repetidos tras incorporar evidencias: PASS. GAP Next.js **RESUELTO**. API de negocio, auth, persistencia y produccion permanecen fuera del alcance.
- Cierre real: cinco endpoints HTTP 200, logs sin errores criticos, terminacion supervisada de un Next.js con salida `ui` no cero, rearranque healthy y SIGTERM normal con salida 0 en `ui`/`api`: PASS. `docker compose down` elimina contenedores y red; los volumenes se conservan.
- Revision y publicacion finales consultables en el historial de la rama. No crear PR ni hacer merge.
## Auditoría documental de serialización (2026-10-22)

- En `feature/serialization-audit` se completó la auditoría de Fase 1 en `docs/serialization-audit.md`: 31 rutas de aplicación (15 ✅, 16 ⚠️, 0 ❌) y cuatro rutas FastAPI de documentación integradas (sin `response_model` de aplicación). La tabla detalla entradas, schemas declarados, estado ejecutable, consumidores y riesgos.
- Se confirmó que `/health` es la única respuesta de éxito; las otras 30 rutas de aplicación responden 501. Los frontends no contienen consumidores HTTP de negocio. No se modificaron API, schemas, contratos, tests, dependencias ni despliegue.
- `git diff --check` pasó y el inventario estático concuerda con 31 decoradores y 31 `response_model`. No se pudieron ejecutar pytest/runtime: el entorno no tiene FastAPI, uv, pytest ni Docker.
- Publicación de esta fase: commit `docs: audit backend serialization` y push de `feature/serialization-audit`, sin despliegue ni PR/merge.

## Cierre de implementación auditoría de serialización (2026-10-23)

- Se integró `origin/main` en `feature/serialization-audit`, conservando la API PostgreSQL (`db.py`), `/health`, `/status`, los routers y la auditoría local; se reconciliaron los conflictos de `main.py`, `pyproject.toml` y esta bitácora sin descartar las entradas de ambas ramas.
- `/status` usa `StatusResponse{status: operational|degraded}` explícito y conserva la comprobación `SELECT 1`; nunca responde con DSN/credenciales. Los demás endpoints de negocio/auth continúan como stubs 501; no se agregó lógica ni éxito de negocio.
- Se fijaron runtime/dependencies de tests, se regeneró `services/api/uv.lock` con uv 0.6.17 y se verificó instalación `uv sync --frozen --extra dev`.
- Se añadieron pruebas HTTP/OpenAPI, filtrado de campos señuelo y comportamiento PostgreSQL mock. Suite: 90 passed, 0 failed, 0 skipped. Cobertura final `app`, `main.py`, `db.py`: 100% (404 statements). Todas las 32 rutas APIRoute tienen response_model; `/health` y `/status` con referencias OpenAPI explícitas.
- `docs/serialization-audit.md` describe criterios, evidencia, límites y bloqueos; README de servicios reconciliados con main.
- PR/commits finales quedan pendientes de revisión completa de diff conforme al protocolo pre-commit.

## Auditoría de caching (2026-10-23)

- Nueva rama `feature/caching-optimisation` creada desde `main` (`43b845b`); el árbol de trabajo estaba limpio. No se implementó caché ni optimizaciones de frontend.
- `CACHING_REPORT.md` documenta stack, inventario de 20 GET de aplicación (2 funcionales y 18 stubs 501), dependencias actuales/hipotéticas, frecuencias configuradas y desconocidas, referencias Lighthouse históricas, propuestas condicionales de TTL/clave/ámbito/invalidación y rutas que no deben cachearse.
- Las medianas frontend disponibles pertenecen a la auditoría anterior en `audit/before/` y `audit/after/`; no se pudieron repetir en este entorno. No hay latencia backend por endpoint ni tráfico/datos operativos disponibles. No se creó ni ejecutó un seeder porque el backend de negocio y sus tablas no existen; producción no se consultó ni alteró.
- Añadida instrumentación pasiva de duración HTTP en `services/api/main.py`, que registra método, plantilla de ruta, status y ms sin URL raw, params ni payload. Test de log añadido en `services/api/tests/test_timing.py`; compileall y `git diff --check` pasan. No se pudo ejecutar pytest/build/Compose/Lighthouse por ausencia de uv, pytest, FastAPI, Node/npm y Docker.
- El checkout de `main` contiene marcadores de conflicto previos en `uis/website/{README.md,app/layout.tsx,app/page.tsx}` y `uis/backoffice/{README.md,app/layout.tsx,app/page.tsx}`; no se modificaron por quedar fuera del alcance y bloquean builds frontend.
- Publicación pendiente de completar checks bloqueados y protocolo pre-commit. Ningún commit/push registrado aún.

## Revisión de caching y reconciliación UI (2026-10-23)

- En `feature/caching-optimisation` se verificó HEAD `dacd066` sincronizado con `origin/feature/caching-optimisation` y árbol limpio antes de comenzar esta revisión. Se revisó el historial: el commit incluye informe, middleware y test de timing. No se confundió con la base `main` (`43b845b`).
- Reconciliados los seis archivos UI solicitados: README, layout y page de website y backoffice. Website conserva `SiteHeader` como Client Component y la página como Server Component; se mantienen `BrandMark`/`DecorativeArrow`, metadata, viewport y fuentes vía `next/font`. Backoffice conserva `BackendStatus` (fetch inicial + polling configurado cada 15 s), flechas SVG y contenido estático. Las guías locales quedaron alineadas con los layouts.
- Durante la búsqueda se hallaron marcadores adicionales en `uis/website/src/styles.css` y `uis/backoffice/src/styles.css`. Tras autorización explícita se eliminaron las secciones duplicadas de estilos y Google Fonts, manteniendo la variante con variables `next/font`, media queries y estilos del indicador. En total hay ocho archivos UI modificados, seis pedidos + dos CSS necesarios para desbloquear la compilación.
- No se implementaron lazy loading, `useMemo` ni caching TTL: no hay componentes pesados/cálculos costosos demostrables y 18 GET de negocio son 501; `/health` y `/status` no deben ocultar estado atrasado. El checklist 4Geeks permanece pendiente, con evidencia y razones en `CACHING_REPORT.md`.
- Checks: `python3 -m compileall -q services/api/main.py services/api/tests/test_timing.py` PASS; `git diff --check` PASS; búsqueda global de marcadores UI sin resultados; el proveedor de errores no reporta errores en los cuatro TSX revisados. Los dos `npm run build` (website y backoffice) y `uv run --frozen --extra dev pytest -q` se intentaron y quedaron bloqueados porque no existen `npm` ni `uv` en PATH; tampoco hay `node_modules`/`.venv`. No se instalaron herramientas, ni se alteraron dependencias/locks. Lighthouse/Compose no ejecutados.
- El informe ahora distingue los resultados de esta revisión de los Lighthouse históricos, enumera checks pendientes y marca los requisitos de práctica como no implementados/no justificados. No hubo acceso a producción, seed, PR, merge ni despliegue.
- Pendiente revisión final pre-commit, commits separados (UI y documentación/progreso), push y recomendación GO/NO-GO de PR; los builds/tests runtime siguen siendo el bloqueo para declarar una validación completa.

## Cierre de entrega Backend Serialization Audit (2026-10-23)

- Se recuperó el inventario individual de 31 endpoints de `12feda2` y se integró
	sin retirar la evidencia actual; se agregó `/status` para completar las 32
	rutas de aplicación. El documento distingue 2 rutas funcionales (`/health`,
	`/status`) y 30 stubs HTTP 501; también contabiliza las cuatro rutas framework
	de documentación por separado.
- Se retiró `services/api/.coverage` del índice Git y se añadió `**/.coverage` a
	`.gitignore`; el archivo local ignorado puede regenerarse al ejecutar coverage.
- Verificación reproducible con uv 0.6.17 desde `services/api`: `uv sync
	--frozen --extra dev --check` → “Would make no changes”; `pytest --collect-only`
	→ 91 casos; suite/cobertura → **91 passed, 0 failed, 0 skipped; 100% (404/404
	statements)** en `app`, `main.py`, `db.py`. Incluye ambos casos parametrizados
	`operational` y `degraded` de `/status`.
- La validación final confirma 32/32 `APIRoute.response_model`, OpenAPI para
	`/health` y `/status`, respuestas HTTP ASGI esperadas y exclusión de password,
	hash, salt, reset token y metadata no contratada. UI inspeccionada: backoffice
	consume `/api/status`; no se encontraron consumidores de rutas de negocio.
- Limitaciones: los 30 endpoints de negocio/auth continúan en 501; no hay
	autenticación ni autorización, ORM o payloads de negocio exitosos. La conexión
	PostgreSQL se prueba con mock; no se afirma conexión a una base real.
- Revisión pre-commit, commits/push y PR de entrega: pendientes al registrar esta
	actualización. No hacer merge ni despliegue.

## Auditoria de rendimiento frontend (2026-10-14)

- Rama `feature/frontend-performance-audit`, creada desde `origin/main` actualizado (`9d0561b`); working tree limpio antes del ejercicio.
- Fase 1: ambos frontends compilaron para produccion con Next.js 16.4.0 dentro de la imagen Docker existente. Se iniciaron con `next start`; HTTP 200 en website y backoffice. Lighthouse 12.8.2 / Chromium Headless 141.0.7390.37: 3 informes JSON/HTML por escenario (website/backoffice, desktop/mobile), 12 runs, resultados en `audit/before/`; capturas de filmstrip y viewport guardadas. Navegador, emulacion, versiones, resultados y mediana registrados. No se modifico codigo de aplicaciones antes de la linea base.
- Medianas Lighthouse iniciales (Performance/A11y/Best Practices/SEO): website desktop 99/95/96/100, website mobile 92/95/93/100; backoffice desktop 100/95/96/100, backoffice mobile 94/95/93/100. Medianas LCP/CLS/TBT/TTFB y cada ejecucion en `audit/before/summary.json` y reports.
- Smoke Playwright: ambos roots HTTP 200. Website no excede 412 px; backoffice mide 417 px de scroll width a 412 px. Lighthouse observa `/favicon.ico` 404. El baseline medido tiene TBT no cero solo en mobile; TBT no equivale a INP.
- Fases 2-6 pendientes al registrar esta nota. No hay optimizaciones ni mejoras finales declaradas.

## Retirada de `@import` de fuentes (2026-10-16)

- En `feature/frontend-performance-audit` se eliminó el `@import` duplicado de Google Fonts en `uis/website/src/styles.css` y `uis/backoffice/src/styles.css`. Los enlaces de `app/layout.tsx` siguen siendo el único origen de esas familias.
- Remedición con la misma metodología Lighthouse, sin otros cambios de aplicación: las peticiones de CSS de fuentes y de woff2 no bajaron; las medianas de CLS no cambiaron. No hay mejora demostrada. Evidencia en `audit/after-fonts/`. `audit/before/` no se alteró.
- El menú del website pasó a `uis/website/app/site-header.tsx`. La página vuelve a ser Server Component. Build de producción y prueba de apertura/cierre/teclado: PASS. Capturas desktop y móvil idénticas al baseline. Lighthouse posterior no muestra mejora reclamable.
- En backoffice, a 412 px desbordaba `article.team-card` (borde derecho 416.5 px, `scrollWidth` 417). Se redujo solo su padding horizontal a 6 px bajo 460 px. Tras el cambio, `scrollWidth` es 412 y el texto no se recorta. La captura móvil difiere un 2.98 % por ese padding. Performance móvil mediana 93 frente a 94; no se declara mejora.

## Cierre final auditoría rendimiento (2026-10-20)

- Rama `feature/frontend-performance-audit`, HEAD `add4e1bc2052b7c0c8edef37f917f5b86965e128`.
- **Builds verificados:** Backoffice (Next.js 16.4.0) y website compilan correctamente con `next/font/google` (DM_Sans, DM_Mono, Manrope) y `font-display: swap`. TypeScript y compilación: PASS.
- **Lighthouse:** No se pudieron re-ejecutar por falta de Docker Engine y Chromium en el entorno. Los informes existentes en `audit/after/` reflejan el estado tras las correcciones de fuentes, navegación y overflow (commits `07dc18f` + `645896f` + `90042a4`), pero anteriores a `add4e1b`. `audit/before/` se conserva intacto.
- **REPORT.md:** Creado con comparativa antes/después, LCP, CLS, TBT, puntuaciones, correcciones aplicadas, reutilización y conclusiones. No se inventan mejoras.
- **AUDIT.md:** Actualizado: tabla de alcance final, correcciones aplicadas con estado ✅/⚠️/❌, evidencia por fase y pendientes documentados.
- **next/font pendiente de remedición:** Documentado como limitación. Los builds compilan correctamente.
- **git diff --check:** PASS (sin errores de whitespace).
- **git status:** `AUDIT.md` modificado, `REPORT.md` nuevo, `memory-bank/progress.md` actualizado.
