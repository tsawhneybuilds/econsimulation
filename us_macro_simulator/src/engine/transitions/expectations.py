"""Step 1-4: Growth/inflation expectations, ROW update, central bank Taylor rule."""
from __future__ import annotations
import numpy as np
from src.engine.core.state import SimulationState


def set_growth_inflation_expectations(state: SimulationState) -> None:
    """
    Update expected GDP growth (gamma_e) and inflation (pi_e) using
    adaptive expectations on recent history.
    BeforeIT.jl: set_growth_inflation_expectations!
    """
    agg = state.aggregate
    hist_len = len(agg.Y_hist)

    if hist_len >= 2:
        # Adaptive: weight recent observation heavily
        y_prev = agg.Y_hist[-1]
        y_curr = agg.Y
        gamma_new = (y_curr - y_prev) / max(y_prev, 1e-10)
        # Smooth: 80% persistence + 20% new signal
        agg.gamma_e = 0.8 * agg.gamma_e + 0.2 * gamma_new
    else:
        agg.gamma_e = 0.005   # default 2% annual

    if len(agg.pi_hist) >= 2:
        pi_new = agg.pi_hist[-1]
        agg.pi_e = 0.8 * agg.pi_e + 0.2 * pi_new
    else:
        agg.pi_e = 0.005


def set_epsilon(state: SimulationState) -> None:
    """
    Draw external (ROW) shocks for growth and inflation.
    BeforeIT.jl: set_epsilon!
    """
    rng = state.rng_state
    rotw = state.rotw

    eps_Y = rng.normal(0.0, rotw.sigma_Y_ROW)
    eps_pi = rng.normal(0.0, rotw.sigma_pi_ROW)

    rotw.gamma_ROW = (rotw.alpha_Y_ROW * rotw.gamma_ROW
                      + (1 - rotw.alpha_Y_ROW) * rotw.beta_Y_ROW
                      + eps_Y)
    rotw.pi_ROW = (rotw.alpha_pi_ROW * rotw.pi_ROW
                   + (1 - rotw.alpha_pi_ROW) * rotw.beta_pi_ROW
                   + eps_pi)


def set_growth_inflation_row(state: SimulationState) -> None:
    """
    Update ROW GDP level based on growth shock.
    BeforeIT.jl: set_growth_inflation_EA!  (U.S. ROW proxy)
    """
    rotw = state.rotw
    rotw.Y_ROW = rotw.Y_ROW * (1.0 + rotw.gamma_ROW)
