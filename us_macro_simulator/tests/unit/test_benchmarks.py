"""Unit tests for the benchmark suite."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.forecasting.benchmarks import list_benchmarks
from src.forecasting.benchmarks.semi_structural import SemiStructuralBenchmark


def test_registry_includes_semistructural():
    assert "semi_structural" in list_benchmarks()


def test_semistructural_forecast_shape():
    idx = pd.period_range("2010Q1", "2014Q4", freq="Q")
    history = pd.DataFrame(
        {
            "gdp_growth": np.linspace(1.0, 2.5, len(idx)),
            "cpi_inflation": np.linspace(1.5, 2.2, len(idx)),
            "unemployment_rate": np.linspace(8.0, 5.0, len(idx)),
            "fed_funds_rate": np.linspace(0.2, 1.4, len(idx)),
            "consumption_growth": np.linspace(1.2, 2.0, len(idx)),
            "residential_inv_growth": np.linspace(2.5, 3.0, len(idx)),
            "fci": np.linspace(0.3, -0.1, len(idx)),
        },
        index=idx,
    )
    forecast = SemiStructuralBenchmark().forecast(history, horizon=4)
    assert forecast.shape == (4, history.shape[1])
    assert list(forecast.columns) == list(history.columns)


def test_semistructural_handles_sparse_history():
    idx = pd.period_range("2019Q1", "2019Q4", freq="Q")
    history = pd.DataFrame(
        {
            "gdp_growth": [1.0, np.nan, 1.1, 1.2],
            "cpi_inflation": [2.0, 1.9, np.nan, 2.1],
            "unemployment_rate": [4.0, 3.9, 3.8, 3.7],
            "fed_funds_rate": [1.5, 1.5, 1.6, 1.6],
            "consumption_growth": [1.0, 1.1, 1.2, 1.2],
            "residential_inv_growth": [2.0, 2.1, 2.2, 2.3],
            "fci": [0.1, 0.0, -0.1, -0.1],
        },
        index=idx,
    )
    forecast = SemiStructuralBenchmark().forecast(history, horizon=2)
    assert forecast.notna().all().all()
