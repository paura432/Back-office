# Carpeta `data/raw`

Esta carpeta está pensada para almacenar **datos en bruto** (raw) relacionados con la compañía: dumps, exports, archivos de ejemplo, muestras de eventos, o datasets sin transformar.

- **Propósito principal**: servir como zona de aterrizaje o referencia de datos originales antes de ser procesados por pipelines.
- **Recomendación**: documenta el origen de cada dataset, formato, tamaño esperado, consideraciones de privacidad/PII y cómo se versiona (idealmente evitando subir datos sensibles al repositorio).

## `trackflow_sales.csv`

Ingresos mensuales consolidados de TrackFlow de 2016-01 a 2025-12 (120 filas, 5,8 KB), usados por el pronóstico de ventas (`scripts/train_sales_forecast.py`). Copia sin cambios de `content/contexts/sales-forecasting/trackflow/trackflow_sales.csv` del syllabus de AI Engineering de 4Geeks (SHA-256 `2b8c782e…7d2f4c33`). Las columnas y los patrones están descritos en el `trackflow-BRIEFING` de esa carpeta: `month`, `revenue_eur`, `shipments_processed`, `avg_revenue_per_shipment_eur`, `market` (solo `consolidated`). Datos sintéticos y agregados, sin información personal.
