"""Unit tests for USInitializer."""
import numpy as np
import pytest

from src.us.calibration import build_us_2019q4_calibration
from src.us.initialization import USInitializer
from src.engine.core.state import SimulationState


@pytest.fixture
def state():
    calib = build_us_2019q4_calibration()
    init = USInitializer()
    # No obs_data needed for basic initialization
    return init.initialize(calib, None, seed=42)


def test_state_is_simulation_state(state):
    assert isinstance(state, SimulationState)


def test_no_nan_inf(state):
    state.check_no_nan_inf()  # should not raise


def test_firm_prices_positive(state):
    assert np.all(state.firms.P_i > 0)


def test_firm_capital_positive(state):
    assert np.all(state.firms.K_i > 0)


def test_aggregate_gdp_positive(state):
    assert state.aggregate.Y > 0


def test_price_index_positive(state):
    assert state.aggregate.P_bar > 0


def test_inactive_workers_occupation(state):
    assert np.all(state.workers_inact.O_h == -1)


def test_sector_assignment_valid(state):
    I = state.firms.n_firms
    G = 6
    assert state.firms.G_i.shape == (I,)
    assert np.all((state.firms.G_i >= 0) & (state.firms.G_i < G))


def test_worker_deposits_nonnegative(state):
    assert np.all(state.workers_act.D_h >= 0)


def test_bank_equity_positive(state):
    assert state.bank.E_k > 0


def test_government_debt_positive(state):
    assert state.government.L_G > 0


def test_reproducible_with_seed(state):
    calib = build_us_2019q4_calibration()
    init = USInitializer()
    s2 = init.initialize(calib, None, seed=42)
    np.testing.assert_array_equal(state.firms.G_i, s2.firms.G_i)
    np.testing.assert_allclose(state.firms.Y_i, s2.firms.Y_i)
