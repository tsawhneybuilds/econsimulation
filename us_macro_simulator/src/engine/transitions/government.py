"""Government expenditure and fiscal accounts."""
from __future__ import annotations
import numpy as np
from src.engine.core.state import SimulationState


def set_gov_expenditure(state: SimulationState) -> None:
    """
    Government consumption expenditure (AR process).
    BeforeIT.jl: set_gov_expenditure!
    """
    gov = state.government
    rng = state.rng_state
    agg = state.aggregate

    eps_G = rng.normal(0.0, gov.sigma_G)
    C_G_new = (gov.alpha_G * np.log(max(gov.C_G, 1e-10))
               + (1 - gov.alpha_G) * gov.beta_G
               + eps_G)
    gov.C_G = np.exp(C_G_new) if C_G_new < 20 else gov.C_G * (1 + agg.gamma_e)
    gov.C_G = max(gov.C_G, 0.0)

    # Distribute to sectors
    gov.C_d_j = gov.C_G * np.array([0.02, 0.08, 0.10, 0.15, 0.05, 0.60])


def set_gov_revenues(state: SimulationState) -> None:
    """
    Compute government tax revenues.
    BeforeIT.jl: set_gov_revenues!
    """
    gov = state.government
    firms = state.firms
    workers = state.workers_act
    workers_inact = state.workers_inact
    bank = state.bank
    s = state

    # Income tax from workers
    tax_workers = (s.central_bank.r_bar * 0 +   # placeholder
                   workers.Y_h.sum() * 0.22 * 0.1)  # simplified

    # Corporate tax
    tax_corporate = np.maximum(firms.Pi_i, 0).sum() * 0.21

    # VAT proxy (on consumption)
    C_total = (workers.C_h.sum() + workers_inact.C_h.sum()
               + firms.C_h_i.sum() if hasattr(firms, 'C_h_i') else 0)
    tax_vat = C_total * 0.085

    gov.Y_G = tax_workers + tax_corporate + tax_vat


def set_gov_loans(state: SimulationState) -> None:
    """
    Update government debt: borrow to cover deficit.
    BeforeIT.jl: set_gov_loans!
    """
    gov = state.government
    cb = state.central_bank

    # Deficit = expenditure - revenues
    deficit = gov.C_G - gov.Y_G
    interest_payment = cb.r_G * gov.L_G

    # Borrow to cover deficit + interest
    delta_L = deficit + interest_payment
    gov.L_G = max(gov.L_G + delta_L, 0.0)
