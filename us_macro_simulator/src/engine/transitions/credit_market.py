"""Credit market: search and matching for loans."""
from __future__ import annotations
import numpy as np
from src.engine.core.state import SimulationState


def search_and_matching_credit(state: SimulationState) -> None:
    """
    Firms request loans; bank allocates up to capacity.
    BeforeIT.jl: search_and_matching_credit!
    """
    firms = state.firms
    bank = state.bank
    rng = state.rng_state

    # Bank lending capacity: fraction of equity + deposits
    lending_capacity = bank.E_k * 10.0  # leverage up to 10x equity

    total_demand = firms.DL_d_i.sum()
    if total_demand <= 0:
        firms.DL_i[:] = 0.0
        return

    # Rationing: scale down if demand exceeds capacity
    if total_demand <= lending_capacity:
        firms.DL_i = firms.DL_d_i.copy()
    else:
        ratio = lending_capacity / total_demand
        firms.DL_i = firms.DL_d_i * ratio

    # Random search friction: ~5% of credit requests fail
    friction = rng.uniform(0.90, 1.0, firms.n_firms)
    firms.DL_i *= friction
