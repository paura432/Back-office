"""Tests del split 8/2 años y de la causalidad de los features del pronóstico de ventas.

Usan el dataset real ``data/raw/trackflow_sales.csv`` y las funciones de
``data/process/sales_forecast_features.py``, que solo dependen de pandas, así
que corren con el entorno de los pipelines:

    uv run --project data/pipelines python -m pytest tests/pipelines/test_sales_forecast.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from data.process.sales_forecast_features import (
    MODEL_FEATURES,
    MODEL_TARGET,
    TARGET,
    add_time_features,
    load_sales,
    split_train_test,
)

DATA = Path(__file__).resolve().parents[2] / "data" / "raw" / "trackflow_sales.csv"
CUTOFF = pd.Timestamp("2024-01-01")


@pytest.fixture(scope="module")
def sales() -> pd.DataFrame:
    return load_sales(DATA)


# --- Split 8 años / 2 años y fuga entre conjuntos ---------------------------------


def test_split_uses_first_8_years_for_train_and_last_2_for_test(sales):
    train, test = split_train_test(sales)

    assert sorted(train["month"].dt.year.unique()) == list(range(2016, 2024))
    assert sorted(test["month"].dt.year.unique()) == [2024, 2025]
    assert len(train) == 96 and len(test) == 24
    assert train["month"].max() < CUTOFF <= test["month"].min()
    assert set(train["month"]).isdisjoint(test["month"])


def test_split_with_features_only_drops_months_without_history(sales):
    train, test = split_train_test(add_time_features(sales))

    # 2016 solo sirve de historia para el lag de 12 meses; el test queda completo.
    assert train["month"].min() == pd.Timestamp("2017-01-01")
    assert train["month"].max() == pd.Timestamp("2023-12-01")
    assert len(train) == 84
    assert len(test) == 24
    assert not test[MODEL_FEATURES].isna().any().any()


def test_test_years_do_not_leak_into_training_rows(sales):
    """Cambiar por completo las ventas de 2024-2025 no altera ninguna fila de train."""
    altered = sales.copy()
    future = altered["month"] >= CUTOFF
    altered.loc[future, TARGET] = altered.loc[future, TARGET] * 10

    train, _ = split_train_test(add_time_features(sales))
    train_altered, _ = split_train_test(add_time_features(altered))

    columns = MODEL_FEATURES + [MODEL_TARGET]
    pd.testing.assert_frame_equal(train[columns], train_altered[columns])


# --- Causalidad de lags y estadísticas rodantes -----------------------------------


def test_lag_features_equal_past_raw_values(sales):
    feats = add_time_features(sales)
    revenue = feats[TARGET]

    for t in (12, 50, 96, 119):
        assert feats.loc[t, "lag_1"] == revenue[t - 1]
        assert feats.loc[t, "lag_2"] == revenue[t - 2]
        assert feats.loc[t, "lag_12"] == revenue[t - 12]
        assert feats.loc[t, "lag_1"] != revenue[t]


def test_rolling_features_only_use_previous_months(sales):
    feats = add_time_features(sales)
    revenue = feats[TARGET]

    for t in (12, 50, 96, 119):
        assert feats.loc[t, "rolling_mean_3"] == pytest.approx(revenue[t - 3:t].mean())
        assert feats.loc[t, "rolling_mean_12"] == pytest.approx(revenue[t - 12:t].mean())
        assert feats.loc[t, "rolling_std_12"] == pytest.approx(revenue[t - 12:t].std())


def test_features_of_a_month_ignore_that_month_and_the_future(sales):
    """Perturbar el mes t solo puede cambiar features de meses posteriores a t."""
    t = 100
    altered = sales.copy()
    altered.loc[t:, TARGET] = altered.loc[t:, TARGET] * 3

    original = add_time_features(sales)
    changed = add_time_features(altered)

    feature_cols = MODEL_FEATURES + ["lag_1", "lag_12", "rolling_mean_3", "rolling_mean_12", "rolling_std_12"]
    pd.testing.assert_frame_equal(original.loc[:t, feature_cols], changed.loc[:t, feature_cols])
    assert not np.isclose(original.loc[t + 1, "lag_1"], changed.loc[t + 1, "lag_1"])


def test_future_month_without_revenue_still_gets_features(sales):
    future = sales.copy()
    future.loc[future.index[-1], TARGET] = np.nan

    feats = add_time_features(future)

    assert not feats.loc[feats.index[-1], MODEL_FEATURES].isna().any()


# --- Contrato del dataset (BRIEFING) -----------------------------------------------


def test_dataset_matches_briefing(sales):
    assert len(sales) == 120
    assert sales["month"].min() == pd.Timestamp("2016-01-01")
    assert sales["month"].max() == pd.Timestamp("2025-12-01")
    assert (sales[TARGET] > 0).all()
    assert set(sales["market"]) == {"consolidated"}


@pytest.mark.parametrize(
    "corrupt, message",
    [
        (lambda df: df.drop(index=30), "faltan meses"),
        (lambda df: df.assign(revenue_eur=df["revenue_eur"].where(df.index != 5, -1.0)), "positivo"),
        (lambda df: df.assign(revenue_eur=df["revenue_eur"].where(df.index != 5)), "sin revenue_eur"),
        (lambda df: df.rename(columns={"revenue_eur": "revenue"}), "columnas"),
    ],
)
def test_load_rejects_data_that_breaks_the_briefing(tmp_path, corrupt, message):
    path = tmp_path / "sales.csv"
    corrupt(pd.read_csv(DATA)).to_csv(path, index=False)

    with pytest.raises(ValueError, match=message):
        load_sales(path)
