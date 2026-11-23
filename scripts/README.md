# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

> _Spanish version: [README.es.md](./README.es.md)._

## `train_sales_forecast.py`

Trains and evaluates the monthly revenue forecast (Random Forest on 2016-2023, tested on 2024-2025) and writes metrics, predictions and charts to `data/eval/sales_forecast/`. Dependencies are declared inside the script (inline metadata, managed with `uv add --script`) and pinned in `train_sales_forecast.py.lock`, so it needs neither a root `pyproject.toml` nor `pip`. Run from the repository root, no parameters:

```sh
uv run scripts/train_sales_forecast.py
```

The choice of algorithm is justified in the script header; results and metric explanations in `data/eval/sales_forecast/README.md`.
