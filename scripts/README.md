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

## `evaluate_sales_forecast.py`

Evaluates the same Random Forest (it imports `make_model` from `train_sales_forecast.py`) with time-series cross-validation (`TimeSeriesSplit`, 5 folds of one calendar year on 2017-2023), a learning curve and candidate corrective actions; the 2024-2025 test years are never used. Checks that the folds keep chronological order and that lag/rolling features do not leak across fold boundaries. Writes `data/eval/learning_curve.png` and `data/eval/sales_forecast/evaluation_cv.json`; the diagnosis is in `data/eval/evaluation_report.md`. Dependencies inline, pinned in `evaluate_sales_forecast.py.lock`:

```sh
uv run scripts/evaluate_sales_forecast.py
```
