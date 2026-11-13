# Eventos sintéticos del pipeline de desempeño de negocio

Ningún evento fuente de los KPIs ejecutivos se emite todavía, así que el pipeline se prueba con eventos generados por `data/pipelines/business_performance/synthetic.py`. Siguen el contrato `docs/telemetry/event-schemas.json`, tienen la forma de las filas de `public.telemetry_events` y no contienen datos personales.

`synthetic_events.jsonl` (no se versiona) es la copia de lo que se insertó en `telemetry_test` para las evidencias de `data/eval/business_performance/`. Se regenera igual, porque el generador es determinista:

```sh
uv run --project data/pipelines python -m data.pipelines.business_performance.synthetic \
  --start 2026-10-24 --end 2026-11-06 --jsonl data/raw/business_performance/synthetic_events.jsonl
```

Con `--start 2026-10-24 --end 2026-11-06` salen 751 eventos: 247 `shipment_created` (con reenvíos del mismo envío), 228 `order_created`, 191 `shipment_delivered` (algunas sin coste), 25 `return_requested` y 60 `customer_satisfaction_submitted` (algunas sin país).
