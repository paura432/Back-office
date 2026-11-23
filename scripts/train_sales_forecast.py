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
"""Entrena y evalúa el modelo de pronóstico de ingresos mensuales de TrackFlow.

Lee ``data/raw/trackflow_sales.csv``, entrena un Random Forest con los
primeros 8 años (2016-2023) y lo evalúa sobre los 2 más recientes (2024-2025),
que el modelo no ve durante el entrenamiento. Escribe métricas, predicciones y
gráficos en ``data/eval/sales_forecast/``.

Desde la raíz del monorepo:

    uv run scripts/train_sales_forecast.py

Las dependencias están declaradas en este mismo archivo (bloque ``script``,
gestionado con ``uv add --script``) y fijadas en ``train_sales_forecast.py.lock``.

Por qué Random Forest y no XGBoost
----------------------------------
- Tamaño de datos: hay 84 meses útiles para entrenar (2017-2023; 2016 se usa
  solo como historia de los lags). XGBoost corrige errores árbol a árbol y, con
  tan pocas filas, se ajusta al ruido si no se le ponen tasa de aprendizaje,
  profundidad y regularización cuidadas; Random Forest promedia árboles
  independientes y es estable con valores casi por defecto.
- Tiempo para ajustar: con 84 filas no hay margen para reservar una
  validación fiable donde tunear los hiperparámetros de XGBoost. Random Forest
  da además un error fuera de bolsa (OOB) gratis, que usamos para construir la
  banda de variabilidad sin tocar los años de prueba.
- Explicabilidad: a Finanzas se le puede contar como «500 árboles que miran los
  meses anteriores y el mes del año, y se promedia lo que dicen», con la
  importancia de cada feature. La serie tiene un patrón estacional claro y
  pocas variables: la precisión extra que suele dar XGBoost no compensa aquí
  perder esa explicación.
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
from scipy import stats  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error  # noqa: E402
from statsmodels.tsa.seasonal import seasonal_decompose  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # para importar data.process como en el resto del monorepo

from data.process.sales_forecast_features import (  # noqa: E402
    MODEL_FEATURES,
    MODEL_TARGET,
    TARGET,
    add_time_features,
    load_sales,
    split_train_test,
)

DATA = ROOT / "data" / "raw" / "trackflow_sales.csv"
OUT = ROOT / "data" / "eval" / "sales_forecast"
SEED = 42
BAND = (0.10, 0.90)  # banda del 80 %
PSI_BINS = 5


def psi(expected: pd.Series, actual: pd.Series, bins: int = PSI_BINS) -> float:
    """Population Stability Index con cortes por cuantiles de ``expected`` (train)."""
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.histogram(expected, edges)[0] / len(expected)
    a = np.histogram(actual, edges)[0] / len(actual)
    e, a = np.clip(e, 1e-4, None), np.clip(a, 1e-4, None)
    return float(np.sum((a - e) * np.log(a / e)))


def normalized_gini(actual: np.ndarray, pred: np.ndarray) -> float:
    """Gini normalizado: 1 si el modelo ordena los meses igual que la realidad."""

    def gini(a, p):
        order = np.lexsort((np.arange(len(a)), -p))
        cum = np.cumsum(a[order]) / a.sum()
        return cum.sum() / len(a) - (len(a) + 1) / (2 * len(a))

    return float(gini(actual, pred) / gini(actual, actual))


def scores(actual: pd.Series, pred: pd.Series) -> dict:
    mse = mean_squared_error(actual, pred)
    resid = actual - pred
    k2, k2_p = stats.normaltest(resid)
    return {
        "mse_eur2": mse,
        "rmse_eur": float(np.sqrt(mse)),
        "rmse_pct_mean_revenue": float(np.sqrt(mse) / actual.mean() * 100),
        "mae_eur": mean_absolute_error(actual, pred),
        "mape_pct": mean_absolute_percentage_error(actual, pred) * 100,
        "bias_eur": float((pred - actual).mean()),
        "gini": normalized_gini(actual.to_numpy(), pred.to_numpy()),
        "k2_stat": float(k2),
        "k2_pvalue": float(k2_p),
    }


def decomposition(df: pd.DataFrame, train_end: pd.Timestamp) -> dict:
    """Descompone la serie de entrenamiento y la contrasta con el BRIEFING."""
    series = df.set_index("month")[TARGET]
    dec = seasonal_decompose(series[series.index < train_end], model="multiplicative", period=12)
    index = dec.seasonal.iloc[:12].set_axis(range(1, 13))
    # El BRIEFING habla de alzas y caídas «respecto al promedio»: lo comparamos
    # con la media de los meses que no son ni el pico (nov-dic) ni el valle (feb).
    normal = index.drop([2, 11, 12]).mean()
    yearly = series.groupby(series.index.year).sum()

    fig = dec.plot()
    fig.set_size_inches(11, 8)
    fig.suptitle("Descomposición multiplicativa de revenue_eur (2016-2023)", y=1.0)
    fig.tight_layout()
    fig.savefig(OUT / "decomposition.png", dpi=120)
    plt.close(fig)

    return {
        "seasonal_index_pct": ((index - 1) * 100).round(1).to_dict(),
        "vs_normal_months_pct": {
            "nov": round((index[11] / normal - 1) * 100, 1),
            "dec": round((index[12] / normal - 1) * 100, 1),
            "feb": round((index[2] / normal - 1) * 100, 1),
            "other_months_range": [round((index.drop([2, 11, 12]) / normal - 1).min() * 100, 1),
                                   round((index.drop([2, 11, 12]) / normal - 1).max() * 100, 1)],
        },
        "annual_growth_pct": (yearly.pct_change() * 100).round(2).dropna().to_dict(),
    }


def recursive_forecast(model: RandomForestRegressor, df: pd.DataFrame, test_months: pd.Series) -> pd.Series:
    """Pronóstico a 24 meses vista: cada predicción ocupa el lugar del dato real.

    Es el escenario de presupuestar los dos años enteros a 31 de diciembre de
    2023, sin ir conociendo los meses reales de 2024-2025.
    """
    history = df[["month", TARGET]].copy()
    history.loc[history["month"].isin(test_months), TARGET] = np.nan
    for month in test_months:
        row = add_time_features(history).loc[history["month"] == month]
        rel = model.predict(row[MODEL_FEATURES])[0]
        history.loc[history["month"] == month, TARGET] = rel * row["rolling_mean_12"].iloc[0]
    return history.set_index("month").loc[test_months, TARGET]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    raw = load_sales(DATA)
    df = add_time_features(raw)
    train, test = split_train_test(df)
    print(f"train {train['month'].min():%Y-%m}..{train['month'].max():%Y-%m} ({len(train)} meses útiles)"
          f" | test {test['month'].min():%Y-%m}..{test['month'].max():%Y-%m} ({len(test)} meses)")

    decomp = decomposition(raw, test["month"].min())

    model = RandomForestRegressor(n_estimators=500, min_samples_leaf=2, oob_score=True,
                                  random_state=SEED, n_jobs=1)
    model.fit(train[MODEL_FEATURES], train[MODEL_TARGET])

    # Predicción mes a mes: para cada mes de prueba el modelo usa los meses
    # reales anteriores, como pasaría al cerrar cada mes. No se reentrena.
    level = test["rolling_mean_12"]
    pred = pd.Series(model.predict(test[MODEL_FEATURES]) * level, index=test.index)

    # Banda de variabilidad: cuantiles del error relativo fuera de bolsa (OOB)
    # en entrenamiento, aplicados a cada predicción. No mira los años de prueba.
    oob_pred = model.oob_prediction_ * train["rolling_mean_12"]
    rel_err = train[TARGET] / oob_pred - 1
    lo_q, hi_q = np.quantile(rel_err, BAND)
    lower, upper = pred * (1 + lo_q), pred * (1 + hi_q)
    inside = ((test[TARGET] >= lower) & (test[TARGET] <= upper)).mean()

    recursive = recursive_forecast(model, raw, test["month"]).set_axis(test.index)
    lo_r, hi_r = recursive * (1 + lo_q), recursive * (1 + hi_q)
    seasonal_naive = test["lag_12"]
    naive_growth = test["lag_12"] * test["rolling_mean_12"] / df["rolling_mean_12"].shift(12).loc[test.index]

    actual = test[TARGET]
    metrics = {
        "split": {"train_months_used": len(train), "train_first": f"{train['month'].min():%Y-%m}",
                  "train_last": f"{train['month'].max():%Y-%m}", "test_first": f"{test['month'].min():%Y-%m}",
                  "test_last": f"{test['month'].max():%Y-%m}", "test_months": len(test)},
        "model": {"type": "RandomForestRegressor", "n_estimators": 500, "min_samples_leaf": 2,
                  "random_state": SEED, "features": MODEL_FEATURES, "target": "revenue_eur / rolling_mean_12",
                  "oob_r2_scaled_target": round(model.oob_score_, 4),
                  "feature_importance": dict(sorted(zip(MODEL_FEATURES, model.feature_importances_.round(4)),
                                                    key=lambda kv: -kv[1]))},
        "test": {
            "random_forest_month_by_month": scores(actual, pred),
            "random_forest_24_months_ahead": scores(actual, recursive),
            "baseline_same_month_last_year": scores(actual, seasonal_naive),
            "baseline_same_month_last_year_plus_growth": scores(actual, naive_growth),
        },
        "band": {"quantiles": BAND, "relative_error": [round(lo_q, 4), round(hi_q, 4)],
                 "test_coverage_month_by_month": round(float(inside), 4),
                 "test_coverage_24_months_ahead": round(float(((actual >= lo_r) & (actual <= hi_r)).mean()), 4)},
        "psi_train_vs_test": {
            "revenue_eur": psi(train[TARGET], actual),
            MODEL_TARGET: psi(train[MODEL_TARGET], test[MODEL_TARGET]),
            "avg_revenue_per_shipment_eur": psi(train["avg_revenue_per_shipment_eur"],
                                                test["avg_revenue_per_shipment_eur"]),
            **{f: psi(train[f], test[f]) for f in MODEL_FEATURES if not f.startswith("month_")},
        },
        "decomposition_train": decomp,
        "test_mean_monthly_revenue_eur": float(actual.mean()),
    }

    predictions = pd.DataFrame({
        "month": test["month"].dt.strftime("%Y-%m-%d"), "revenue_eur": actual.round(2),
        "pred_month_by_month": pred.round(2), "lower_80": lower.round(2), "upper_80": upper.round(2),
        "pred_24_months_ahead": recursive.round(2), "same_month_last_year": seasonal_naive.round(2),
    })
    predictions.to_csv(OUT / "predictions.csv", index=False)
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=float) + "\n")
    plot_forecast(df, test, pred, lower, upper, recursive)

    m = metrics["test"]["random_forest_month_by_month"]
    print(f"MSE {m['mse_eur2']:.4g} EUR² | RMSE {m['rmse_eur']:,.0f} EUR ({m['rmse_pct_mean_revenue']:.2f} % del ingreso"
          f" medio) | MAPE {m['mape_pct']:.2f} % | Gini {m['gini']:.4f} | K2 {m['k2_stat']:.3f} (p={m['k2_pvalue']:.3f})"
          f" | PSI target_rel {metrics['psi_train_vs_test'][MODEL_TARGET]:.3f} | banda 80 % cubre {inside:.0%}")
    print(f"Resultados en {OUT.relative_to(ROOT)}/")


def plot_forecast(df, test, pred, lower, upper, recursive) -> None:
    history = df[(df["month"] >= "2022-01-01") & (df["month"] < test["month"].min())]
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(history["month"], history[TARGET] / 1e6, color="0.55", label="real (entrenamiento)")
    ax.plot(test["month"], test[TARGET] / 1e6, color="black", marker="o", ms=4, label="real 2024-2025 (prueba)")
    ax.fill_between(test["month"], lower / 1e6, upper / 1e6, color="tab:blue", alpha=0.2,
                    label="rango de variabilidad (80 %)")
    ax.plot(test["month"], pred / 1e6, color="tab:blue", marker="o", ms=4, label="predicción mes a mes")
    ax.plot(test["month"], recursive / 1e6, color="tab:orange", ls="--", label="predicción a 24 meses vista")
    ax.axvline(test["month"].min(), color="0.3", ls=":", lw=1)
    ax.set(title="TrackFlow: ingresos mensuales consolidados, predicción frente a real",
           ylabel="revenue_eur (millones de EUR)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "forecast_vs_actual.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
