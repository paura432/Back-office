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
- Builds finales de website y backoffice: **PASS** (`npm run build` en cada aplicación, tras `npm install`).
- Capturas reales: **SCREENSHOTS_PENDING**; Playwright/Chromium no pudo ejecutarse por faltar la biblioteca del sistema `libatk-1.0.so.0`. Para obtenerlas manualmente, abrir website en `http://localhost:5173/` y backoffice en `http://localhost:5174/` desde un navegador con interfaz y guardar los PNGs en `docs/screenshots/` con los nombres de entrega.
- Siguiente paso: completar las capturas y, cuando ambas estén disponibles, abrir la PR de `feature/agent-memory-bank` a `main` para revisión. No hacer merge sin autorización.