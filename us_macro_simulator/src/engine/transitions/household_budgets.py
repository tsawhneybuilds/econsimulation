"""Household budget decisions: consumption and investment."""
from __future__ import annotations
import numpy as np
from src.engine.core.state import SimulationState


def set_gov_social_benefits(state: SimulationState) -> None:
    """
    Government sets social benefit levels.
    BeforeIT.jl: set_gov_social_benefits!
    """
    gov = state.government
    agg = state.aggregate
    s = state

    # Benefits scaled to aggregate price level
    gov.sb_inact = gov.sb_inact * (1 + agg.pi_e)
    gov.sb_other = gov.sb_other * (1 + agg.pi_e)


def set_bank_expected_profits(state: SimulationState) -> None:
    """BeforeIT.jl: set_bank_expected_profits!"""
    bank = state.bank
    firms = state.firms
    cb = state.central_bank

    bank.Pi_e_k = (bank.r - cb.r_bar) * firms.L_i.sum() + cb.r_bar * bank.E_k


def set_households_budget_act(state: SimulationState) -> None:
    """
    Consumption and investment budget for active (employed/unemployed) workers.
    BeforeIT.jl: set_households_budget_act!
    """
    workers = state.workers_act
    gov = state.government
    cb = state.central_bank
    agg = state.aggregate

    # Propensity to consume out of income and wealth
    mpc_income = 0.75
    mpc_wealth = 0.02

    workers.C_d_h = np.maximum(
        mpc_income * workers.Y_h + mpc_wealth * workers.D_h,
        0.0
    )
    workers.I_d_h = np.maximum(
        (1 - mpc_income) * workers.Y_h * 0.3,
        0.0
    )


def set_households_budget_inact(state: SimulationState) -> None:
    """BeforeIT.jl: set_households_budget_inact!"""
    workers = state.workers_inact
    mpc_income = 0.85   # higher MPC for inactive (lower income)
    mpc_wealth = 0.01

    workers.C_d_h = np.maximum(
        mpc_income * workers.Y_h + mpc_wealth * workers.D_h,
        0.0
    )
    workers.I_d_h = np.zeros(workers.n_workers)


def set_households_budget_firms(state: SimulationState) -> None:
    """Budget for firm owners. BeforeIT.jl: set_households_budget_firms!"""
    firms = state.firms
    mpc = 0.60
    firms.C_d_h_i = np.maximum(mpc * firms.Y_h_i, 0.0)
    firms.I_d_h_i = np.maximum((1 - mpc) * firms.Y_h_i * 0.5, 0.0)


def set_households_budget_bank(state: SimulationState) -> None:
    """Budget for bank owner. BeforeIT.jl: set_households_budget_bank!"""
    bank = state.bank
    mpc = 0.60
    bank.C_d_h = max(mpc * bank.Y_h, 0.0)
    bank.I_d_h = max((1 - mpc) * bank.Y_h * 0.5, 0.0)
