"""Hardcoded 2019Q4 U.S. calibration parameters."""
from __future__ import annotations

from datetime import date

from .provenance import ParameterProvenance
from .us_calibration import (
    CalibrationBundle,
    StructuralParams,
    MappingParams,
    MeasurementParams,
    InitialDistributions,
    ShockProcessParams,
)

_BEA_2020 = ParameterProvenance(
    source="BEA_NIPA_2020Q1_ADVANCE",
    vintage_date=date(2020, 1, 30),
    is_assumption=False,
    notes="BEA advance estimate, 2019Q4",
)
_BLS_2020 = ParameterProvenance(
    source="BLS_CPS_2020Q1",
    vintage_date=date(2020, 1, 10),
    is_assumption=False,
)
_FRB_2020 = ParameterProvenance(
    source="FRB_H15_2020Q1",
    vintage_date=date(2020, 1, 2),
    is_assumption=False,
)
_ASSUMPTION = ParameterProvenance(
    source="CALIBRATED",
    vintage_date=date(2020, 6, 1),
    is_assumption=True,
    notes="Calibrated to match 2019Q4 moments",
)


def build_us_2019q4_calibration() -> CalibrationBundle:
    """
    Construct the 2019Q4 U.S. calibration bundle.

    All stock values in billions of 2017 chained USD (SAAR) unless noted.
    Sources: BEA NIPA Table 1.1.6 (advance), BLS, Federal Reserve H.15.
    """
    structural = StructuralParams(
        I=100,
        H_act=1000,
        H_inact=200,
        G=6,
        sector_weights=[0.012, 0.115, 0.048, 0.189, 0.212, 0.424],
        tau_INC=0.22,
        tau_FIRM=0.21,
        tau_VAT=0.085,
        tau_SIW=0.0765,
        tau_SIF=0.0765,
        tau_K=0.21,
        theta_UB=0.40,
        theta_DIV=0.55,
        alpha_bar=[0.85, 0.75, 0.80, 0.78, 0.72, 0.70],
        beta=[0.12, 0.35, 0.28, 0.22, 0.15, 0.18],
        kappa=[0.40, 0.55, 0.48, 0.45, 0.60, 0.42],
        delta=[0.025, 0.040, 0.035, 0.030, 0.020, 0.025],
        tau_Y=[0.02, 0.04, 0.03, 0.03, 0.02, 0.025],
        tau_K_sect=[0.015, 0.03, 0.025, 0.02, 0.015, 0.02],
    )

    mapping = MappingParams(
        C_share=0.682,
        I_share=0.176,
        G_share=0.174,
        NX_share=-0.032,
        I_fixed_share=0.835,
        I_resid_share=0.165,
        w_food=0.148,
        w_energy=0.052,
        w_core=0.800,
    )

    measurement = MeasurementParams(
        gdp_deflator_2019q4=112.8,
        cpi_2019q4=257.97,
        core_cpi_2019q4=268.61,
        pce_deflator_2019q4=110.5,
        seasonal_adjustment="SA",
        base_year=2017,
    )

    initial_distributions = InitialDistributions(
        # BEA NIPA Table 1.1.6 advance, 2019Q4, billions chained 2017 USD SAAR
        Y_0=19_254.0,
        C_0=13_160.0,
        I_0=3_390.0,
        G_0=3_350.0,
        NX_0=-646.0,
        D_H=2.5,
        K_H=0.8,
        E_k=1_200.0,
        L_G=22_719.0,
        gva_shares=[0.012, 0.115, 0.048, 0.189, 0.212, 0.424],
        unemployment_rate_0=0.036,
        participation_rate_0=0.632,
        P_bar_0=1.0,
    )

    shock_process = ShockProcessParams(
        alpha_Y_ROW=0.70,
        beta_Y_ROW=0.006,
        sigma_Y_ROW=0.008,
        alpha_pi_ROW=0.65,
        beta_pi_ROW=0.005,
        sigma_pi_ROW=0.004,
        alpha_E=0.80,
        beta_E=0.003,
        sigma_E=0.010,
        alpha_I=0.75,
        beta_I=0.004,
        sigma_I=0.012,
        rho=0.80,
        r_star=0.005,
        pi_star=0.005,
        xi_pi=1.50,
        xi_gamma=0.50,
        mu=0.020,
    )

    provenance = {
        "gdp": _BEA_2020,
        "consumption": _BEA_2020,
        "investment": _BEA_2020,
        "government": _BEA_2020,
        "net_exports": _BEA_2020,
        "unemployment_rate": _BLS_2020,
        "participation_rate": _BLS_2020,
        "fed_funds_rate": _FRB_2020,
        "structural_params": _ASSUMPTION,
        "shock_params": _ASSUMPTION,
        "tax_rates": _ASSUMPTION,
    }

    return CalibrationBundle(
        reference_quarter="2019Q4",
        structural=structural,
        mapping=mapping,
        measurement=measurement,
        initial_distributions=initial_distributions,
        shock_process=shock_process,
        provenance=provenance,
    )
