---
name: pre-commit-review
description: Validar un cambio de TrackFlow antes de permitir su commit; nunca realiza el commit.
---

# Skill: pre-commit-review

## Objetivo único

Evaluar si un cambio del repositorio TrackFlow está listo para commit y emitir un resultado verificable **PASS** o **FAIL**. Esta skill solo revisa y valida; no crea commits, no los publica ni amplía el alcance.

## Cuándo usarla

Usarla antes de cada commit, después de terminar los cambios y antes de ejecutar `git commit`. Si falta información o una verificación requerida no puede ejecutarse, no dar PASS.

## Inputs obligatorios

1. **Alcance/tarea:** solicitud aprobada y requisitos concretos.
2. **Archivos modificados:** lista completa, incluidos archivos nuevos, eliminados y renombrados.
3. **Comandos de verificación aplicables:** comandos exigidos por README, configuración o por el tipo de cambio; indicar explícitamente si no hay comandos definidos.

Consultar también `CONTEXT.md`, Memory Bank, reglas aplicables de `/.agents/rules/` y README de las carpetas afectadas según `AGENTS.md`.

## Procedimiento

1. Comprobar que los tres inputs están disponibles y que el alcance no requiere una autorización pendiente.
2. Obtener y revisar el diff completo, incluyendo el contenido de archivos nuevos; relacionar cada cambio con un requisito del alcance.
3. Verificar que todos los archivos están en rutas correctas y que se cumplen las reglas activas, README y restricciones de TrackFlow.
4. Ejecutar todos los tests, build, lint u otros comandos aplicables identificados en los inputs y documentación. Registrar comando y resultado; no afirmar éxito si no se ejecutó.
5. Comprobar si el cambio altera estado, progreso o arquitectura y, si corresponde, verificar que `memory-bank/` fue actualizado de forma fiel.
6. Consultar `git status --short` y verificar los archivos previstos; señalar cualquier cambio ajeno o no incluido en la revisión.
7. Emitir resultado **PASS** solo si todos los criterios siguientes se cumplen. En cualquier otro caso, emitir **FAIL** con motivos y acciones pendientes. No hacer commit automáticamente.

## Output

Un informe conciso con:

- `Resultado: PASS` o `Resultado: FAIL`.
- Alcance revisado y archivos incluidos.
- Estado de diff, reglas/rutas y verificaciones ejecutadas (comandos y resultados).
- Estado de actualización del Memory Bank (actualizado, no necesario o falla).
- `git status --short` conocido y cualquier discrepancia.
- Bloqueos o correcciones requeridas; con PASS, declarar que queda listo para que una persona/agente autorizado decida el commit.

## Criterios de aceptación verificables

El resultado solo puede ser **PASS** cuando se confirme todo lo siguiente:

- [ ] Diff completo revisado, incluidos archivos nuevos.
- [ ] Cada cambio está dentro del alcance aprobado.
- [ ] Reglas aplicables y README de las carpetas afectadas comprobados.
- [ ] Tests/build/lint y demás verificaciones aplicables ejecutados y exitosos; si no existen/no aplican, se documenta por qué.
- [ ] Memory Bank actualizado si cambió el estado o la arquitectura, o se documenta por qué no corresponde.
- [ ] `git status --short` conocido y consistente solo con cambios revisados.
- [ ] Resultado final expresado explícitamente como `PASS` o `FAIL`.
- [ ] Ningún commit se ha ejecutado como parte de esta skill.
