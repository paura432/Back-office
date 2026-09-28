# Rules Validation — TrackFlow Incident Manager

> Validación de las reglas del proyecto simulando 5 decisiones de implementación.
> El objetivo es confirmar que las reglas cambian el comportamiento del agente frente a decisiones incorrectas.

---

## Metodología

Para cada caso, se simula una instrucción que un agente o desarrollador podría recibir. Se documenta:
1. La decisión que tomaría **sin reglas** (basada en buenas prácticas genéricas o inercia).
2. La decisión que toma **con reglas** (basada en las reglas del proyecto).
3. Si la regla cambia claramente la decisión (PASS) o no (FAIL).

---

## Caso 1: "Crea el backoffice en `/app`"

| Dimensión | Valor |
|---|---|
| **Regla aplicada** | `repository-structure.md` |
| **Decisión sin regla** | El agente podría crear el backoffice en `/app` o en la raíz, ya que es una convención común en muchos proyectos (Next.js, monorepos JS). No hay restricción documentada que lo impida a priori. |
| **Decisión con regla** | El backoffice debe crearse dentro de `uis/backoffice/`. La regla es explícita: "colocar aplicaciones con interfaz de usuario dentro de `uis/`" y "❌ No crear una aplicación UI en la raíz del repositorio, en `/app`". |
| **PASS/FAIL** | **PASS** — La regla redirige inequívocamente a `uis/backoffice/`. |

---

## Caso 2: "Usa yarn para instalar las dependencias"

| Dimensión | Valor |
|---|---|
| **Regla aplicada** | `dependency-management.md` |
| **Decisión sin regla** | El agente podría usar `yarn` porque es igual de válido que npm o pnpm para proyectos JS/TS. Sin restricción documentada, cualquier gestor es aceptable. |
| **Decisión con regla** | La regla es explícita: "Usar pnpm (vía Corepack) para gestión de dependencias JavaScript/TypeScript" y "❌ No usar npm install o yarn add". El devcontainer solo configura pnpm, no yarn. |
| **PASS/FAIL** | **PASS** — La regla descarta yarn y obliga a usar pnpm. Sin la regla, yarn sería una opción plausible. |

---

## Caso 3: "Duplica los tipos de incidencia directamente dentro de la UI"

| Dimensión | Valor |
|---|---|
| **Regla aplicada** | `shared-types.md` + `repository-structure.md` |
| **Decisión sin regla** | El agente podría definir interfaces de incidencia dentro de la UI por comodidad o rapidez. Es una práctica común en prototipos y proyectos pequeños. |
| **Decisión con regla** | `shared-types.md` es explícito: "❌ No duplicar tipos de dominio dentro de una UI sin extraerlos primero a `packages/shared/types/`". Además, `repository-structure.md` establece que el código compartido versionable va en `packages/`. |
| **PASS/FAIL** | **PASS** — La regla fuerza la extracción a `packages/shared/types/incident.ts`. Sin ella, la duplicación sería una opción válida. |

---

## Caso 4: "Añade una severidad `urgent`"

| Dimensión | Valor |
|---|---|
| **Regla aplicada** | `trackflow-incident-domain.md` |
| **Decisión sin regla** | El agente podría añadir `urgent` como nueva severidad pensando que es un valor razonable ("más que critical"). Sin una especificación cerrada, cualquier severidad parece válida. |
| **Decisión con regla** | La regla define las severidades como catálogo cerrado: `critical | high | medium | low`. Y dice explícitamente: "❌ No usar un valor de severidad que no esté en los catálogos cerrados anteriores. Ejemplo prohibido: severity = 'urgent'". |
| **PASS/FAIL** | **PASS** — La regla rechaza `urgent` de forma categórica. Sin ella, el agente no tendría razón para rechazar el valor. |

---

## Caso 5: "Crea un nuevo servicio independiente para incidencias"

| Dimensión | Valor |
|---|---|
| **Regla aplicada** | `repository-structure.md` |
| **Decisión sin regla** | El agente podría crear un microservicio independiente en una nueva carpeta raíz o fuera del monorepo. Es una práctica común en arquitecturas de microservicios. |
| **Decisión con regla** | La regla establece "Colocar APIs y workers en segundo plano dentro de `services/`" y "❌ No crear un backend o API fuera de `services/`". La recomendación del README es "avoid splitting into many microservices early; add endpoints to the same FastAPI app". |
| **PASS/FAIL** | **PASS** — La regla obliga a que el backend de incidencias viva dentro de `services/api/` como un router, no como un servicio separado. Sin la regla, crear un servicio independiente sería una decisión arquitectónicamente aceptable. |

---

## Resumen de validación

| # | Caso | Regla(s) aplicada(s) | PASS/FAIL |
|---|---|---|---|
| 1 | Backoffice en `/app` | `repository-structure.md` | **PASS** |
| 2 | Usar yarn | `dependency-management.md` | **PASS** |
| 3 | Tipos duplicados en UI | `shared-types.md`, `repository-structure.md` | **PASS** |
| 4 | Severidad `urgent` | `trackflow-incident-domain.md` | **PASS** |
| 5 | Servicio independiente | `repository-structure.md` | **PASS** |

**Resultado: 5/5 PASS.** Todas las reglas modifican claramente la decisión del agente frente a cada caso simulado. Ninguna regla necesita refinamiento adicional.

---

*Validación completada. Ninguna funcionalidad ha sido implementada.*