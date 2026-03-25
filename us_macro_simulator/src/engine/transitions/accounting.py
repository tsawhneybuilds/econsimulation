"""
Accounting transitions: price indices, income, deposits, bank/CB equity,
GDP aggregation, and insolvency handling.

These functions correspond to BeforeIT.jl's steps 23-33 plus the
finance_insolvent_firms! helper (step 1).
"""
from __future__ import annotations

import numpy as np

from src.engine.core.state import SimulationState


# ──────────────────────────────────────────────────────────────────────────────
# Step 1 helper: insolvency
# ──────────────────────────────────────────────────────────────────────────────

def finance_insolvent_firms(state: SimulationState) -> None:
    """
    Recapitalise insolvent firms (E_i < 0) via emergency bank lending.
    Insolvent firms receive a debt injection equal to their equity shortfall,
    restoring equity to zero and adding the same amount to their loan balance.

    BeforeIT.jl: finance_insolvent_firms!
    """
    firms = state.firms
    bank = state.bank

    insolvent = firms.E_i < 0.0
    if not insolvent.any():
        return

    shortfall = -firms.E_i[insolvent]          # positive amount needed
    firms.L_i[insolvent] += shortfall           # raise loans
    firms.E_i[insolvent] = 0.0                  # restore equity to zero

    # Reduce bank equity to reflect emergency lending
    bank.E_k = max(bank.E_k - shortfall.sum() * 0.05, 0.0)  # 5% loss given default


# ──────────────────────────────────────────────────────────────────────────────
# Steps 23-26: Price indices
# ──────────────────────────────────────────────────────────────────────────────

def set_inflation_priceindex(state: SimulationState) -> None:
    """
    Update the global price index P_bar and quarterly inflation rate pi_.
    BeforeIT.jl: set_inflation_priceindex!

    P_bar is a sales-weighted average of firm prices.
    """
    firms = state.firms
    agg = state.aggregate

    total_sales = firms.Q_i.sum()
    if total_sales > 0:
        P_bar_new = np.dot(firms.P_i, firms.Q_i) / total_sales
    else:
        P_bar_new = firms.P_i.mean()

    P_bar_new = max(P_bar_new, 1e-10)

    # Quarterly inflation rate
    agg.pi_ = (P_bar_new - agg.P_bar) / max(agg.P_bar, 1e-10)

    # Append to history
    agg.Y_hist.append(agg.Y)
    agg.pi_hist.append(agg.pi_)

    agg.P_bar = P_bar_new


def set_sector_specific_priceindex(state: SimulationState) -> None:
    """
    Update the sector-level price index P_bar_g (one entry per sector G).
    BeforeIT.jl: set_sector_specific_priceindex!
    """
    firms = state.firms
    agg = state.aggregate
    G = len(agg.P_bar_g)

    for g in range(G):
        mask = firms.G_i == g
        if mask.any():
            sales_g = firms.Q_i[mask]
            prices_g = firms.P_i[mask]
            total = sales_g.sum()
            if total > 0:
                agg.P_bar_g[g] = np.dot(prices_g, sales_g) / total
            else:
                agg.P_bar_g[g] = prices_g.mean()
        # if no firms in sector, keep existing index


def set_capital_formation_priceindex(state: SimulationState) -> None:
    """
    Update the capital-formation price index P_bar_CF.
    Weighted average of manufacturing + construction sectors (g=1, g=2).
    BeforeIT.jl: set_capital_formation_priceindex!
    """
    agg = state.aggregate
    # Capital goods produced primarily in manufacturing (g=1) and construction (g=2)
    w_mfg = 0.55
    w_const = 0.45
    agg.P_bar_CF = w_mfg * agg.P_bar_g[1] + w_const * agg.P_bar_g[2]
    agg.P_bar_CF = max(agg.P_bar_CF, 1e-10)


def set_households_priceindex(state: SimulationState) -> None:
    """
    Update the household (CPI) price index P_bar_HH.
    BeforeIT.jl: set_households_priceindex!

    CPI basket weights (approximate PCE basket):
        0=Agri 1=Mfg 2=Const 3=Trade 4=Finance 5=Services
    """
    agg = state.aggregate
    # PCE-like basket weights across 6 sectors
    cpi_weights = np.array([0.04, 0.18, 0.06, 0.20, 0.12, 0.40])
    cpi_weights /= cpi_weights.sum()
    agg.P_bar_HH = float(np.dot(cpi_weights, agg.P_bar_g))
    agg.P_bar_HH = max(agg.P_bar_HH, 1e-10)


# ──────────────────────────────────────────────────────────────────────────────
# Steps 29-30: Bank profits and equity
# ──────────────────────────────────────────────────────────────────────────────

def set_bank_profits(state: SimulationState) -> None:
    """
    Compute bank profits: net interest income minus operating cost.
    BeforeIT.jl: set_bank_profits!
    """
    bank = state.bank
    firms = state.firms
    cb = state.central_bank

    # Net interest income = spread * loans
    net_interest = (bank.r - cb.r_bar) * firms.L_i.sum()

    # Cost of funds on deposits (approximate: pay r_bar on deposits)
    total_deposits = (
        state.workers_act.D_h.sum()
        + state.workers_inact.D_h.sum()
        + firms.D_i.sum()
        + bank.D_h
        + firms.D_h_i.sum()
    )
    deposit_cost = cb.r_bar * 0.5 * total_deposits  # pay half r_bar on deposits

    # Operating cost proxy
    operating_cost = net_interest * 0.15

    bank.Pi_k = net_interest - deposit_cost - operating_cost


def set_bank_equity(state: SimulationState) -> None:
    """
    Update bank equity: retained earnings.
    BeforeIT.jl: set_bank_equity!
    """
    bank = state.bank
    retention_rate = 0.45   # retain 45% of profits
    after_tax = max(bank.Pi_k * (1.0 - 0.21), 0.0)
    bank.E_k = max(bank.E_k + retention_rate * after_tax, 0.0)


# ──────────────────────────────────────────────────────────────────────────────
# Steps 31-32: Household income and deposits
# ──────────────────────────────────────────────────────────────────────────────

def set_households_income_act(state: SimulationState) -> None:
    """
    Finalise income for active workers (already set in budget step, here we
    also credit interest on deposits).
    BeforeIT.jl: set_households_income_act!
    """
    workers = state.workers_act
    cb = state.central_bank
    # Add interest on deposits (deposit rate ≈ half policy rate)
    deposit_rate = cb.r_bar * 0.5
    workers.Y_h = workers.Y_h + deposit_rate * workers.D_h


def set_households_income_inact(state: SimulationState) -> None:
    """BeforeIT.jl: set_households_income_inact!"""
    workers = state.workers_inact
    cb = state.central_bank
    deposit_rate = cb.r_bar * 0.5
    workers.Y_h = workers.Y_h + deposit_rate * workers.D_h


def set_households_income_firms(state: SimulationState) -> None:
    """
    Firm-owner households receive dividend income (already in Y_h_i) plus
    interest on deposits.
    BeforeIT.jl: set_households_income_firms!
    """
    firms = state.firms
    cb = state.central_bank
    deposit_rate = cb.r_bar * 0.5

    theta_DIV = 0.55
    tau_FIRM = 0.21
    after_tax_profit = np.maximum(firms.Pi_i * (1.0 - tau_FIRM), 0.0)
    dividends = theta_DIV * after_tax_profit
    interest_on_deposits = deposit_rate * firms.D_h_i
    firms.Y_h_i = dividends + interest_on_deposits


def set_households_income_bank(state: SimulationState) -> None:
    """BeforeIT.jl: set_households_income_bank!"""
    bank = state.bank
    cb = state.central_bank
    deposit_rate = cb.r_bar * 0.5

    theta_DIV = 0.55
    tau_FIRM = 0.21
    after_tax = max(bank.Pi_k * (1.0 - tau_FIRM), 0.0)
    bank.Y_h = theta_DIV * after_tax + deposit_rate * bank.D_h


def set_households_deposits_act(state: SimulationState) -> None:
    """
    Update active-worker deposits: income minus consumption/investment spending.
    BeforeIT.jl: set_households_deposits_act!
    """
    workers = state.workers_act
    spending = workers.C_h + workers.I_h
    workers.D_h = np.maximum(workers.D_h + workers.Y_h - spending, 0.0)

    # Update capital stock (investment adds to capital, depreciation removes)
    delta_h = 0.025
    workers.K_h = np.maximum(workers.K_h * (1.0 - delta_h) + workers.I_h, 0.0)


def set_households_deposits_inact(state: SimulationState) -> None:
    """BeforeIT.jl: set_households_deposits_inact!"""
    workers = state.workers_inact
    spending = workers.C_h + workers.I_h
    workers.D_h = np.maximum(workers.D_h + workers.Y_h - spending, 0.0)

    delta_h = 0.025
    workers.K_h = np.maximum(workers.K_h * (1.0 - delta_h) + workers.I_h, 0.0)


def set_households_deposits_firms(state: SimulationState) -> None:
    """BeforeIT.jl: set_households_deposits_firms!"""
    firms = state.firms
    spending = firms.C_h_i + firms.I_h_i
    firms.D_h_i = np.maximum(firms.D_h_i + firms.Y_h_i - spending, 0.0)

    delta_h = 0.025
    firms.K_h_i = np.maximum(firms.K_h_i * (1.0 - delta_h) + firms.I_h_i, 0.0)


def set_households_deposits_bank(state: SimulationState) -> None:
    """BeforeIT.jl: set_households_deposits_bank!"""
    bank = state.bank
    spending = bank.C_h + bank.I_h
    bank.D_h = max(bank.D_h + bank.Y_h - spending, 0.0)

    delta_h = 0.025
    bank.K_h = max(bank.K_h * (1.0 - delta_h) + bank.I_h, 0.0)


# ──────────────────────────────────────────────────────────────────────────────
# Step 33: Final accounting
# ──────────────────────────────────────────────────────────────────────────────

def set_central_bank_equity(state: SimulationState) -> None:
    """
    Update central bank equity: seigniorage income on government bonds.
    BeforeIT.jl: set_central_bank_equity!
    """
    cb = state.central_bank
    gov = state.government
    # Simplified: CB earns r_G on some fraction of government debt
    cb_holdings_fraction = 0.20   # CB holds ~20% of govt debt (QE proxy)
    seigniorage = cb.r_G * gov.L_G * cb_holdings_fraction
    cb.E_CB += seigniorage


def set_bank_deposits(state: SimulationState) -> None:
    """
    Update bank net deposit position: balance sheet identity.
    D_k = total deposits received - loans outstanding.
    BeforeIT.jl: set_bank_deposits!
    """
    bank = state.bank
    firms = state.firms
    workers_act = state.workers_act
    workers_inact = state.workers_inact

    total_deposits = (
        workers_act.D_h.sum()
        + workers_inact.D_h.sum()
        + firms.D_i.sum()
        + firms.D_h_i.sum()
        + bank.D_h
    )
    total_loans = firms.L_i.sum()
    bank.D_k = total_deposits - total_loans


def set_gross_domestic_product(state: SimulationState) -> None:
    """
    Compute nominal and real GDP from the expenditure side.

    GDP = C + I + G + NX
    BeforeIT.jl: set_gross_domestic_product!
    """
    agg = state.aggregate
    firms = state.firms
    workers_act = state.workers_act
    workers_inact = state.workers_inact
    gov = state.government
    rotw = state.rotw
    bank = state.bank

    # Personal consumption (C)
    C = (workers_act.C_h.sum()
         + workers_inact.C_h.sum()
         + firms.C_h_i.sum()
         + bank.C_h)

    # Gross private investment (I)
    # Firm business investment + residential investment by household owners
    I_business = firms.I_i.sum()
    I_residential = (workers_act.I_h.sum()
                     + workers_inact.I_h.sum()
                     + firms.I_h_i.sum()
                     + bank.I_h)
    I_total = I_business + I_residential

    # Government (G)
    G = gov.C_j

    # Net exports (NX) = exports - imports
    NX = rotw.C_l - rotw.Y_I

    # Nominal GDP
    Y_nominal = C + I_total + G + NX
    agg.Y = max(Y_nominal, 0.0)

    # Real GDP = nominal / price level
    P = max(agg.P_bar, 1e-10)
    agg.Y_real = agg.Y / P

    # Expected GDP (adaptive)
    agg.Y_e = 0.9 * agg.Y_e + 0.1 * agg.Y if agg.Y_e > 0 else agg.Y


def set_time(state: SimulationState) -> None:
    """
    Advance the simulation time counter by one step.
    BeforeIT.jl: set_time!
    """
    state.time_index += 1
