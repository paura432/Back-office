# `data/process` folder

This folder contains **processed/intermediate data** and/or artifacts produced by pipelines (for example: clean datasets, features, aggregates, intermediate tables, or transformation outputs).

- **Main purpose**: clearly separate “raw” data from data ready for analysis, modeling, or app consumption.
- **Recommendation**: document which pipeline produces each artifact, its schema, refresh cadence, and how quality is validated (checks, constraints, data tests).

> _Spanish version: [README.es.md](./README.es.md)._

## `business_kpis.py`

Pure pandas transformations of the business performance pipeline (`data/pipelines/pipeline.py`): event validation and natural-key dedupe, country of returns, KPIs as numerator and denominator, statuses, recompute window, quality signals and weekly aggregation. No database access. It is a script rather than a dataset because the pipeline brief asks for reusable transformation scripts in `data/process/`. Tests in `data/pipelines/tests/test_business_kpis.py`.
