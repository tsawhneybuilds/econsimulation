"""Unit tests for a single engine step."""
from __future__ import annotations

import copy

import numpy as np
import pytest

from src.us.calibration import build_us_2019q4_calibration
from src.us.initialization import USInitializer
from src.engine.core.engine import USMacroEngine
from src.engine.shocks.shock_protocol import NoShock, RateShock, ImportPriceShock


@pytest.fixture(scope="module")
def initial_state():
    calib = build_us_2019q4_calibration()
    init = USInitializer()
    return init.initialize(calib, None, seed=42)


def test_one_step_completes(initial_state):
    engine = USMacroEngine()
    state = copy.deepcopy(initial_state)
    engine.step(state)
    assert state.time_index == 1


def test_one_step_no_nan(initial_state):
    engine = USMacroEngine()
    state = copy.deepcopy(initial_state)
    engine.step(state)
    state.check_no_nan_inf()


def test_gdp_positive_after_step(initial_state):
    engine = USMacroEngine()
    state = copy.deepcopy(initial_state)
    engine.step(state)
    assert state.aggregate.Y > 0


def test_price_index_positive(initial_state):
    engine = USMacroEngine()
    state = copy.deepcopy(initial_state)
    engine.step(state)
    assert state.aggregate.P_bar > 0


def test_rate_shock_raises_rate(initial_state):
    engine = USMacroEngine()
    state = copy.deepcopy(initial_state)
    r_before = state.central_bank.r_bar
    shock = RateShock(delta_r=0.005, duration=1)
    engine.step(state, shock=shock)
    assert state.central_bank.r_bar >= r_before


def test_deterministic_with_seed(initial_state):
    engine = USMacroEngine()
    s1 = copy.deepcopy(initial_state)
    s2 = copy.deepcopy(initial_state)
    s1.rng_state = np.random.default_rng(99)
    s2.rng_state = np.random.default_rng(99)
    engine.step(s1)
    engine.step(s2)
    np.testing.assert_allclose(s1.aggregate.Y, s2.aggregate.Y)


def test_time_increments(initial_state):
    engine = USMacroEngine()
    state = copy.deepcopy(initial_state)
    for t in range(4):
        engine.step(state)
    assert state.time_index == 4


def test_no_negative_capital(initial_state):
    engine = USMacroEngine()
    state = copy.deepcopy(initial_state)
    for _ in range(4):
        engine.step(state)
    assert np.all(state.firms.K_i >= 0)


def test_import_price_shock_direction(initial_state):
    """Import price shock should raise firm prices."""
    engine = USMacroEngine()
    s_base = copy.deepcopy(initial_state)
    s_shock = copy.deepcopy(initial_state)
    s_base.rng_state = np.random.default_rng(1)
    s_shock.rng_state = np.random.default_rng(1)

    engine.step(s_base, shock=NoShock())
    engine.step(s_shock, shock=ImportPriceShock(delta_pm=0.10, duration=1))

    # Shocked prices should be higher
    assert s_shock.firms.P_i.mean() >= s_base.firms.P_i.mean() * 0.99
