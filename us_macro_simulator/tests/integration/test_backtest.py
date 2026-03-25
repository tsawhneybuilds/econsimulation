"""Integration tests for pseudo-real-time backtesting."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.forecasting.runners.backtest_runner import BacktestConfig, BacktestRunner


def test_backtest_runs_on_small_origin_grid():
    runner = BacktestRunner(
        config=BacktestConfig(
            start_origin="2017Q1",
            end_origin="2017Q2",
            horizon=2,
        )
    )
    result = runner.run()
    assert result.origins == ["2017Q1", "2017Q2"]
    assert len(result.artifacts) == 2
    assert "semi_structural" in result.benchmark_forecasts["2017Q1"]
    assert not result.comparison_table.empty


def test_backtest_masks_unreleased_quarterly_data():
    runner = BacktestRunner(
        config=BacktestConfig(
            start_origin="2019Q4",
            end_origin="2019Q4",
            horizon=1,
        )
    )
    dataset = runner._build_observed_dataset(datetime(2019, 12, 31))
    assert dataset.latest_period("GDPC1") == pd.Period("2019Q3", freq="Q")
    assert dataset.latest_period("FEDFUNDS") == pd.Period("2019Q4", freq="Q")
