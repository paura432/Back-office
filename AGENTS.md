# Instrucciones para agentes — TrackFlow

## Inicio de sesión obligatorio

Antes de analizar, planificar o editar el repositorio, lee en este orden:

1. `CONTEXT.md` completo: fuente de verdad del negocio TrackFlow.
2. `memory-bank/projectbrief.md`.
3. `memory-bank/techContext.md`.
4. `memory-bank/progress.md`.
5. Las reglas aplicables de `.agents/rules/` (incluidas las marcadas `always_active`).

Antes de trabajar en una carpeta, lee también su `README.md` y sigue las instrucciones locales.

## Límites de autorización

No modificar sin confirmación explícita del usuario:

- `CONTEXT.md`.
- Infraestructura o configuración sensible, credenciales, despliegue, seguridad o acceso.
- Decisiones arquitectónicas globales o documentación que las establezca.
- Dependencias globales, manifiestos/lockfiles globales o configuración del workspace.
- Archivos fuera del alcance solicitado.

No inventes hechos sobre TrackFlow. Si hay contradicciones en el contexto, consérvalas y señálalas en vez de resolverlas por suposición. No implementes componentes que no estén en el alcance autorizado.

## Antes de cada commit — protocolo obligatorio

No hagas commit hasta completar todos estos pasos y comunicar cualquier bloqueo:

1. Revisar el alcance y los requisitos solicitados; confirmar que cada cambio responde a ellos.
2. Revisar el diff completo (`git diff` y, para archivos nuevos, revisar su contenido y `git diff --no-index /dev/null <archivo>` o equivalente).
3. Ejecutar las verificaciones aplicables a los archivos y componentes modificados (tests, build, lint u otras comprobaciones documentadas). Si no existen o no aplican, indicarlo explícitamente.
4. Actualizar `memory-bank/` si cambió el estado, el alcance realizado o la arquitectura.
5. Comprobar `git status` y confirmar que solo incluye archivos previstos.
6. Solo entonces realizar el commit autorizado. No incluir cambios ajenos ni asumir autorización para modificar los límites indicados arriba.

La skill `.agents/skills/pre-commit-review/SKILL.md` proporciona la lista de validación: úsala antes de cada commit. No realiza commits automáticamente.