# `data/raw` folder

This folder is intended for **raw data** related to the company: dumps, exports, sample files, event samples, or untransformed datasets.

- **Main purpose**: serve as a landing zone or reference for original data before pipelines process it.
- **Recommendation**: document each dataset’s origin, format, expected size, privacy/PII considerations, and how it is versioned (ideally avoiding sensitive data in the repository).

> _Spanish version: [README.es.md](./README.es.md)._

## `trackflow_sales.csv`

Monthly consolidated revenue of TrackFlow, 2016-01 to 2025-12 (120 rows, 5.8 KB), used by the sales forecast (`scripts/train_sales_forecast.py`). Unmodified copy of `content/contexts/sales-forecasting/trackflow/trackflow_sales.csv` from the 4Geeks AI Engineering syllabus (SHA-256 `2b8c782e…7d2f4c33`). Columns and patterns are described in that folder's `trackflow-BRIEFING`: `month`, `revenue_eur`, `shipments_processed`, `avg_revenue_per_shipment_eur`, `market` (only `consolidated`). Synthetic, aggregated data with no personal information.
