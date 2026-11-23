"""Carga, features temporales y split 8/2 años del pronóstico de ventas de TrackFlow.

Funciones puras de pandas, sin entrenamiento ni dependencias de ML, para que
el script de entrenamiento (``scripts/train_sales_forecast.py``) y los tests
(``tests/pipelines/test_sales_forecast.py``) usen exactamente el mismo código.

El formato del dataset es el del BRIEFING de sales forecasting de TrackFlow:
``data/raw/trackflow_sales.csv``, una fila ``consolidated`` por mes de 2016-01
a 2025-12 y ``revenue_eur`` como variable objetivo.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "revenue_eur"
COLUMNS = ["month", "revenue_eur", "shipments_processed", "avg_revenue_per_shipment_eur", "market"]
MARKET = "consolidated"
FIRST_MONTH = pd.Timestamp("2016-01-01")
LAST_MONTH = pd.Timestamp("2025-12-01")
TRAIN_YEARS = 8

LAGS = (1, 2, 3, 12)
ROLLING_WINDOWS = (3, 12)

# Lo que recibe el modelo. Todo lo que mide euros va dividido entre la media de
# los 12 meses anteriores (rolling_mean_12): así el modelo aprende la forma
# estacional y el ritmo reciente, no un nivel de facturación que en los años de
# prueba ya está por encima de todo lo visto en entrenamiento.
MODEL_FEATURES = [
    "lag_1_rel",
    "lag_2_rel",
    "lag_3_rel",
    "lag_12_rel",
    "rolling_mean_3_rel",
    "rolling_std_12_rel",
    "month_sin",
    "month_cos",
]
MODEL_TARGET = "target_rel"


def load_sales(path: str | Path) -> pd.DataFrame:
    """Lee el CSV y comprueba las columnas y restricciones del BRIEFING.

    Los nulos se tratan aquí: un mes sin ``revenue_eur`` no puede rellenarse
    sin inventar ventas, así que se rechaza el archivo; las demás columnas
    numéricas se interpolan en el tiempo si faltaran (en el dataset provisto
    no falta ninguna).
    """
    df = pd.read_csv(path)
    if list(df.columns) != COLUMNS:
        raise ValueError(f"columnas {list(df.columns)}, se esperaban {COLUMNS}")

    df = df[df["market"] == MARKET].copy()
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m-%d")
    df = df.sort_values("month").reset_index(drop=True)

    expected = pd.date_range(FIRST_MONTH, LAST_MONTH, freq="MS")
    if not df["month"].equals(pd.Series(expected, name="month")):
        raise ValueError("faltan meses o hay meses repetidos entre 2016-01 y 2025-12")
    if df[TARGET].isna().any():
        raise ValueError("hay meses sin revenue_eur")
    if (df[TARGET] <= 0).any():
        raise ValueError("revenue_eur debe ser positivo en todos los meses")

    for col in ("shipments_processed", "avg_revenue_per_shipment_eur"):
        df[col] = df[col].interpolate(limit_direction="both")
    return df


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Añade features de lag, rolling y calendario calculados de forma causal.

    Cada valor de la fila ``t`` usa solo filas anteriores a ``t``: los lags son
    ``shift(k)`` con ``k >= 1`` y las ventanas rodantes se calculan sobre la
    serie ya desplazada (``shift(1)`` antes de ``rolling``), de modo que nunca
    incluyen el mes que se quiere predecir. ``shipments_processed`` y
    ``avg_revenue_per_shipment_eur`` no se usan: su producto es ``revenue_eur``,
    así que los del propio mes serían el target disfrazado y los de meses
    anteriores no aportan nada que no esté ya en los lags de ingresos.

    Solo necesita ``month`` y ``revenue_eur``; una fila con ``revenue_eur``
    vacío (un mes futuro) recibe igualmente sus features a partir del pasado.
    """
    out = df.copy()
    revenue = out[TARGET]
    past = revenue.shift(1)

    for k in LAGS:
        out[f"lag_{k}"] = revenue.shift(k)
    for w in ROLLING_WINDOWS:
        out[f"rolling_mean_{w}"] = past.rolling(w).mean()
    out["rolling_std_12"] = past.rolling(12).std()

    month = out["month"].dt.month
    out["month_num"] = month
    out["quarter"] = out["month"].dt.quarter
    out["month_sin"] = np.sin(2 * np.pi * month / 12)
    out["month_cos"] = np.cos(2 * np.pi * month / 12)

    # Escalado: euros relativos al nivel medio de los 12 meses anteriores.
    level = out["rolling_mean_12"]
    for k in LAGS:
        out[f"lag_{k}_rel"] = out[f"lag_{k}"] / level
    out["rolling_mean_3_rel"] = out["rolling_mean_3"] / level
    out["rolling_std_12_rel"] = out["rolling_std_12"] / level
    out[MODEL_TARGET] = revenue / level
    return out


def split_train_test(df: pd.DataFrame, train_years: int = TRAIN_YEARS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Primeros ``train_years`` años completos para entrenar y el resto para probar.

    El corte es por fecha (2024-01-01 con el dataset de TrackFlow), no por
    posición ni al azar, así que ningún mes de prueba puede caer en
    entrenamiento. Las filas sin historia suficiente para todos los features
    (2016, por el lag de 12 meses) se descartan del entrenamiento.
    """
    cutoff = df["month"].min() + pd.DateOffset(years=train_years)
    train = df[df["month"] < cutoff]
    test = df[df["month"] >= cutoff]
    if MODEL_TARGET in df.columns:
        train = train.dropna(subset=MODEL_FEATURES + [MODEL_TARGET])
    return train.copy(), test.copy()
