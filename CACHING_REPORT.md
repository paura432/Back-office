# Auditoría de rendimiento y caching — TrackFlow

**Fecha:** 2026-10-23  
**Rama:** `feature/caching-optimisation`  
**Alcance:** auditoría y preparación; no se implementan cachés ni optimizaciones de frontend. La única modificación de runtime es instrumentación pasiva de duración HTTP descrita abajo.  
**Estado de la evidencia:** inventario de código y mediciones históricas verificables; en esta revisión se reconciliaron los conflictos UI. Los builds y tests runtime se intentaron, pero no pudieron ejecutarse porque faltan Node/npm y uv en el entorno.

## Resumen ejecutivo

Este repositorio no tiene actualmente endpoints GET de negocio operativos: los routers declaran listados y detalles, pero devuelven HTTP 501. Los únicos GET implementados son `/health` y `/status`; este último ejecuta un `SELECT 1` contra PostgreSQL. No hay métricas de tráfico real, latencias por ruta, esquema/tablas de negocio ni datos operativos que justifiquen un seeder. No se preparó ni ejecutó seed y no se accedió ni modificó producción.

El backoffice consulta `/api/status` inmediatamente y cada 15 segundos por pestaña abierta. El healthcheck de Compose consulta `/health` cada 5 segundos. Son las únicas frecuencias de llamada observables desde configuración del repositorio; no equivalen a frecuencia de usuarios ni a RPS de servidor.

### Línea base disponible

Las mediciones siguientes son **históricas**, tomadas de los informes versionados de la auditoría de frontend anterior (Lighthouse 12.8.2, Chrome 141, tres ejecuciones por escenario). No son mediciones de esta rama ni sustituyen una nueva corrida con la revisión actual. Se citan como referencia reproducible ya archivada:

| Escenario histórico | Performance mediana | LCP mediano | CLS mediano | TBT mediano | TTFB mediano | Evidencia |
|---|---:|---:|---:|---:|---:|---|
| Website desktop, baseline | 99 | 643.282 ms | 0.053153 | 0 ms | 4.141 ms | `audit/before/summary.json` |
| Website mobile, baseline | 92 | 2664.057 ms | 0.050702 | 98 ms | 3.113 ms | `audit/before/summary.json` |
| Backoffice desktop, baseline | 100 | 687.978 ms | 0.015558 | 0 ms | 5.646 ms | `audit/before/summary.json` |
| Backoffice mobile, baseline | 94 | 2588.299 ms | 0.022812 | 0 ms | 4.784 ms | `audit/before/summary.json` |
| Website desktop, auditoría posterior histórica | 99 | 645.060 ms | 0.053153 | 0 ms | 8.260 ms | `audit/after/summary.json` |
| Website mobile, auditoría posterior histórica | 92 | 2643.309 ms | 0.050702 | 118 ms | 8.616 ms | `audit/after/summary.json` |
| Backoffice desktop, auditoría posterior histórica | 100 | 688.388 ms | 0.015558 | 0 ms | 6.082 ms | `audit/after/summary.json` |
| Backoffice mobile, auditoría posterior histórica | 93 | 2602.723 ms | 0.022812 | 56.050 ms | 6.749 ms | `audit/after/summary.json` |

No se afirma mejora a partir de esas variaciones: los informes corresponden a una auditoría previa, con cambios de frontend distintos entre antes y después. El TTFB Lighthouse local no es latencia de endpoints backend ni carga de producción. TBT tampoco es INP. Para cache, faltan latencias y distribución reales por ruta.

## Evidencia de medición en esta auditoría

| Evidencia | Resultado observado | Interpretación / bloqueo |
|---|---|---|
| Rama inicial | `main`, HEAD `43b845b`; working tree limpio | Se creó la rama de trabajo desde `main`; no había cambios locales que preservar. Checkout identificado por Git como shallow/grafted. |
| Stack declarado y fuentes | Website y backoffice Next.js 16.4.0 / React 19.3.0 / TypeScript App Router; API FastAPI / Python 3.12; PostgreSQL 16 en Compose | Verificado en manifiestos, código y configuración. No hay caché existente identificada en el servicio. |
| Frontend: uso de API | `BackendStatus` llama inmediatamente y luego cada 15 s a `/api/status`; componente de cliente pequeño | Frecuencia configurada, no tráfico observado. El endpoint ejecuta query de DB: cachearlo ocultaría la salud actual y retrasaría la detección. |
| Healthcheck Compose | `/health` cada 5 s en servicio API | Frecuencia de healthcheck configurada. `/health` devuelve constante y no es candidato significativo a caché; está en ruta de monitorización. |
| GET de negocio | 18 rutas declaradas entre routers, todas con 501 según implementación y tests; 0 respuestas de negocio exitosas | Sin consultas de negocio ejecutables o latencias reales. No debe inferirse coste real de sus nombres/descripciones. |
| Runtime/testing disponible en la revisión de cierre | `python3 3.12.15`; `node`, `npm`, `uv` y `docker` no disponibles en PATH; no hay `node_modules` ni `.venv` locales. Hay `package-lock.json` para ambas UIs y `services/api/uv.lock` | Los comandos de build y pytest se intentaron, pero el shell respondió `npm: command not found` / `uv: command not found`; no se instalaron herramientas ni se alteraron locks. Compose y Lighthouse tampoco se pueden ejecutar. |
| Conflictos de UI | Eliminados los marcadores de los seis archivos solicitados y, con autorización expresa, de `uis/website/src/styles.css` y `uis/backoffice/src/styles.css` | Se conservaron los estilos `next/font`, los estilos responsive, `SiteHeader`, `BrandMark`, `DecorativeArrow` y `BackendStatus`. Los README describen el mecanismo `next/font` que usan los layouts. `git grep` no encuentra marcadores tras resolverlos. |
| Validaciones posibles | `python3 -m compileall -q services/api/main.py services/api/tests/test_timing.py`, `git diff --check` y búsqueda global de marcadores de conflicto | PASS. `get_errors` no detectó errores en los cuatro archivos TSX de app/layout/pages. Estas comprobaciones no sustituyen los builds ni pytest. |
| Instrumentación | Se añadió middleware en `services/api/main.py` que emite método, plantilla de ruta, status y `duration_ms`; prueba `services/api/tests/test_timing.py` | Cambio pasivo, no almacena datos ni registra query strings, IDs, tracking numbers o payloads. Sintaxis Python disponible; prueba runtime bloqueada por dependencias ausentes. |
| Datos/seeder | No se preparó ni ejecutó seed | No existen modelos/tablas de dominio implementados y las rutas son stubs. Inventar dataset o esquema produciría una línea base engañosa; no se tocaron datos de producción. |

### Reproducción pendiente

1. Usar un entorno local aislado de desarrollo con Docker Engine/Compose, Node 22 y uv 0.6.17; confirmar `docker compose config` y revisar que el `DATABASE_DSN`/variables apunten únicamente al servicio local de Compose. No apuntar a producción.
2. Instalar API según `services/api/README.md`: `uv sync --frozen --extra dev`; ejecutar `uv run --frozen --extra dev pytest -q`. Instalar/build de cada UI con sus locks (`npm ci`, `npm run build`).
3. Levantar exclusivamente el stack local con `docker compose up --build -d --wait`. Capturar versión de herramientas, commit, hardware/entorno y logs; solicitar cada GET varias veces en serie y concurrente, separar cold/warm, registrar status y latencia de cliente. El middleware proporciona duración de aplicación en logs; agregar percentiles p50/p95/p99 por ruta en el harness de medición (no deducirlos de una sola petición).
4. Ejecutar tres o más repeticiones de Lighthouse en desktop/móvil para website y backoffice con mismo Chrome, perfiles y build de producción. Guardar reportes nuevos sin sobreescribir `audit/before/` ni `audit/after/`.
5. Para medir datos de negocio, esperar a que se apruebe e implemente un esquema y endpoints funcionales. Si se autoriza un seeder, debe ser script local explícito, idempotente, con IDs/emails/direcciones ficticios reservados, entorno validado como local, y ninguna URL/credencial productiva. Medir endpoints funcionales antes y después de poblar solo esa DB local; eliminar el seed al terminar de acuerdo con el procedimiento del proyecto.

## Inventario de GET backend

Frecuencia y latencia real de servidor: **desconocidas/no medidas**, salvo configuración explícita del healthcheck y polling descrita arriba. Todos los GET que no sean `/health` y `/status` están declarados como stubs 501 y no tienen dependencias de datos actuales. “Dependencia candidata” describe lo que su contrato sugiere, no una conexión ya implementada.

| GET | Estado actual / dependencia observada | Frecuencia / latencia observada | Sensibilidad y decisión preliminar |
|---|---|---|---|
| `/health` | Implementado; respuesta constante `{"status":"ok"}`, sin DB | Compose healthcheck cada 5 s; latencia no medida | No cachear como endpoint de health: respuesta debe representar disponibilidad del proceso y la capa de monitorización ya controla la frecuencia. |
| `/status` | Implementado; ejecuta PostgreSQL `SELECT 1`, devuelve `operational` o `degraded` | Backoffice al montar y cada 15 s por pestaña; latencia no medida | No cachear inicialmente; contenido refleja disponibilidad dependiente del estado actual. Respuesta actual no contiene credenciales. |
| `/auth/me` | 501; perfil autenticado, user profile sin secretos por schema; autenticación aún no implementada | Desconocida; 0 RPS de negocio medidos | No cachear compartido. Si se implementa, cualquier cache deberá aislar identidad/sesión y tener invalidación de cambios de cuenta. |
| `/inventory/items` | 501; lista de stock; no hay DB/repositorio de inventario | Desconocida | Potencialmente cara/frecuente según futura operación; cantidades cambiantes y por almacén. Candidato condicional, cache corto y ámbito de tenant/almacén tras medición. |
| `/inventory/items/{sku}` | 501; detalle por SKU; sin almacenamiento | Desconocida | Misma sensibilidad de inventario; el stock tiene estabilidad baja. TTL muy corto o no cachear cantidad; separar metadatos estables solo en diseño futuro. |
| `/inventory/alerts` | 501; umbral y cantidad; sin dependencia implementada | Desconocida | No cachear alertas operativas desactualizadas; si se decide cache futuro, ventana mínima y tenant/almacén en clave. |
| `/orders/` | 501; listados con estado, fecha, cliente e items según schemas | Desconocida | Datos operativos/posible dirección de envío en detalle; no compartir entre clientes/tenants. Invalidar en creación/cambio de estado. |
| `/orders/{order_id}` | 501; detalle incluye dirección de envío, notas, items y estado | Desconocida | Sensibilidad alta; no cache compartido ni público. Requerir auth, tenant en clave y TTL mínimo si se aprueba. Invalidar en cada cambio. |
| `/shipments/` | 501; lista con tracking number, carrier, recipient, status | Desconocida | Puede incluir datos identificativos y estado volátil; aislar tenant y considerar no cachear por defecto. |
| `/shipments/{shipment_id}` | 501; detalle con destinatario, destino e historial de tracking | Desconocida | Sensibilidad alta y volatilidad alta; evitar cache compartido. Invalidación por eventos del transportista si se reconsidera. |
| `/shipments/tracking/{tracking_number}` | 501; tracking por número | Desconocida | No cachear en CDN/ámbito global: número de tracking puede permitir consultar estado y datos del destinatario. Si hay portal público, diseñar acceso y exposición mínima; TTL segundos/minutos solo tras análisis. |
| `/returns/` | 501; listado con order ID, SKU y estado | Desconocida | Datos vinculados a clientes, pedidos y reclamaciones; no cache compartido, invalidar en crear/aprobar/inspeccionar. |
| `/returns/{return_id}` | 501; detalle incluye motivo y notas de inspección | Desconocida | Sensibilidad alta; no cache público/compartido. En ámbito autenticado, invalidación obligatoria ante transiciones. |
| `/customers/` | 501; lista contiene empresa, email de contacto, país | Desconocida | Información de contacto/cliente; no cachear compartido entre tenants; invalidar cambios de perfil. |
| `/customers/{customer_id}` | 501; detalle incluye email, teléfono, dirección y notas | Desconocida | Información privada comercial/identificativa; no cache público. Tenant/usuario y TTL breve en cualquier futuro cache privado. |
| `/customers/{customer_id}/health` | 501; score/riesgo y fecha contractual | Desconocida | Dato comercial sensible, pero derivado potencialmente estable. Candidato solo después de medir; key por tenant+cliente+versión de datos, TTL inicialmente 5–15 min, invalidación al cambiar inputs. |
| `/users/` | 501; lista con email, rol y estado | Desconocida | Datos de cuentas/roles; no cache compartido. Invalidar inmediatamente al cambiar rol/estado. |
| `/users/{user_id}` | 501; detalle personal con email, rol y fecha de alta; sin contraseña en schema | Desconocida | Datos personales/cuenta; sólo cache privado y clave con tenant/usuario, si se permite. No cachear información de credenciales. |
| `/dashboard/executive` | 501; agregados propuestos de envíos, coste, retornos, clientes y satisfacción | Desconocida | Candidato principal futuro: agregación potencialmente costosa y compartible dentro de un tenant/ámbito autorizado; datos no necesariamente reales-time. Cache privado por tenant+país+filtros+versión, TTL de partida 1–5 min, invalidación/refresh por eventos relevantes. Contrastar freshness con “tiempo real” requerido. |
| `/dashboard/weekly-report` | 501; reporte semanal con resumen, highlights y métricas | Desconocida | Candidato futuro de alta estabilidad una vez cerrado el periodo; clave tenant+semana+zona horaria/país+versión. TTL hasta siguiente generación semanal (o 24 h con refresh al generar), invalidar/regenerar al corregir datos. No hay job implementado. |

**Nota de conteo:** 20 rutas GET de aplicación en total; 2 operativas y 18 stubs 501 (incluye `/auth/me`). Ningún endpoint funcional de negocio expone hoy datos de negocio. Framework OpenAPI/docs no se cuenta como ruta de aplicación de negocio.

## Frontend: análisis de coste y estabilidad

No se pudo generar un perfil React/Chrome actual. La inspección de código muestra páginas estáticas con arrays constantes definidos a nivel de módulo; no hay filtering, sorting, transformaciones grandes ni cálculos derivados dentro de render, por lo que envolver `services`, `teams` o `priorities` en `useMemo` no tiene beneficio demostrable y añade complejidad. Website `SiteHeader` es un Client Component pequeño por su estado de menú; el resto de página es Server Component en el estado de auditoría previo documentado. Backoffice renderiza arrays de cinco áreas/cuatro prioridades y un componente `BackendStatus` pequeño que hace polling. No hay paquetes de gráficos, tablas virtualizadas o dependencias de UI grandes identificadas en los manifiestos revisados.

| Candidato | Evidencia/coste observado | Prioridad para perfil | Recomendación previa a implementación |
|---|---|---|---|
| Website: ilustración CSS/red de la landing, ticker y secciones inferiores | Contenido principalmente HTML/CSS; no hay evidencia de bundle JS grande; arte en CSS/SVG inline. Lighthouse histórico mobile con TBT mediano 98 ms (baseline) y 118 ms en informe posterior, sin atribución probada a un componente | Media-baja | Medir JS transferido, long tasks y coste de render antes. No aplicar `dynamic()` por intuición; estudiar lazy loading solo si aparece módulo pesado real y fuera del contenido LCP. |
| Backoffice: listado de equipos y prioridades | 5 + 4 registros estáticos, arrays constantes fuera del componente | Baja | No usar `useMemo`: cálculo trivial y estable. Reevaluar si se conectan datasets grandes, filtros o tablas. |
| Website: lista de cuatro servicios | 4 registros estáticos y `map` pequeño | Baja | Sin necesidad actual de `useMemo` o lazy loading. |
| Backoffice: `BackendStatus` | Un fetch inicial y un intervalo cada 15 s; renderiza una etiqueta sencilla | Baja para cálculo/render, medible como carga de polling | No convertirlo en cache de `/status` sin aceptar explícitamente retraso de salud. Medir coste de red por número de pestañas; considerar consolidación/visibilidad sólo como futura optimización funcional separada. |

## Requisitos de la práctica 4Geeks (revisión de esta rama)

| Requisito solicitado | Estado en el código revisado | Decisión y evidencia |
|---|---|---|
| 2 casos de lazy loading | **Pendiente / no implementado** | No se identificaron módulos o componentes pesados separables; las páginas son HTML/CSS/SVG, las listas son pequeñas y `SiteHeader`/`BackendStatus` son componentes cliente pequeños. No se añadieron cargas diferidas artificiales. |
| 1 uso de `useMemo` | **Pendiente / no implementado** | No hay cálculos costosos derivados en render. `services`, `teams` y `priorities` son arrays pequeños constantes a nivel de módulo. Memoizar no aporta beneficio sustentado. |
| 2 endpoints con cache TTL e invalidación | **Pendiente / no implementado** | No existen dos GET de negocio funcionales: las 18 rutas correspondientes devuelven 501. `/health` y `/status` son endpoints de monitorización; cachearlos produciría salud atrasada. No se crearon endpoints ni se cachearon errores/stubs. Los candidatos documentados siguen siendo diseños condicionales y no cuentan como cumplimiento. |

**Conclusión:** no se satisface todavía el checklist técnico de la práctica. Cumplirlo requeriría inventar lazy loading/useMemo sin coste demostrado y activar caching sobre rutas no funcionales o añadir endpoints de negocio no autorizados. Recomendación: no presentar esta auditoría como implementación completa de los requisitos; solicitar aclaración funcional/aprobación de endpoints reales antes de intentar satisfacerlos. La decisión sobre abrir PR depende además de ejecutar builds y tests en un entorno equipado.

## Candidatos de caching priorizados (condicionales)

Todos son candidatos de **futuras implementaciones**, no endpoints cacheables hoy; las rutas asociadas responden 501.

| Prioridad | Recurso | Coste potencial | Frecuencia | Estabilidad | TTL inicial propuesto | Clave / ámbito | Invalidación | Razón / condición |
|---|---|---|---|---|---|---|---|---|
| 1 | `/dashboard/executive` | Alto potencial: agregación de varias métricas (hipótesis basada en contrato) | Desconocida; se espera uso de dashboard, sin dato real | Media; ventanas por país y agregados | 1–5 min, a validar contra frescura requerida | `dashboard:executive:{tenant}:{country}:{filters}:{data_version}`; backend privado, tenant autorizado | Eventos de pedido/envío/devolución/cliente o invalidación por versión; TTL como fallback | Mejor perfil coste/estabilidad si el query plan confirma agregación cara. No puede afirmarse hoy. |
| 2 | `/dashboard/weekly-report` | Potencialmente alto si agregación/generación de resumen; no existe job/LLM probado | Desconocida; contrato indica reporte semanal | Alta para semana cerrada, baja mientras semana abierta | Semana cerrada: hasta siguiente generación semanal; periodo abierto: no cachear o TTL corto | `dashboard:weekly:{tenant}:{week}:{timezone}:{data_version}`; acceso privado | Regeneración semanal y correcciones explícitas de datos | Gran estabilidad temporal tras cierre; primero definir job, calendario, correcciones y propiedad de datos. |
| 3 | `/inventory/items` (solo campos estables/listado) | Medio/alto solo con volumen real; no medido | Desconocida | Baja para quantity; mayor para descripciones estáticas | 5–30 s para stock, sujeto a SLA operativo; separar metadatos estables | `inventory:list:{tenant}:{warehouse}:{filters}:{version}`; interno/privado | Eventos de recepción, picking, ajuste, transferencia; TTL fallback | Frecuencia potencial en operaciones, pero stock desactualizado puede causar decisiones incorrectas. No cachear cifras hasta acordar tolerancia de staleness. |

**Candidato alternativo:** `/shipments/tracking/{tracking_number}` podría tener alta frecuencia, pero es de alta volatilidad y sensibilidad; no está entre los tres principales precisamente porque el riesgo de respuesta stale o exposición supera evidencia de beneficio. No cachear inicialmente.

## Endpoints/rutas que no cachear

- `/health`: monitorización de proceso; una respuesta cacheada puede declarar sano un proceso que ya no lo está.
- `/status`: depende de conectividad actual a PostgreSQL; cache de cualquier duración suprime la comprobación. Un cache separado con objetivo de disponibilidad distinto requeriría diseño explícito y señal visual etiquetada como stale.
- `/auth/me`, `/users/*`, `/customers/*`, `/orders/*`, `/returns/*`: requieren identidad/tenant y algunos incluyen email, teléfono, dirección, notas, motivos o roles. No usar cache público/compartido. No hay autorización implementada todavía.
- `/shipments/tracking/{tracking_number}` y detalles de envío: tracking number, destinatario, destino e historial; volatilidad alta y posible consulta pública. No usar cache global/CDN; revisar privacidad y autorización antes de implementar.
- `/inventory/alerts` y cantidad de inventario: la antigüedad puede afectar operación física; sin SLA de freshness y eventos de invalidación, dejar sin caché.
- Recomendaciones con datos de destino/peso, si en el futuro se exponen por GET: actualmente la recomendación es POST y 501. No cachear cuerpo sensible en infraestructura genérica sin diseño de clave y retención.

## Timing backend agregado

Se añadió middleware de medición en `services/api/main.py`: reloj monotónico alrededor de cada petición, log estructurado con método, plantilla de ruta, status y milisegundos con tres decimales. Se evita incluir URL raw, query string, path params, cabeceras, cuerpo, credenciales, tenant, IDs y tracking numbers. El middleware no retiene la respuesta, no altera status/body deliberadamente y no implementa cache. Se añadió prueba en `services/api/tests/test_timing.py` que verifica registro para `GET /health`; no se pudo ejecutar por ausencia de FastAPI/pytest. Aún no hay agregación p50/p95/p99 ni métricas exportables; recoger logs en un entorno de medición y reportar percentiles antes de seleccionar cache.

## Checks y limitaciones para el siguiente paso

- Build website intentado: `npm --prefix uis/website run build` → bloqueado (`npm: command not found`). Build backoffice intentado: `npm --prefix uis/backoffice run build` → bloqueado (`npm: command not found`). Tests intentados: `uv run --frozen --extra dev pytest -q` → bloqueado (`uv: command not found`). No se instalaron herramientas globales.
- `python3 -m compileall -q services/api/main.py services/api/tests/test_timing.py` (PASS), `git diff --check` (PASS) y búsqueda global de marcadores (sin resultados). `get_errors` informó sin errores en `website/app/{layout,page}.tsx` y `backoffice/app/{layout,page}.tsx`; estas comprobaciones no reemplazan builds de Next ni pytest.
- Los seis archivos pedidos (`uis/website/{README.md,app/layout.tsx,app/page.tsx}` y `uis/backoffice/{README.md,app/layout.tsx,app/page.tsx}`) se reconciliaron. Durante el grep se detectaron marcadores adicionales en ambos `src/styles.css`; con autorización expresa se resolvieron conservando la variante alineada con `next/font` y los estilos responsive. No quedan marcadores en `uis/`.
- No fue posible ejecutar `docker compose config/build/up`, Lighthouse ni perfiles de navegador: Docker/Node/npm no están instalados. No se midió una nueva baseline visual/rendimiento.
- No se editó `CONTEXT.md`, configuración, lockfiles ni variables de entorno. No se creó seed; no se ejecutaron consultas fuera del código ni se modificó DB local/productiva.

## Plan de implementación tras aprobación

1. Ejecutar los builds de ambos frontends y la suite backend en un entorno con dependencias de proyecto; corregir cualquier error que aparezca y luego guardar una nueva línea base de Lighthouse.
2. Aprobar contratos de negocio, autenticación, autorización/tenant, esquema y política de frescura antes de habilitar endpoints 501.
3. Medir con tráfico de prueba representativo, mínimo tres repeticiones por ruta, cold/warm, concurrencia, query plans y p50/p95/p99; registrar errores y tamaño de respuesta. No mezclar `health/status` con agregados de negocio.
4. Seleccionar candidatos por coste y repetición medidos; empezar por un agregado privado estable solo si hay mejora material, con estrategia de versionado/invalidation, límites de memoria, protección de stampede y pruebas de aislamiento.
5. Probar invalidación tras mutaciones relevantes, tenant/rol, país, filtros y errores; documentar freshness permitida y comportamiento ante backend/cache caídos.
6. Comparar antes/después con mismo hardware, dataset exclusivamente local/ficticio, build, tráfico y metodología; exigir resultado de corrección/privacidad y rendimiento, no solo hit ratio. Mantener endpoints de health y datos volátiles/sensibles fuera de caches compartidos.
