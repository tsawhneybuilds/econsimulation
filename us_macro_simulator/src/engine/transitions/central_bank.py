"""Central bank Taylor rule."""
from __future__ import annotations
import numpy as np
from src.engine.core.state import SimulationState


def set_central_bank_rate(state: SimulationState) -> None:
    """
    Set nominal policy rate via Taylor rule.
    r_bar = rho * r_bar_prev + (1-rho) * [r_star + pi_e + xi_pi*(pi_e - pi_star) + xi_gamma*gamma_e]
    BeforeIT.jl: set_central_bank_rate!
    """
    cb = state.central_bank
    agg = state.aggregate

    pi_e = agg.pi_e
    gamma_e = agg.gamma_e

    r_taylor = (cb.r_star + pi_e
                + cb.xi_pi * (pi_e - cb.pi_star)
                + cb.xi_gamma * gamma_e)

    # Smooth with inertia
    r_new = cb.rho * cb.r_bar + (1 - cb.rho) * r_taylor
    cb.r_bar = max(0.0, r_new)   # zero lower bound
    agg.r_bar = cb.r_bar

    # Update 10-year rate with small term premium adjustment
    cb.r_G = cb.r_bar + state.financial.term_premium


def set_bank_rate(state: SimulationState) -> None:
    """
    Update lending rate = policy rate + credit spread.
    BeforeIT.jl: set_bank_rate!
    """
    state.bank.r = state.central_bank.r_bar + state.financial.credit_spread
