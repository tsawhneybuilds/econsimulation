"""CalibrationBundle dataclass — U.S.-adapted BeforeIT parameter structure."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

import numpy as np

from .provenance import ParameterProvenance


@dataclass
class StructuralParams:
    """Structural parameters: tax rates, productivities, sector shares."""
    # Number of firms and workers
    I: int = 100              # number of firms
    H_act: int = 1000         # active workers (employed + unemployed)
    H_inact: int = 200        # inactive workers
    G: int = 6                # number of sectors

    # Sector assignment probabilities (must sum to 1.0)
    sector_weights: list = field(default_factory=lambda: [
        0.012,   # Agriculture
        0.115,   # Manufacturing
        0.048,   # Construction
        0.189,   # Trade/Transport
        0.212,   # Finance/RE
        0.424,   # Services
    ])

    # Tax rates
    tau_INC: float = 0.22     # income tax rate
    tau_FIRM: float = 0.21    # corporate tax rate
    tau_VAT: float = 0.085    # effective VAT rate (U.S. sales tax proxy)
    tau_SIW: float = 0.0765   # social insurance contribution (employee FICA)
    tau_SIF: float = 0.0765   # social insurance contribution (employer FICA)
    tau_K: float = 0.21       # capital gains tax (same as corp for simplicity)

    # Unemployment benefit replacement rate
    theta_UB: float = 0.40    # fraction of last wage

    # Dividend payout fraction
    theta_DIV: float = 0.55

    # Sector productivity (Leontief)
    alpha_bar: list = field(default_factory=lambda: [
        0.85, 0.75, 0.80, 0.78, 0.72, 0.70
    ])  # average labour productivity per sector

    beta: list = field(default_factory=lambda: [
        0.12, 0.35, 0.28, 0.22, 0.15, 0.18
    ])  # intermediate goods productivity

    kappa: list = field(default_factory=lambda: [
        0.40, 0.55, 0.48, 0.45, 0.60, 0.42
    ])  # capital productivity

    # Capital depreciation rates per sector
    delta: list = field(default_factory=lambda: [
        0.025, 0.040, 0.035, 0.030, 0.020, 0.025
    ])

    # Markup (net tax rate on products)
    tau_Y: list = field(default_factory=lambda: [
        0.02, 0.04, 0.03, 0.03, 0.02, 0.025
    ])

    # Net tax rate on production
    tau_K_sect: list = field(default_factory=lambda: [
        0.015, 0.03, 0.025, 0.02, 0.015, 0.02
    ])


@dataclass
class MappingParams:
    """Model → NIPA mapping coefficients."""
    # GDP expenditure shares (2019Q4 NIPA)
    C_share: float = 0.682    # personal consumption
    I_share: float = 0.176    # gross private investment
    G_share: float = 0.174    # govt consumption + investment
    NX_share: float = -0.032  # net exports

    # Investment breakdown
    I_fixed_share: float = 0.835   # fixed investment fraction of total I
    I_resid_share: float = 0.165   # residential fraction of total I

    # Price index weights (PCE deflator basket, approx)
    w_food: float = 0.148
    w_energy: float = 0.052
    w_core: float = 0.800


@dataclass
class MeasurementParams:
    """Deflators and seasonal adjustment factors."""
    gdp_deflator_2019q4: float = 112.8    # BEA GDP deflator index 2012=100
    cpi_2019q4: float = 257.97            # BLS CPI-U, Dec 2019
    core_cpi_2019q4: float = 268.61       # BLS CPI less food/energy
    pce_deflator_2019q4: float = 110.5    # BEA PCE deflator 2012=100
    seasonal_adjustment: str = "SA"
    base_year: int = 2017


@dataclass
class InitialDistributions:
    """Initial state distributions from 2019Q4 data."""
    # Aggregate stocks (billions 2017 USD, SAAR)
    Y_0: float = 19_254.0      # real GDP 2019Q4
    C_0: float = 13_160.0      # real PCE 2019Q4
    I_0: float = 3_390.0       # real gross private investment
    G_0: float = 3_350.0       # real govt consumption + investment
    NX_0: float = -646.0       # real net exports

    # Financial stocks
    D_H: float = 2.5           # household deposits / annual income ratio
    K_H: float = 0.8           # household capital / income ratio
    E_k: float = 1_200.0       # bank equity (bn USD)
    L_G: float = 22_719.0      # federal debt held by public (bn USD, 2019Q4)

    # Sectoral GVA shares (sum to 1.0, approx 2019 BEA)
    gva_shares: list = field(default_factory=lambda: [
        0.012,   # Agriculture
        0.115,   # Manufacturing
        0.048,   # Construction
        0.189,   # Trade/Transport
        0.212,   # Finance/RE
        0.424,   # Services
    ])

    # Labour market
    unemployment_rate_0: float = 0.036   # 3.6% Dec 2019
    participation_rate_0: float = 0.632  # 63.2%

    # Price levels
    P_bar_0: float = 1.0        # normalised global price index


@dataclass
class ShockProcessParams:
    """Shock covariance matrix and AR(1) parameters for EA-equivalent."""
    # AR(1) for U.S. ROW (global GDP growth) shock
    alpha_Y_ROW: float = 0.70   # AR coefficient
    beta_Y_ROW: float = 0.006   # drift (quarterly)
    sigma_Y_ROW: float = 0.008  # std dev of innovation

    # AR(1) for U.S. ROW inflation shock
    alpha_pi_ROW: float = 0.65
    beta_pi_ROW: float = 0.005
    sigma_pi_ROW: float = 0.004

    # Export/import process
    alpha_E: float = 0.80
    beta_E: float = 0.003
    sigma_E: float = 0.010

    alpha_I: float = 0.75
    beta_I: float = 0.004
    sigma_I: float = 0.012

    # Taylor rule parameters
    rho: float = 0.80           # interest rate smoothing
    r_star: float = 0.005       # real neutral rate (quarterly)
    pi_star: float = 0.005      # inflation target (quarterly = 2% annual)
    xi_pi: float = 1.50         # weight on inflation gap
    xi_gamma: float = 0.50      # weight on output gap

    # Bank spread
    mu: float = 0.020           # loan spread over policy rate


@dataclass
class CalibrationBundle:
    """Full calibration bundle for U.S. ABM (mirrors BeforeIT.jl parameter dict)."""
    version_hash: str = ""
    reference_quarter: str = "2019Q4"
    structural: StructuralParams = field(default_factory=StructuralParams)
    mapping: MappingParams = field(default_factory=MappingParams)
    measurement: MeasurementParams = field(default_factory=MeasurementParams)
    initial_distributions: InitialDistributions = field(default_factory=InitialDistributions)
    shock_process: ShockProcessParams = field(default_factory=ShockProcessParams)
    provenance: Dict[str, ParameterProvenance] = field(default_factory=dict)

    def __post_init__(self):
        if not self.version_hash:
            self.version_hash = self._compute_hash()
        self._validate()

    def _compute_hash(self) -> str:
        d = {
            "reference_quarter": self.reference_quarter,
            "structural": {k: v for k, v in self.structural.__dict__.items()
                           if not callable(v)},
            "mapping": self.mapping.__dict__,
            "measurement": self.measurement.__dict__,
            "initial_distributions": {
                k: v for k, v in self.initial_distributions.__dict__.items()
                if not callable(v)
            },
            "shock_process": self.shock_process.__dict__,
        }
        canonical = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def _validate(self) -> None:
        s = self.structural
        # Sector weights sum to 1
        sw = sum(s.sector_weights)
        if abs(sw - 1.0) > 1e-6:
            raise ValueError(f"sector_weights sum to {sw:.6f}, expected 1.0")
        # GVA shares sum to 1
        gva = sum(self.initial_distributions.gva_shares)
        if abs(gva - 1.0) > 1e-6:
            raise ValueError(f"gva_shares sum to {gva:.6f}, expected 1.0")
        # Expenditure shares sum to ~1
        exp_sum = (self.mapping.C_share + self.mapping.I_share +
                   self.mapping.G_share + self.mapping.NX_share)
        if abs(exp_sum - 1.0) > 0.01:
            raise ValueError(f"NIPA expenditure shares sum to {exp_sum:.4f}, expected ~1.0")
        # All tax rates in [0, 1]
        for attr in ["tau_INC", "tau_FIRM", "tau_VAT", "tau_SIW", "tau_SIF"]:
            v = getattr(s, attr)
            if not (0 <= v <= 1):
                raise ValueError(f"{attr}={v} out of [0,1]")
