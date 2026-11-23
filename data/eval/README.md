# `data/eval` folder

This folder is for **evaluation and validation**: evaluation datasets, golden sets, experiment results, metrics, and artifacts used to measure quality for models, RAG, agents, or pipelines.

- **Main purpose**: centralize evaluation inputs and outputs so improvements stay measurable across project milestones.
- **Recommendation**: document each evaluation set (what it measures, how it was built, success criteria) and avoid sensitive data; use synthetic or anonymized data when needed.

> _Spanish version: [README.es.md](./README.es.md)._

## Sales forecast evaluation

- `evaluation_report.md`: technical evaluation of the revenue forecast (`scripts/train_sales_forecast.py`) before staging: time-series cross-validation, learning curve, MAE/RMSE on training and validation, diagnosis (moderate overfitting) and the proposed corrective action. Generated numbers come from `scripts/evaluate_sales_forecast.py`.
- `learning_curve.png`: training and validation error as the training window grows (validation year 2023).
- `sales_forecast/`: results of the forecast on the 2024-2025 test years (`README.md`) and the cross-validation detail (`evaluation_cv.json`).
