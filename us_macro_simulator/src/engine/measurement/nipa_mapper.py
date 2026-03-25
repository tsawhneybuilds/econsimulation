"""
NIPAMapper: translates SimulationState into observables that align with
U.S. NIPA / BLS / Fed conventions.

All rates are returned in *annualised percentage* form so downstream
validation against BEA / BLS releases requires no further conversion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

from src.engine.core.state import SimulationState


@dataclass
class ObservableSnapshot:
    """
    One-quarter observables computed from SimulationState.

    All growth rates are quarter-on-quarter in annualised % (SAAR convention).
    """

    # GDP expenditure-side
    gdp_growth_qoq: float          # GDP growth, annualised % (SAAR)
    nominal_gdp: float             # nominal GDP level, bn USD

    # Inflation
    cpi_inflation_qoq: float       # CPI annualised %
    core_cpi_inflation_qoq: float  # core CPI (ex food/energy), annualised %

    # Labour market
    unemployment_rate: float       # % of active labour force

    # Monetary policy
    fed_funds_rate_annual: float   # annualised Fed Funds Rate, %

    # Sub-aggregate growth rates
    consumption_growth_qoq: float        # PCE annualised %
    residential_inv_growth_qoq: float    # residential investment annualised %

    # Financial conditions
    fci: float                     # standardised financial conditions index

    # Time metadata
    time_index: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gdp_growth_qoq": self.gdp_growth_qoq,
            "nominal_gdp": self.nominal_gdp,
            "cpi_inflation_qoq": self.cpi_inflation_qoq,
            "core_cpi_inflation_qoq": self.core_cpi_inflation_qoq,
            "unemployment_rate": self.unemployment_rate,
            "fed_funds_rate_annual": self.fed_funds_rate_annual,
            "consumption_growth_qoq": self.consumption_growth_qoq,
            "residential_inv_growth_qoq": self.residential_inv_growth_qoq,
            "fci": self.fci,
            "time_index": self.time_index,
        }


class NIPAMapper:
    """
    Maps a SimulationState snapshot to an ObservableSnapshot.

    Design notes
    ------------
    * The ABM tracks nominal quantities.  Real series are obtained by
      deflating with the model's own price indices.
    * All quarter-on-quarter growth rates are converted to *annualised*
      form via (1 + q/q_rate)^4 - 1.
    * The class is stateful: it retains the previous period's levels so it
      can compute growth rates.
    """

    def __init__(self, warmup_steps: int = 2) -> None:
        # Previous-period levels (initialised on first call)
        self._prev_Y_real: float | None = None
        self._prev_C_real: float | None = None
        self._prev_I_resid_real: float | None = None
        self._prev_P_bar_HH: float | None = None
        self._prev_P_core: float | None = None
        self._warmup_steps = warmup_steps
        self._call_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize_from_state(self, state: SimulationState) -> None:
        """
        Seed previous-period levels from the *initial* (pre-step) state so
        that the first post-step growth rate is computed against a meaningful
        baseline rather than being zero or blowing up.
        """
        agg = state.aggregate
        workers_act = state.workers_act
        firms = state.firms
        bank = state.bank

        self._prev_Y_real = agg.Y_real if agg.Y_real > 0 else agg.Y / max(agg.P_bar, 1e-10)

        C_nominal = (
            workers_act.C_h.sum()
            + state.workers_inact.C_h.sum()
            + firms.C_h_i.sum()
            + bank.C_h
        )
        P_HH = max(agg.P_bar_HH, 1e-10)
        # If consumption is zero (pre-simulation), use Y_real as proxy
        self._prev_C_real = max(C_nominal / P_HH, self._prev_Y_real * 0.68)

        I_resid_nominal = (
            workers_act.I_h.sum()
            + state.workers_inact.I_h.sum()
            + firms.I_h_i.sum()
            + bank.I_h
        )
        P_CF = max(agg.P_bar_CF, 1e-10)
        self._prev_I_resid_real = max(I_resid_nominal / P_CF, self._prev_Y_real * 0.04)

        self._prev_P_bar_HH = agg.P_bar_HH

        core_weights = np.array([0.0, 0.16, 0.06, 0.20, 0.14, 0.44])
        core_weights /= core_weights.sum()
        self._prev_P_core = max(float(np.dot(core_weights, agg.P_bar_g)), 1e-10)

    def map(self, state: SimulationState) -> ObservableSnapshot:
        """Compute observables from a post-step SimulationState."""

        agg = state.aggregate
        firms = state.firms
        workers_act = state.workers_act
        gov = state.government
        rotw = state.rotw
        bank = state.bank
        cb = state.central_bank
        fin = state.financial

        # ── GDP ──────────────────────────────────────────────────────────
        Y_real = agg.Y_real if agg.Y_real > 0 else agg.Y / max(agg.P_bar, 1e-10)
        self._call_count += 1
        if self._call_count <= self._warmup_steps:
            # During warm-up, use calibrated expected growth to avoid
            # transient oscillations from model initialisation.
            gdp_growth_qoq = ((1.0 + agg.gamma_e) ** 4 - 1.0) * 100.0
        else:
            gdp_growth_qoq = self._annualised_growth(Y_real, self._prev_Y_real)

        # ── Consumption ──────────────────────────────────────────────────
        C_nominal = (
            workers_act.C_h.sum()
            + state.workers_inact.C_h.sum()
            + firms.C_h_i.sum()
            + bank.C_h
        )
        P_HH = max(agg.P_bar_HH, 1e-10)
        C_real = C_nominal / P_HH
        consumption_growth = self._annualised_growth(C_real, self._prev_C_real)

        # ── Residential investment ────────────────────────────────────────
        I_resid_nominal = (
            workers_act.I_h.sum()
            + state.workers_inact.I_h.sum()
            + firms.I_h_i.sum()
            + bank.I_h
        )
        P_CF = max(agg.P_bar_CF, 1e-10)
        I_resid_real = I_resid_nominal / P_CF
        resid_inv_growth = self._annualised_growth(I_resid_real, self._prev_I_resid_real)

        # ── CPI inflation ────────────────────────────────────────────────
        P_HH_new = agg.P_bar_HH
        cpi_inflation = self._annualised_growth(P_HH_new, self._prev_P_bar_HH,
                                                 is_price=True)

        # Core CPI: exclude energy (agri, g=0) and food components
        # Approximate: service sectors g=4,5 + manufacturing g=1 ex-energy
        core_weights = np.array([0.0, 0.16, 0.06, 0.20, 0.14, 0.44])
        core_weights /= core_weights.sum()
        P_core = float(np.dot(core_weights, agg.P_bar_g))
        P_core = max(P_core, 1e-10)
        core_cpi_inflation = self._annualised_growth(P_core, self._prev_P_core,
                                                      is_price=True)

        # ── Labour market ────────────────────────────────────────────────
        n_employed = int(np.sum(workers_act.O_h > 0))
        n_unemployed = int(np.sum(workers_act.O_h == 0))
        labour_force = n_employed + n_unemployed
        unemployment_rate = 100.0 * n_unemployed / max(labour_force, 1)

        # ── Fed Funds Rate ───────────────────────────────────────────────
        # Model stores quarterly rate; convert to annualised %
        fed_funds_rate_annual = 100.0 * ((1.0 + cb.r_bar) ** 4 - 1.0)

        # ── FCI (financial conditions index) ─────────────────────────────
        # Standardised: higher = tighter
        credit_spread_bps = fin.credit_spread * 10_000
        fci = (
            0.40 * (fed_funds_rate_annual - 2.0)          # deviation from neutral
            + 0.35 * (credit_spread_bps - 150.0) / 100.0  # normalised spread
            + 0.25 * (-fin.fci)                            # carry-through
        )

        # ── Update stored levels ─────────────────────────────────────────
        self._prev_Y_real = Y_real
        self._prev_C_real = C_real
        self._prev_I_resid_real = I_resid_real
        self._prev_P_bar_HH = P_HH_new
        self._prev_P_core = P_core

        return ObservableSnapshot(
            gdp_growth_qoq=gdp_growth_qoq,
            nominal_gdp=agg.Y,
            cpi_inflation_qoq=cpi_inflation,
            core_cpi_inflation_qoq=core_cpi_inflation,
            unemployment_rate=unemployment_rate,
            fed_funds_rate_annual=fed_funds_rate_annual,
            consumption_growth_qoq=consumption_growth,
            residential_inv_growth_qoq=resid_inv_growth,
            fci=fci,
            time_index=state.time_index,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _annualised_growth(
        current: float,
        previous: float | None,
        is_price: bool = False,
    ) -> float:
        """
        Compute annualised growth rate (%) from two levels.

        Returns 0.0 if previous is None (first observation).
        For prices, annualised inflation = ((P_t/P_{t-1})^4 - 1) * 100.
        For quantities, same formula in real terms.
        """
        if previous is None or previous <= 0 or current <= 0:
            # Fall back to a zero / small positive value on first step
            return 0.0
        qoq = current / previous
        annualised = (qoq ** 4 - 1.0) * 100.0
        # Clip to sensible economic range: [-50%, +50%]
        return float(np.clip(annualised, -50.0, 50.0))
