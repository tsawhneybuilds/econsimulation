"""SimulationState dataclass — all agent arrays + time index."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List

import numpy as np
import pandas as pd


@dataclass
class AggregateState:
    """Economy-wide aggregates."""
    Y: float = 0.0              # nominal GDP
    Y_real: float = 0.0         # real GDP (2017 USD, SAAR bn)
    pi_: float = 0.0            # quarterly inflation rate
    P_bar: float = 1.0          # global price index
    P_bar_HH: float = 1.0       # household (CPI) price index
    P_bar_CF: float = 1.0       # capital formation price index
    P_bar_g: np.ndarray = field(default_factory=lambda: np.ones(6))  # sector price indices
    Y_e: float = 0.0            # expected GDP
    gamma_e: float = 0.005      # expected quarterly growth
    pi_e: float = 0.005         # expected quarterly inflation
    r_bar: float = 0.0038       # central bank nominal rate (quarterly)
    # Running time series (populated during simulation)
    Y_hist: List[float] = field(default_factory=list)
    pi_hist: List[float] = field(default_factory=list)


@dataclass
class FirmState:
    """Vectorised firm arrays (length = I firms)."""
    G_i: np.ndarray = field(default_factory=lambda: np.zeros(100, dtype=int))     # sector assignment
    alpha_bar_i: np.ndarray = field(default_factory=lambda: np.ones(100))         # labour productivity
    beta_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.2)        # intermediate goods prod
    kappa_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.5)       # capital productivity
    w_i: np.ndarray = field(default_factory=lambda: np.ones(100))                 # wage paid
    w_bar_i: np.ndarray = field(default_factory=lambda: np.ones(100))             # average wage
    delta_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.03)      # depreciation
    tau_Y_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.03)      # product tax
    tau_K_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.02)      # production tax
    N_i: np.ndarray = field(default_factory=lambda: np.zeros(100, dtype=int))     # employment
    Y_i: np.ndarray = field(default_factory=lambda: np.ones(100))                 # production
    Q_i: np.ndarray = field(default_factory=lambda: np.ones(100))                 # sales
    Q_d_i: np.ndarray = field(default_factory=lambda: np.ones(100))               # demand
    P_i: np.ndarray = field(default_factory=lambda: np.ones(100))                 # price
    S_i: np.ndarray = field(default_factory=lambda: np.zeros(100))                # inventories
    K_i: np.ndarray = field(default_factory=lambda: np.ones(100))                 # capital stock
    M_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.2)           # intermediate goods
    L_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.5)           # outstanding loans
    pi_bar_i: np.ndarray = field(default_factory=lambda: np.zeros(100))           # operating margin
    D_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.1)           # deposits
    Pi_i: np.ndarray = field(default_factory=lambda: np.zeros(100))               # profits
    V_i: np.ndarray = field(default_factory=lambda: np.zeros(100, dtype=int))     # vacancies
    I_i: np.ndarray = field(default_factory=lambda: np.zeros(100))                # investment
    E_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.5)           # equity
    P_bar_i: np.ndarray = field(default_factory=lambda: np.ones(100))             # price index
    DS_i: np.ndarray = field(default_factory=lambda: np.zeros(100))               # delta inventories
    DM_i: np.ndarray = field(default_factory=lambda: np.zeros(100))               # delta intermediates
    DL_i: np.ndarray = field(default_factory=lambda: np.zeros(100))               # new loans
    DL_d_i: np.ndarray = field(default_factory=lambda: np.zeros(100))             # desired new loans
    K_e_i: np.ndarray = field(default_factory=lambda: np.ones(100))               # expected capital
    L_e_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.5)         # expected loans
    Q_s_i: np.ndarray = field(default_factory=lambda: np.ones(100))               # expected sales
    I_d_i: np.ndarray = field(default_factory=lambda: np.zeros(100))              # desired investment
    DM_d_i: np.ndarray = field(default_factory=lambda: np.zeros(100))             # desired intermediates
    N_d_i: np.ndarray = field(default_factory=lambda: np.zeros(100, dtype=int))   # desired employment
    Pi_e_i: np.ndarray = field(default_factory=lambda: np.zeros(100))             # expected profits
    # Owner household fields
    Y_h_i: np.ndarray = field(default_factory=lambda: np.ones(100))               # owner income
    C_d_h_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.6)       # desired consumption
    I_d_h_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.1)       # desired investment
    C_h_i: np.ndarray = field(default_factory=lambda: np.zeros(100))              # realised consumption
    I_h_i: np.ndarray = field(default_factory=lambda: np.zeros(100))              # realised investment
    K_h_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.8)         # owner capital
    D_h_i: np.ndarray = field(default_factory=lambda: np.ones(100) * 0.2)         # owner deposits

    @property
    def n_firms(self) -> int:
        return len(self.G_i)


@dataclass
class WorkerState:
    """Vectorised worker arrays (length = H workers)."""
    Y_h: np.ndarray = field(default_factory=lambda: np.ones(1000))     # disposable income
    D_h: np.ndarray = field(default_factory=lambda: np.ones(1000) * 2.5)  # deposits
    K_h: np.ndarray = field(default_factory=lambda: np.ones(1000) * 0.8)  # capital stock
    w_h: np.ndarray = field(default_factory=lambda: np.ones(1000))        # wage
    O_h: np.ndarray = field(default_factory=lambda: np.zeros(1000, dtype=int))  # occupation (firm idx, 0=unemp, -1=inact)
    C_d_h: np.ndarray = field(default_factory=lambda: np.ones(1000) * 0.7)   # desired consumption
    I_d_h: np.ndarray = field(default_factory=lambda: np.ones(1000) * 0.05)  # desired investment
    C_h: np.ndarray = field(default_factory=lambda: np.zeros(1000))           # realised consumption
    I_h: np.ndarray = field(default_factory=lambda: np.zeros(1000))           # realised investment

    @property
    def n_workers(self) -> int:
        return len(self.Y_h)


@dataclass
class BankState:
    """Single-bank state."""
    E_k: float = 1200.0         # equity capital
    Pi_k: float = 0.0           # profits
    Pi_e_k: float = 0.0         # expected profits
    D_k: float = 0.0            # net creditor/debtor position
    r: float = 0.04             # loan rate
    # Owner household
    Y_h: float = 0.0
    C_d_h: float = 0.0
    I_d_h: float = 0.0
    C_h: float = 0.0
    I_h: float = 0.0
    K_h: float = 0.8
    D_h: float = 2.5


@dataclass
class CentralBankState:
    """Central bank (Fed) state."""
    r_bar: float = 0.0038       # quarterly policy rate (≈1.55% annualised, 2019Q4)
    r_G: float = 0.0044         # 10y Treasury yield equivalent (quarterly)
    rho: float = 0.80           # smoothing parameter
    r_star: float = 0.005       # equilibrium real rate
    pi_star: float = 0.005      # inflation target (quarterly)
    xi_pi: float = 1.50         # Taylor inflation weight
    xi_gamma: float = 0.50      # Taylor output weight
    E_CB: float = 0.0           # central bank equity


@dataclass
class GovernmentState:
    """Federal government state."""
    alpha_G: float = 0.80       # AR coeff for govt consumption
    beta_G: float = 0.003       # drift
    sigma_G: float = 0.005      # std dev
    Y_G: float = 0.0            # tax revenues
    C_G: float = 3_350.0        # govt consumption (bn 2017 USD, SAAR)
    L_G: float = 22_719.0       # govt debt
    sb_inact: float = 0.0       # social benefits (inactive)
    sb_other: float = 0.0       # social benefits (general)
    C_d_j: np.ndarray = field(default_factory=lambda: np.ones(6))  # sectoral demand
    C_j: float = 0.0            # realised consumption
    P_j: float = 1.0            # price index


@dataclass
class ROTWState:
    """Rest-of-World state (U.S. ROW = global ex-U.S.)."""
    alpha_E: float = 0.80
    beta_E: float = 0.003
    sigma_E: float = 0.010
    alpha_I: float = 0.75
    beta_I: float = 0.004
    sigma_I: float = 0.012
    Y_ROW: float = 0.0          # global ex-U.S. GDP proxy
    gamma_ROW: float = 0.006    # global growth
    pi_ROW: float = 0.005       # global inflation
    alpha_pi_ROW: float = 0.65
    beta_pi_ROW: float = 0.005
    sigma_pi_ROW: float = 0.004
    alpha_Y_ROW: float = 0.70
    beta_Y_ROW: float = 0.006
    sigma_Y_ROW: float = 0.008
    D_RoW: float = 0.0          # net creditor/debtor vs ROW
    Y_I: float = 0.0            # import supply
    C_E: float = 0.0            # export demand
    C_d_l: np.ndarray = field(default_factory=lambda: np.ones(6))  # sector export demand
    C_l: float = 0.0            # realised exports
    Y_m: np.ndarray = field(default_factory=lambda: np.ones(6))
    Q_m: np.ndarray = field(default_factory=lambda: np.ones(6))
    Q_d_m: np.ndarray = field(default_factory=lambda: np.ones(6))
    P_m: np.ndarray = field(default_factory=lambda: np.ones(6))
    P_l: float = 1.0


@dataclass
class FinancialState:
    """Financial conditions."""
    credit_spread: float = 0.015    # credit spread over policy rate
    term_premium: float = 0.010     # term premium
    fci: float = 0.0                # financial conditions index (standardised)
    nfc_debt_gdp: float = 0.75      # non-financial corp debt/GDP


@dataclass
class SimData:
    """Collected time-series during simulation."""
    gdp_growth: List[float] = field(default_factory=list)
    cpi_inflation: List[float] = field(default_factory=list)
    core_cpi_inflation: List[float] = field(default_factory=list)
    unemployment_rate: List[float] = field(default_factory=list)
    fed_funds_rate: List[float] = field(default_factory=list)
    consumption_growth: List[float] = field(default_factory=list)
    residential_inv_growth: List[float] = field(default_factory=list)
    fci: List[float] = field(default_factory=list)

    def to_dataframe(self, origin_quarter: str = "2019Q4") -> pd.DataFrame:
        """Convert collected series to a DataFrame with PeriodIndex."""
        n = len(self.gdp_growth)
        if n == 0:
            return pd.DataFrame()

        # Build forward period index
        start = pd.Period(origin_quarter, freq="Q") + 1
        idx = pd.period_range(start=start, periods=n, freq="Q")

        return pd.DataFrame(
            {
                "gdp_growth": self.gdp_growth,
                "cpi_inflation": self.cpi_inflation,
                "core_cpi_inflation": self.core_cpi_inflation,
                "unemployment_rate": self.unemployment_rate,
                "fed_funds_rate": self.fed_funds_rate,
                "consumption_growth": self.consumption_growth,
                "residential_inv_growth": self.residential_inv_growth,
                "fci": self.fci,
            },
            index=idx,
        )


@dataclass
class SimulationState:
    """Full simulation state — all agents + time index."""
    time_index: int = 0
    rng_state: Optional[np.random.Generator] = None
    origin_quarter: str = "2019Q4"
    aggregate: AggregateState = field(default_factory=AggregateState)
    firms: FirmState = field(default_factory=FirmState)
    workers_act: WorkerState = field(default_factory=WorkerState)
    workers_inact: WorkerState = field(default_factory=lambda: WorkerState(
        Y_h=np.zeros(200),
        D_h=np.ones(200) * 2.5,
        K_h=np.ones(200) * 0.8,
        w_h=np.zeros(200),
        O_h=np.full(200, -1, dtype=int),
        C_d_h=np.ones(200) * 0.5,
        I_d_h=np.zeros(200),
        C_h=np.zeros(200),
        I_h=np.zeros(200),
    ))
    bank: BankState = field(default_factory=BankState)
    central_bank: CentralBankState = field(default_factory=CentralBankState)
    government: GovernmentState = field(default_factory=GovernmentState)
    rotw: ROTWState = field(default_factory=ROTWState)
    financial: FinancialState = field(default_factory=FinancialState)
    data: SimData = field(default_factory=SimData)

    def __post_init__(self):
        if self.rng_state is None:
            self.rng_state = np.random.default_rng(42)

    def check_no_nan_inf(self) -> None:
        """Raise ValueError if any numeric state contains NaN or Inf."""
        import dataclasses

        def _check_array(arr, name: str):
            if isinstance(arr, np.ndarray):
                if not np.all(np.isfinite(arr)):
                    bad = arr[~np.isfinite(arr)]
                    raise ValueError(f"NaN/Inf in {name}: {bad[:3]}")
            elif isinstance(arr, float):
                if not np.isfinite(arr):
                    raise ValueError(f"NaN/Inf in {name}: {arr}")

        for fname, fval in [
            ("aggregate.Y", self.aggregate.Y),
            ("aggregate.P_bar", self.aggregate.P_bar),
            ("aggregate.r_bar", self.aggregate.r_bar),
            ("firms.Y_i", self.firms.Y_i),
            ("firms.P_i", self.firms.P_i),
            ("firms.K_i", self.firms.K_i),
            ("workers_act.Y_h", self.workers_act.Y_h),
            ("workers_act.D_h", self.workers_act.D_h),
        ]:
            _check_array(fval, fname)
