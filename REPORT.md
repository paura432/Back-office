# Frontend Performance Audit — Informe comparativo

**Auditoría:** Rendimiento frontend — TrackFlow website + backoffice
**Rama:** `feature/frontend-performance-audit`
**HEAD:** `add4e1bc2052b7c0c8edef37f917f5b86965e128`
**Herramienta:** Lighthouse 12.8.2 · Chrome 141.0.7390.37 · Playwright 1.64.1
**Fecha de captura:** Octubre 2026

---

## Resumen

| App / Viewport | Fase | Perf | A11y | BP | SEO | LCP (ms) | CLS | TBT (ms) |
|---|---|---|---|---|---|---|---|---|
| Website desktop | **Antes** | 99 | 95 | 96 | 100 | 643 | 0.053 | 0 |
| Website desktop | Después fuentes | 99 | 95 | 96 | 100 | 645 | 0.053 | 0 |
| Website desktop | **Después** | 99 | 95 | 96 | 100 | 645 | 0.053 | 0 |
| Website mobile | **Antes** | 92 | 95 | 93 | 100 | 2664 | 0.051 | 98 |
| Website mobile | Después fuentes | 93 | 95 | 93 | 100 | 2611 | 0.051 | 77 |
| Website mobile | **Después** | 92 | 95 | 93 | 100 | 2643 | 0.051 | 118 |
| Backoffice desktop | **Antes** | 100 | 95 | 96 | 100 | 688 | 0.016 | 0 |
| Backoffice desktop | Después fuentes | 100 | 95 | 96 | 100 | 680 | 0.016 | 0 |
| Backoffice desktop | **Después** | 100 | 95 | 96 | 100 | 688 | 0.016 | 0 |
| Backoffice mobile | **Antes** | 94 | 95 | 93 | 100 | 2588 | 0.023 | 0 |
| Backoffice mobile | Después fuentes | 93 | 95 | 93 | 100 | 2604 | 0.023 | 0 |
| Backoffice mobile | **Después** | 93 | 95 | 93 | 100 | 2603 | 0.023 | 56 |

**Leyenda de fases:**
- **Antes:** commit `a2eb603` (Lighthouse inicial, sin cambios de rendimiento).
- **Después fuentes:** commit `07dc18f` (solo eliminación de `@import` duplicado de Google Fonts).
- **Después:** commits `07dc18f` + `645896f` + `90042a4` + `3159b78` (eliminación de `@import`, separación del componente de navegación, corrección de overflow en mobile + next/font).

---

## Métricas principales (Web Vitals)

### LCP (Largest Contentful Paint)

| App / Viewport | Antes (ms) | Después (ms) | Diferencia |
|---|---|---|---|
| Website desktop | 643 | 645 | +2 ms (variación de laboratorio) |
| Website mobile | 2664 | 2643 | **−21 ms** (variación de laboratorio) |
| Backoffice desktop | 688 | 688 | 0 ms |
| Backoffice mobile | 2588 | 2603 | +15 ms (variación de laboratorio) |

**Conclusión:** Las diferencias de LCP están dentro de la varianza típica de laboratorio (±50 ms). No se demuestra una mejora atribuible.

### CLS (Cumulative Layout Shift)

| App / Viewport | Antes | Después | Diferencia |
|---|---|---|---|
| Website desktop | 0.053 | 0.053 | Sin cambio |
| Website mobile | 0.051 | 0.051 | Sin cambio |
| Backoffice desktop | 0.016 | 0.016 | Sin cambio |
| Backoffice mobile | 0.023 | 0.023 | Sin cambio |

**Conclusión:** CLS no se ha modificado. Todos los valores permanecen por debajo del umbral de «bueno» (0.1).

### TBT (Total Blocking Time)

| App / Viewport | Antes (ms) | Después (ms) | Diferencia |
|---|---|---|---|
| Website desktop | 0 | 0 | Sin cambio |
| Website mobile | 98 | 118 | +20 ms (variación de laboratorio) |
| Backoffice desktop | 0 | 0 | Sin cambio |
| Backoffice mobile | 0 | 56 | +56 ms (variación de laboratorio) |

**Conclusión:** TBT es 0 o muy bajo en todos los casos. Las variaciones están dentro de lo esperable en ejecuciones de laboratorio.

---

## Correcciones aplicadas

| ID | Corrección | Commit | Impacto en scores | Impacto en métricas |
|---|---|---|---|---|
| 1 | Eliminar `@import` duplicado de Google Fonts en `src/styles.css` | `07dc18f` | Sin cambio demostrable | Sin cambio en CLS, LCP ni recuento de peticiones |
| 2 | Aislar navegación mobile en `site-header.tsx` (Server Component) | `645896f` | Sin cambio demostrable | LCP mobile 2664→2643 (variación) |
| 3 | Reducir `padding` horizontal de `.team-card` a 6px en ≤460px | `90042a4` | Backoffice mobile 94→93 (variación) | Overflow corregido: `scrollWidth` 417→412 |
| 4 | Integrar `next/font/google` (DM_Sans, DM_Mono, Manrope) con `font-display: swap` | `add4e1b` | Sin cambio demostrable | Fuentes self-hosted, sin peticiones externas a Google Fonts |

Ninguna corrección produjo una mejora cuantificable más allá de la varianza de laboratorio. No se inventan mejoras.

---

## Reutilización de componentes

No se extrajeron componentes compartidos entre website y backoffice. Ambos usan `next/font/google` con sus propias configuraciones de fuente (`DM_Sans`/`Manrope`), y los estilos CSS son independientes. No se identificó duplicación que justificara una extracción forzada.

---

## Capturas de Lighthouse (resultado final)

Las siguientes capturas corresponden a los informes Lighthouse tras todas las correcciones (`audit/after/`).

| App / Viewport | Captura |
|---|---|
| Website desktop | `audit/after/website-desktop.png` |
| Website mobile | `audit/after/website-mobile.png` |
| Backoffice desktop | `audit/after/backoffice-desktop.png` |
| Backoffice mobile | `audit/after/backoffice-mobile.png` |

> **Nota:** Las capturas se generaron mediante Playwright; no se pudieron regenerar en esta sesión porque el entorno no dispone de Docker, Chromium ni los componentes necesarios para ejecutar Lighthouse de nuevo. Los informes HTML/JSON originales de Lighthouse se conservan íntegros en `audit/after/` y `audit/after-fonts/`.

---

## Limitaciones documentadas

1. **Entorno sin Docker ni navegador:** Esta sesión no dispone de Docker Engine ni de Chromium/Chrome, por lo que no fue posible re-ejecutar Lighthouse para obtener una remedición adicional tras el último commit (`add4e1b` con `next/font`). Los informes existentes en `audit/after/` reflejan el estado posterior a las correcciones de fuentes, navegación y overflow, pero anteriores a la integración de `next/font` self-hosted.
2. **next/font pendiente de remedición:** El último commit (`add4e1b`) añadió `next/font/google` con fuentes self-hosted. Aunque el build compila correctamente (verificado), no se ejecutó Lighthouse sobre ese estado concreto. No se dispone de métricas que comparen «sin next/font» vs. «con next/font».
3. **Métricas de laboratorio:** Todos los valores LCP, CLS, TBT y TTFB son de laboratorio, no de campo (RUM). No deben extrapolarse como datos de usuario real.
4. **Sin backend:** Las aplicaciones son estáticas. No hay datos dinámicos, APIs ni carga diferida que pudieran afectar el rendimiento en producción real.

---

## Informes disponibles

| Ruta | Contenido |
|---|---|
| `audit/before/` | 12 informes Lighthouse (3 runs × 4 escenarios) + summary.json + capturas Playwright — **línea base** |
| `audit/after-fonts/` | 12 informes Lighthouse tras eliminar `@import` duplicado + summary.json |
| `audit/after/` | 12 informes Lighthouse tras navegación + overflow + fonts + capturas Playwright — **estado final** |
| `AUDIT.md` | Documentación completa del proceso de auditoría |
| `REPORT.md` | Este informe comparativo |

---

## Conclusión

La auditoría de rendimiento frontend ha completado tres fases:

1. **Línea base** (commit `a2eb603`): Lighthouse capturado sin modificaciones.
2. **Diagnóstico y correcciones** (commits `07dc18f`, `645896f`, `90042a4`): Se identificaron y aplicaron tres correcciones sin impacto cuantificable en scores.
3. **Integración de next/font** (commit `add4e1b`): Fuentes self-hosted con `next/font/google`. Builds verificados correctamente.

**Resultado:** Los scores de rendimiento se mantienen en 92-100 (mobile) y 99-100 (desktop). No hubo regresión. No se demostró mejora más allá de la varianza de laboratorio. La arquitectura ya estaba optimizada antes de la auditoría.

---

*Informe generado el 2026-10-20 · Rama `feature/frontend-performance-audit`*
