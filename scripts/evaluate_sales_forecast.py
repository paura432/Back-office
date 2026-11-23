# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "matplotlib==3.11.2",
#     "numpy==2.5.5",
#     "pandas==3.1.1",
#     "scikit-learn==1.9.1",
#     "scipy==1.18.1",
#     "statsmodels==0.15.0",
# ]
# ///
"""Evaluación técnica del pronóstico de ingresos de TrackFlow antes de su paso a staging.

Responde al ticket de evaluación con evidencia: validación cruzada temporal
sobre los años de entrenamiento (2016-2023), curva de aprendizaje, MAE y RMSE
de entrenamiento y validación, y la comparación de posibles acciones
correctivas. Los años de prueba (2024-2025) no se usan en ningún paso.

Desde la raíz del monorepo:

    uv run scripts/evaluate_sales_forecast.py

Escribe ``data/eval/learning_curve.png`` y ``data/eval/sales_forecast/evaluation_cv.json``.
El reporte con el diagnóstico está en ``data/eval/evaluation_report.md``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.model_selection import TimeSeriesSplit  # noqa: E402
from statsmodels.tsa.seasonal import seasonal_decompose  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.process.sales_forecast_features import (  # noqa: E402
    MODEL_FEATURES,
    MODEL_TARGET,
    TARGET,
    add_time_features,
    load_sales,
    split_train_test,
    time_series_folds,
)
from scripts.train_sales_forecast import RF_PARAMS, make_model  # noqa: E402

DATA = ROOT / "data" / "raw" / "trackflow_sales.csv"
EVAL = ROOT / "data" / "eval"
N_SPLITS = 5
FOLD_MONTHS = 12  # cada fold valida un año natural completo, con su pico y su valle
CURVE_VALIDATION_YEAR = 2023  # último año de entrenamiento; 2024-2025 no se tocan
CURVE_SIZES = range(12, 73, 6)

# Variantes que se comparan como posible acción correctiva (solo con CV).
CANDIDATES = {
    "actual": {"features": MODEL_FEATURES, "params": {}},
    "min_samples_leaf=5": {"features": MODEL_FEATURES, "params": {"min_samples_leaf": 5}},
    "min_samples_leaf=10": {"features": MODEL_FEATURES, "params": {"min_samples_leaf": 10}},
    "max_depth=3": {"features": MODEL_FEATURES, "params": {"max_depth": 3}},
    "max_features=0.5": {"features": MODEL_FEATURES, "params": {"max_features": 0.5}},
    "sin lags cortos ni rolling_std": {
        "features": ["lag_12_rel", "rolling_mean_3_rel", "month_sin", "month_cos"], "params": {}},
    "solo lag_12 y mes": {"features": ["lag_12_rel", "month_sin", "month_cos"], "params": {}},
}


def errors(frame: pd.DataFrame, rel_pred: np.ndarray) -> dict:
    """MAE y RMSE en EUR y en % del ingreso medio, más cuánto y cuánto se subestima."""
    pred = rel_pred * frame["rolling_mean_12"].to_numpy()
    actual = frame[TARGET].to_numpy()
    err = actual - pred  # > 0: el modelo se queda corto (subestima)
    mean = actual.mean()
    under = err[err > 0]
    return {
        "mae_eur": float(np.abs(err).mean()),
        "rmse_eur": float(np.sqrt((err ** 2).mean())),
        "mae_pct": float(np.abs(err).mean() / mean * 100),
        "rmse_pct": float(np.sqrt((err ** 2).mean()) / mean * 100),
        "under_share": float((err > 0).mean()),
        "under_mean_eur": float(under.mean()) if len(under) else 0.0,
        "worst_under_eur": float(err.max()),
    }


def check_folds(train: pd.DataFrame, folds) -> None:
    """Orden cronológico, sin barajar, idéntico a TimeSeriesSplit y sin fuga de features."""
    sk = list(TimeSeriesSplit(n_splits=N_SPLITS, test_size=FOLD_MONTHS).split(train))
    assert all(np.array_equal(a, c) and np.array_equal(b, d) for (a, b), (c, d) in zip(folds, sk))
    assert train["month"].is_monotonic_increasing
    for tr, va in folds:
        assert np.all(np.diff(tr) == 1) and np.all(np.diff(va) == 1)
        assert train["month"].iloc[tr].max() < train["month"].iloc[va].min()

    # Los features se calculan sobre la serie completa, pero son causales: si se
    # borra todo lo que hay desde el inicio de cada fold de validación, las filas
    # de entrenamiento de ese fold quedan idénticas.
    raw = load_sales(DATA)
    full = add_time_features(raw).set_index("month")
    cols = MODEL_FEATURES + [MODEL_TARGET]
    for tr, va in folds:
        cut = train["month"].iloc[va[0]]
        truncated = raw.copy()
        truncated.loc[truncated["month"] >= cut, TARGET] = np.nan
        recomputed = add_time_features(truncated).set_index("month")
        months = train["month"].iloc[tr]
        pd.testing.assert_frame_equal(full.loc[months, cols], recomputed.loc[months, cols])


def cross_validate(train: pd.DataFrame, folds, features, params) -> list[dict]:
    rows = []
    for i, (tr, va) in enumerate(folds, start=1):
        fit_rows, val_rows = train.iloc[tr], train.iloc[va]
        model = make_model(**params).fit(fit_rows[features], fit_rows[MODEL_TARGET])
        rows.append({
            "fold": i,
            "train_months": f"{fit_rows['month'].min():%Y-%m}..{fit_rows['month'].max():%Y-%m}",
            "validation_months": f"{val_rows['month'].min():%Y-%m}..{val_rows['month'].max():%Y-%m}",
            "n_train": len(tr),
            "train": errors(fit_rows, model.predict(fit_rows[features])),
            "validation": errors(val_rows, model.predict(val_rows[features])),
        })
    return rows


def summarize(rows: list[dict]) -> dict:
    out = {}
    for part in ("train", "validation"):
        for metric in rows[0][part]:
            values = np.array([r[part][metric] for r in rows])
            out[f"{part}_{metric}"] = {"mean": float(values.mean()), "std": float(values.std(ddof=1))}
    return out


def learning_curve(train: pd.DataFrame) -> list[dict]:
    """Error de entrenamiento y de validación según crece el entrenamiento.

    La validación es fija (2023). Cada punto entrena con los ``n`` meses
    inmediatamente anteriores, de 12 a 72 (todo lo disponible desde 2017).
    """
    val = train[train["month"].dt.year == CURVE_VALIDATION_YEAR]
    before = train[train["month"].dt.year < CURVE_VALIDATION_YEAR]
    points = []
    for n in CURVE_SIZES:
        fit_rows = before.iloc[-n:]
        model = make_model().fit(fit_rows[MODEL_FEATURES], fit_rows[MODEL_TARGET])
        points.append({"n_train": n, "train": errors(fit_rows, model.predict(fit_rows[MODEL_FEATURES])),
                       "validation": errors(val, model.predict(val[MODEL_FEATURES]))})
    return points


def noise_floor(raw: pd.DataFrame, train_end: pd.Timestamp) -> float:
    """Desviación típica del residuo de la descomposición (2016-2023), en %.

    Es la parte del ingreso mensual que ni la tendencia ni la estacionalidad
    explican: un error de entrenamiento muy por debajo indica que el modelo
    está aprendiendo ese ruido.
    """
    series = raw.set_index("month")[TARGET]
    resid = seasonal_decompose(series[series.index < train_end], model="multiplicative", period=12).resid
    return float((resid.dropna() - 1).std() * 100)


def plot_curve(points: list[dict], floor: float) -> None:
    sizes = [p["n_train"] for p in points]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharex=True)
    for ax, metric, label in [(axes[0], "rmse_pct", "RMSE"), (axes[1], "mae_pct", "MAE")]:
        ax.plot(sizes, [p["train"][metric] for p in points], marker="o", label="entrenamiento")
        ax.plot(sizes, [p["validation"][metric] for p in points], marker="o", label=f"validación ({CURVE_VALIDATION_YEAR})")
        if metric == "rmse_pct":
            ax.axhline(floor, color="0.5", ls="--", lw=1, label=f"ruido de la serie ({floor:.1f} %)")
        ax.set(title=f"{label} en % del ingreso mensual medio", xlabel="meses de entrenamiento",
               ylabel=f"{label} (%)", ylim=(0, None))
        ax.set_xticks(sizes)
        ax.grid(alpha=0.3)
        ax.legend()
    fig.suptitle("Curva de aprendizaje del Random Forest de ingresos (TrackFlow)")
    fig.tight_layout()
    fig.savefig(EVAL / "learning_curve.png", dpi=120)
    plt.close(fig)


def main() -> None:
    raw = load_sales(DATA)
    train, _ = split_train_test(add_time_features(raw))  # el conjunto de prueba no se usa
    train = train.reset_index(drop=True)
    folds = time_series_folds(len(train), N_SPLITS, FOLD_MONTHS)
    check_folds(train, folds)

    cv = {name: cross_validate(train, folds, c["features"], c["params"]) for name, c in CANDIDATES.items()}
    curve = learning_curve(train)
    floor = noise_floor(raw, pd.Timestamp("2024-01-01"))
    plot_curve(curve, floor)

    result = {
        "model": {**RF_PARAMS, "features": MODEL_FEATURES},
        "cv": {"strategy": f"TimeSeriesSplit(n_splits={N_SPLITS}, test_size={FOLD_MONTHS})",
               "checks": ["orden cronológico", "sin barajar", "igual a TimeSeriesSplit",
                          "features de train invariantes al borrar desde el fold de validación"],
               "folds": cv["actual"], "summary": summarize(cv["actual"])},
        "candidates": {name: {"features": CANDIDATES[name]["features"], "params": CANDIDATES[name]["params"],
                              "summary": summarize(rows)} for name, rows in cv.items()},
        "learning_curve": {"validation_year": CURVE_VALIDATION_YEAR, "points": curve},
        "noise_floor_pct": floor,
    }
    out = EVAL / "sales_forecast" / "evaluation_cv.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    print(f"CV {N_SPLITS} folds (un año cada uno, 2019-2023), media ± desviación:")
    for name, rows in cv.items():
        s = summarize(rows)
        print(f"  {name:32s} train RMSE {s['train_rmse_pct']['mean']:.2f} % | val RMSE"
              f" {s['validation_rmse_pct']['mean']:.2f} ± {s['validation_rmse_pct']['std']:.2f} % | val MAE"
              f" {s['validation_mae_pct']['mean']:.2f} ± {s['validation_mae_pct']['std']:.2f} %")
    print(f"Ruido de la serie: {floor:.2f} % | curva: " + ", ".join(
        f"{p['n_train']}m {p['train']['rmse_pct']:.2f}/{p['validation']['rmse_pct']:.2f}" for p in curve))
    print(f"Escrito {out.relative_to(ROOT)} y data/eval/learning_curve.png")


if __name__ == "__main__":
    main()
