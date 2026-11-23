"""Tests de la validación cruzada temporal del pronóstico de ventas.

Comprueban que ``time_series_folds`` (la estrategia de
``scripts/evaluate_sales_forecast.py``) conserva el orden cronológico en cada
fold y que los features de lag/rolling no filtran información entre folds.

    uv run --project data/pipelines python -m pytest tests/pipelines/test_sales_forecast_cv.py
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
    time_series_folds,
)

DATA = Path(__file__).resolve().parents[2] / "data" / "raw" / "trackflow_sales.csv"


@pytest.fixture(scope="module")
def train() -> pd.DataFrame:
    train, _ = split_train_test(add_time_features(load_sales(DATA)))
    return train.reset_index(drop=True)


@pytest.fixture(scope="module")
def folds(train):
    return time_series_folds(len(train), n_splits=5, test_size=12)


def test_each_fold_preserves_chronological_order(train, folds):
    months = train["month"]
    for train_idx, val_idx in folds:
        # Índices consecutivos y crecientes: nada se baraja dentro del fold.
        assert np.all(np.diff(train_idx) == 1)
        assert np.all(np.diff(val_idx) == 1)
        assert months.iloc[train_idx].is_monotonic_increasing
        assert months.iloc[val_idx].is_monotonic_increasing
        # Todo el entrenamiento es anterior a toda la validación.
        assert train_idx.max() < val_idx.min()
        assert months.iloc[train_idx].max() < months.iloc[val_idx].min()


def test_no_index_of_a_later_fold_appears_before_an_earlier_one(folds):
    val_sets = [val for _, val in folds]
    for earlier, later in zip(val_sets, val_sets[1:]):
        assert earlier.max() < later.min()
    for (train_a, _), (train_b, _) in zip(folds, folds[1:]):
        # Ventana creciente: cada entrenamiento contiene al anterior y empieza en la primera fila.
        assert train_b[: len(train_a)].tolist() == train_a.tolist()
        assert train_a[0] == train_b[0] == 0


def test_folds_validate_one_calendar_year_each_from_2019_to_2023(train, folds):
    assert len(folds) == 5
    years = [sorted(train["month"].iloc[val].dt.year.unique()) for _, val in folds]
    assert years == [[2019], [2020], [2021], [2022], [2023]]
    assert all(len(val) == 12 for _, val in folds)
    # La validación cruzada usa solo el periodo de entrenamiento: 2024-2025 nunca aparece.
    assert train["month"].max() < pd.Timestamp("2024-01-01")


def test_lag_and_rolling_features_do_not_leak_across_fold_boundaries(train, folds):
    """Borrar todo desde el inicio de un fold de validación no cambia sus filas de entrenamiento."""
    raw = load_sales(DATA)
    full = add_time_features(raw).set_index("month")
    cols = MODEL_FEATURES + [MODEL_TARGET]
    for train_idx, val_idx in folds:
        cut = train["month"].iloc[val_idx[0]]
        truncated = raw.copy()
        truncated.loc[truncated["month"] >= cut, TARGET] = np.nan

        recomputed = add_time_features(truncated).set_index("month")
        months = train["month"].iloc[train_idx]
        pd.testing.assert_frame_equal(full.loc[months, cols], recomputed.loc[months, cols])


def test_rejects_more_folds_than_the_data_allows():
    with pytest.raises(ValueError):
        time_series_folds(50, n_splits=5, test_size=12)
