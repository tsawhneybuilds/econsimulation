"""Integration smoke test: full 8-quarter run."""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from src.us.calibration import build_us_2019q4_calibration
from src.us.initialization import USInitializer
from src.engine.core.engine import USMacroEngine
from src.forecasting.runners.us_runner import USForecastRunner, ForecastArtifact


@pytest.fixture(scope="module")
def forecast_artifact():
    calib = build_us_2019q4_calibration()
    init = USInitializer()
    state = init.initialize(calib, None, seed=42)
    runner = USForecastRunner()
    return runner.run(state, T=8, seed=42)


def test_smoke_completes(forecast_artifact):
    assert isinstance(forecast_artifact, ForecastArtifact)


def test_smoke_horizon(forecast_artifact):
    assert len(forecast_artifact.point_forecasts) == 8


def test_smoke_no_nan(forecast_artifact):
    df = forecast_artifact.point_forecasts
    assert not df.isnull().any().any(), f"NaN found:\n{df.isnull().sum()}"


def test_smoke_gdp_growth_plausible(forecast_artifact):
    gdp = forecast_artifact.point_forecasts["gdp_growth"]
    # Should be within -20% to +20% annualised
    assert (gdp > -20).all() and (gdp < 20).all()


def test_smoke_unemployment_plausible(forecast_artifact):
    u = forecast_artifact.point_forecasts["unemployment_rate"]
    assert (u >= 0).all() and (u <= 30).all()


def test_smoke_fed_funds_nonnegative(forecast_artifact):
    r = forecast_artifact.point_forecasts["fed_funds_rate"]
    assert (r >= 0).all()


def test_smoke_reproducible():
    calib = build_us_2019q4_calibration()
    init = USInitializer()
    runner = USForecastRunner()

    s1 = init.initialize(calib, None, seed=42)
    s2 = init.initialize(calib, None, seed=42)

    a1 = runner.run(s1, T=4, seed=100)
    a2 = runner.run(s2, T=4, seed=100)

    pd.testing.assert_frame_equal(
        a1.point_forecasts,
        a2.point_forecasts,
        check_exact=False,
        rtol=1e-10,
    )


def test_smoke_period_index(forecast_artifact):
    idx = forecast_artifact.point_forecasts.index
    assert isinstance(idx, pd.PeriodIndex)
    assert str(idx[0]) == "2020Q1"
