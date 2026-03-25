"""Firm expectations and decisions (desired quantities, prices, investment)."""
from __future__ import annotations
import numpy as np
from src.engine.core.state import SimulationState


def set_firms_expectations_and_decisions(state: SimulationState) -> None:
    """
    Firms update: quantity targets, price, desired investment, desired labour.
    BeforeIT.jl: set_firms_expectations_and_decisions!
    """
    rng = state.rng_state
    agg = state.aggregate
    firms = state.firms
    I = firms.n_firms

    gamma_e = agg.gamma_e
    pi_e = agg.pi_e

    # Expected sales = last sales * (1 + expected growth) + small noise
    noise = rng.normal(0.0, 0.01, I)
    firms.Q_s_i = np.maximum(firms.Q_i * (1.0 + gamma_e + noise), 0.0)

    # Desired investment = replacement + expansion
    firms.I_d_i = firms.delta_i * firms.K_i + np.maximum(
        firms.kappa_i * (firms.Q_s_i - firms.Q_i), 0.0
    )

    # Desired materials (intermediate goods)
    firms.DM_d_i = firms.beta_i * firms.Q_s_i

    # Desired employment
    labour_demand = firms.Q_s_i / np.maximum(firms.alpha_bar_i, 1e-10)
    firms.N_d_i = np.maximum(labour_demand.astype(int), 1)

    # Expected capital
    firms.K_e_i = firms.K_i * (1 - firms.delta_i) + firms.I_d_i

    # Update prices: adaptive markup with inflation expectations
    price_adj = 1.0 + pi_e + rng.normal(0.0, 0.005, I)
    firms.P_i = np.maximum(firms.P_i * price_adj, 1e-6)

    # Expected loans based on investment plan
    new_loan_need = np.maximum(firms.I_d_i - firms.D_i * 0.5, 0.0)
    firms.L_e_i = firms.L_i + new_loan_need
    firms.DL_d_i = new_loan_need


def set_firms_wages(state: SimulationState) -> None:
    """
    Update firm wage offers with inflation and productivity.
    BeforeIT.jl: set_firms_wages!
    """
    rng = state.rng_state
    agg = state.aggregate
    firms = state.firms

    wage_adj = 1.0 + agg.pi_e + rng.normal(0.0, 0.002, firms.n_firms)
    firms.w_i = np.maximum(firms.w_i * wage_adj, 1e-6)
    firms.w_bar_i = 0.9 * firms.w_bar_i + 0.1 * firms.w_i


def set_firms_production(state: SimulationState) -> None:
    """
    Leontief production function.
    Y_i = min(alpha * N, kappa * K, M / beta)
    BeforeIT.jl: set_firms_production!
    """
    firms = state.firms

    labour_cap = firms.alpha_bar_i * firms.N_i
    capital_cap = firms.kappa_i * firms.K_i
    material_cap = np.where(firms.beta_i > 0,
                             firms.M_i / np.maximum(firms.beta_i, 1e-10),
                             labour_cap)

    firms.Y_i = np.maximum(np.minimum(np.minimum(labour_cap, capital_cap), material_cap), 0.0)


def set_firms_stocks(state: SimulationState) -> None:
    """Update inventories and intermediate goods stocks."""
    firms = state.firms

    firms.DS_i = firms.Q_i - firms.Q_d_i          # inventory change
    firms.S_i = np.maximum(firms.S_i + firms.DS_i, 0.0)
    firms.DM_i = firms.M_i - firms.DM_d_i
    firms.M_i = np.maximum(firms.M_i + firms.DM_d_i - firms.M_i * 0.9, 0.0)


def set_firms_profits(state: SimulationState) -> None:
    """
    Compute profits: Pi = P*Q - w*N - r_L*L - delta*K - tau
    BeforeIT.jl: set_firms_profits!
    """
    firms = state.firms
    bank = state.bank
    s = state    # full state for tax params

    revenue = firms.P_i * firms.Q_i
    labour_cost = firms.w_i * firms.N_i
    interest_cost = bank.r * firms.L_i
    depreciation = firms.delta_i * firms.K_i * firms.P_i
    product_tax = firms.tau_Y_i * revenue
    production_tax = firms.tau_K_i * (firms.K_i * firms.P_i)

    firms.Pi_i = revenue - labour_cost - interest_cost - depreciation - product_tax - production_tax
    firms.pi_bar_i = np.where(revenue > 0, firms.Pi_i / revenue, 0.0)


def set_firms_deposits(state: SimulationState) -> None:
    """Update firm deposits after all transactions."""
    firms = state.firms
    agg = state.aggregate
    # Simplified: deposits = retained earnings + existing deposits
    retained = np.maximum(firms.Pi_i * 0.45, 0.0)  # ~45% retained after tax/dividend
    firms.D_i = np.maximum(firms.D_i + retained - firms.I_i, 0.0)


def set_firms_loans(state: SimulationState) -> None:
    """Update firm loan balances: repay principal fraction + new loans."""
    firms = state.firms
    repayment_rate = 0.05  # 5% of outstanding principal per quarter
    firms.L_i = np.maximum(firms.L_i * (1 - repayment_rate) + firms.DL_i, 0.0)


def set_firms_equity(state: SimulationState) -> None:
    """Update firm equity: E = K - L."""
    firms = state.firms
    firms.E_i = np.maximum(firms.K_i * firms.P_i - firms.L_i, 0.0)
