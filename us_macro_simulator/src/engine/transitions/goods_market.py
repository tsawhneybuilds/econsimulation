"""Goods market: search and matching for consumption and investment."""
from __future__ import annotations
import numpy as np
from src.engine.core.state import SimulationState


def search_and_matching(state: SimulationState) -> None:
    """
    Aggregate demand vs supply matching across all goods markets.
    BeforeIT.jl: search_and_matching!
    """
    firms = state.firms
    workers = state.workers_act
    workers_inact = state.workers_inact
    gov = state.government
    rotw = state.rotw
    agg = state.aggregate
    rng = state.rng_state

    # Total supply (with inventories)
    total_supply = firms.Y_i + firms.S_i  # production + inventories

    # Total demand
    demand_workers = workers.C_d_h.sum() + workers.I_d_h.sum()
    demand_inact = workers_inact.C_d_h.sum()
    demand_firms_owners = firms.C_d_h_i.sum() + firms.I_d_h_i.sum()
    demand_bank_owner = state.bank.C_d_h + state.bank.I_d_h
    demand_gov = gov.C_G
    demand_investment = firms.I_d_i.sum()
    demand_export = rotw.C_E
    demand_import_sub = rotw.Y_I  # imports substitute domestic demand

    total_demand = (demand_workers + demand_inact + demand_firms_owners
                    + demand_bank_owner + demand_gov + demand_investment + demand_export)

    total_supply_val = total_supply.sum()

    if total_supply_val <= 0:
        # No goods to sell
        firms.Q_i[:] = 0.0
        workers.C_h[:] = 0.0
        workers.I_h[:] = 0.0
        return

    # Rationing ratio
    if total_demand <= total_supply_val:
        ration_ratio = 1.0
    else:
        ration_ratio = total_supply_val / max(total_demand, 1e-10)

    # Realised quantities (proportional rationing)
    workers.C_h = workers.C_d_h * ration_ratio
    workers.I_h = workers.I_d_h * ration_ratio
    workers_inact.C_h = workers_inact.C_d_h * ration_ratio
    firms.C_h_i = firms.C_d_h_i * ration_ratio
    firms.I_h_i = firms.I_d_h_i * ration_ratio
    state.bank.C_h = state.bank.C_d_h * ration_ratio
    state.bank.I_h = state.bank.I_d_h * ration_ratio

    # Realised firm investment
    firms.I_i = firms.I_d_i * ration_ratio

    # Aggregate sales
    firms.Q_d_i = (firms.Y_i / max(firms.Y_i.sum(), 1e-10)) * total_demand * ration_ratio
    firms.Q_i = np.minimum(firms.Q_d_i, firms.Y_i + firms.S_i)
