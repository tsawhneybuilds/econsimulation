"""Trade: import/export decisions."""
from __future__ import annotations
import numpy as np
from src.engine.core.state import SimulationState


def set_rotw_import_export(state: SimulationState) -> None:
    """
    Compute demand for exports and supply of imports.
    BeforeIT.jl: set_rotw_import_export!
    """
    rotw = state.rotw
    rng = state.rng_state
    agg = state.aggregate

    # Export demand: AR process driven by ROW growth
    eps_E = rng.normal(0.0, rotw.sigma_E)
    log_C_E = (rotw.alpha_E * np.log(max(rotw.C_E, 1e-10))
               + (1 - rotw.alpha_E) * np.log(max(rotw.beta_E * rotw.Y_ROW, 1e-10))
               + eps_E)
    rotw.C_E = max(np.exp(log_C_E), 0.0)
    rotw.C_d_l = rotw.C_E * np.array([0.08, 0.25, 0.03, 0.20, 0.12, 0.32])

    # Import supply: AR process
    eps_I = rng.normal(0.0, rotw.sigma_I)
    log_Y_I = (rotw.alpha_I * np.log(max(rotw.Y_I, 1e-10))
               + (1 - rotw.alpha_I) * np.log(max(rotw.beta_I * agg.Y, 1e-10))
               + eps_I)
    rotw.Y_I = max(np.exp(log_Y_I), 0.0)
    rotw.Y_m = rotw.Y_I * np.array([0.10, 0.35, 0.05, 0.22, 0.08, 0.20])


def set_rotw_deposits(state: SimulationState) -> None:
    """Update ROW net credit position. BeforeIT.jl: set_rotw_deposits!"""
    rotw = state.rotw
    agg = state.aggregate

    net_exports = rotw.C_E - rotw.Y_I
    rotw.D_RoW = rotw.D_RoW + net_exports
