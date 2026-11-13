# Validación del pipeline de desempeño de negocio

- `runs/` (no se versiona): resumen JSON de cada corrida, escrito por la task no crítica `export_eval_snapshot` de `data/pipelines/pipeline.py`. Si esa task falla, la corrida sigue `completed`.
- `evidence/`: salidas de las comprobaciones del 2026-11-06 sobre el Supabase local.

| Archivo | Qué muestra |
|---|---|
| `evidence/local-runs-real-data.txt` | Dos corridas de `python data/pipelines/pipeline.py` sobre la base `postgres` con los datos reales. Como ningún evento de negocio se emite todavía, las 84 filas (6 KPIs × 7 días × 2 países) salen `not_instrumented`. La segunda corrida reutiliza la transformación (`Cached`) y deja las 84 filas `unchanged` |
| `evidence/api-manual-runs.txt` | `POST /reporting/pipeline/runs` contra la API local, el servidor de Prefect y el deployment servido: 202 con el `run_id`, 409 con el mismo `run_id` mientras esperaba turno, 202 tras un evento tardío y 503 con Prefect parado (1,5 s) |
| `evidence/status-after.json` | `GET /reporting/pipeline/status` tras la primera corrida disparada por la API (751 eventos sintéticos, 19 duplicados descartados, 337 filas) |
| `evidence/kpis-week-US.json`, `evidence/kpis-day-ES.json` | `GET /reporting/kpis` por semana ISO (EE. UU.) y por día (España). Las cifras semanales de EE. UU. coinciden con un recuento independiente sobre el JSONL de entrada: 55 envíos, 45/58 a tiempo, 9/58 devoluciones, 1.239,38 USD, 3,521466 USD/kg y 61/15 de satisfacción |
| `evidence/run-late.json` | `GET /reporting/pipeline/runs/{run_id}` de la corrida tras insertar un `shipment_created` del 2026-10-26: ventana ampliada al 26, `late_days_detected = 1`, 1 fila actualizada y 301 sin cambios. La fila pasó de 3 a 4 envíos con `revision = 2` y la versión publicada quedó en `executive_kpis_daily_history` |
| `evidence/db-outage-retry.txt` | Caída real de Postgres (`docker pause` 6 s): `register_run` falla con `ConnectionTimeout`, Prefect lo reintenta a los 10 s y la corrida termina `completed` |

Los datos de la API y de la caída son eventos sintéticos en la base `telemetry_test` (ver `data/raw/business_performance/README.md`), no datos de producción.
