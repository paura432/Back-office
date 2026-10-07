# TrackFlow — Progress

## Estado inicial

- Repositorio `paura432/Back-office`, rama `feature/agent-memory-bank`, creada desde `main` actualizado.
- Working tree limpio al comenzar.
- Repositorio en fase de plantilla/estructura: sin `uis/website`, `uis/backoffice` ni backend implementados. El paquete compartido existente contiene solo tipos de ejemplo.

## Infraestructura creada

- Memory Bank inicial: `projectbrief.md`, `techContext.md` y este `progress.md`.
- `AGENTS.md` con protocolo de inicio de sesión, cambios y commit.
- Regla de estructura del repositorio en `/.agents/rules/trackflow-repository-structure.md`.
- Skill de revisión pre-commit en `/.agents/skills/pre-commit-review/SKILL.md`.

## Aplicación pendiente

No se ha implementado website público, backoffice, backend, agente de producto ni dependencia nueva. Esta fase se limita a infraestructura AI-ready solicitada.

## Próximos pasos concretos

1. Revisar y aprobar el alcance funcional de la siguiente tarea contra `CONTEXT.md`.
2. Antes de crear cada componente, consultar este Memory Bank, `/.agents/rules/` y el README de la carpeta destino.
3. Elegir arquitectura y stack solo cuando el alcance y una decisión explícita del proyecto lo requieran; registrar decisiones globales con autorización.
4. Implementar únicamente el componente solicitado en su ruta del monorepo, con README y verificaciones aplicables.
5. Usar `/.agents/skills/pre-commit-review/SKILL.md` antes de cada commit y actualizar este archivo al cambiar el estado de implementación o arquitectura.