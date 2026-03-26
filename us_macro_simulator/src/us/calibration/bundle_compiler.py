"""Compiler for Julia-facing U.S. calibration bundles."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .us_baseline_2019q4 import build_us_2019q4_calibration


# Keys consumed by BeforeIT.jl calibration and U.S. Stage 1 wrappers.
REQUIRED_CALIBRATION_KEYS = [
    "years_num",
    "quarters_num",
    "firms",
    "employees",
    "population",
    "inactive_census",
    "unemployed_census",
    "wages",
    "wages_by_sector",
    "property_income",
    "mixed_income",
    "social_benefits",
    "unemployment_benefits",
    "pension_benefits",
    "corporate_tax",
    "social_contributions",
    "income_tax",
    "capital_taxes",
    "fixed_assets",
    "dwellings",
    "fixed_assets_eu7",
    "dwellings_eu7",
    "nominal_nace64_output_eu7",
    "gross_capitalformation_dwellings",
    "capital_consumption",
    "nace64_capital_consumption",
    "nominal_nace64_output",
    "household_cash_quarterly",
    "firm_cash_quarterly",
    "firm_debt_quarterly",
    "government_debt_quarterly",
    "bank_equity_quarterly",
    "firm_interest",
    "firm_interest_quarterly",
    "interest_government_debt",
    "interest_government_debt_quarterly",
    "government_deficit",
    "government_deficit_quarterly",
]

REQUIRED_FIGARO_KEYS = [
    "intermediate_consumption",
    "household_consumption",
    "fixed_capitalformation",
    "exports",
    "imports",
    "compensation_employees",
    "operating_surplus",
    "government_consumption",
    "taxes_products_household",
    "taxes_products_capitalformation",
    "taxes_products_government",
    "taxes_products",
    "taxes_production",
]

REQUIRED_TIMESERIES_KEYS = [
    "periods",
    "years",
    "quarters_num",
    "years_num",
    "real_gdp_quarterly",
    "real_gdp",
    "real_household_consumption_quarterly",
    "real_household_consumption",
    "real_government_consumption_quarterly",
    "real_government_consumption",
    "real_final_consumption_quarterly",
    "real_final_consumption",
    "real_capitalformation_quarterly",
    "real_capitalformation",
    "real_fixed_capitalformation_quarterly",
    "real_fixed_capitalformation",
    "real_exports_quarterly",
    "real_exports",
    "real_imports_quarterly",
    "real_imports",
    "real_gva_quarterly",
    "real_gva",
    "nominal_gdp_quarterly",
    "nominal_gdp",
    "nominal_household_consumption_quarterly",
    "nominal_household_consumption",
    "nominal_government_consumption_quarterly",
    "nominal_government_consumption",
    "nominal_final_consumption_quarterly",
    "nominal_final_consumption",
    "nominal_capitalformation_quarterly",
    "nominal_capitalformation",
    "nominal_fixed_capitalformation_quarterly",
    "nominal_fixed_capitalformation",
    "nominal_exports_quarterly",
    "nominal_exports",
    "nominal_imports_quarterly",
    "nominal_imports",
    "nominal_gva_quarterly",
    "nominal_gva",
    "unemployment_rate_quarterly",
    "euribor",
    "gdp_deflator_quarterly",
    "gdp_deflator",
    "gdp_deflator_growth_quarterly",
    "gdp_deflator_growth",
]

BEFOREIT62_BUCKETS = (4, 8, 4, 10, 8, 28)


@dataclass(frozen=True)
class CalibrationArtifactManifest:
    schema_version: str
    compiler_version: str
    reference_quarter: str
    sector_count: int
    source_mode: str
    observed_macro_file: str
    calibration_file: str
    figaro_file: str
    data_file: str
    ea_file: str
    provenance_file: str
    release_manifest_file: str
    max_calibration_date: str
    estimation_date: str
    generated_at: str


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def matlab_datenum(ts: pd.Timestamp) -> float:
    """Approximate MATLAB datenum compatible with BeforeIT.jl `date2num`."""
    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)
    frac = (ts.hour * 3600 + ts.minute * 60 + ts.second) / 86400.0
    return float(ts.to_pydatetime().toordinal() + 366 + frac)


def _normalise_observed(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    if "period" not in df.columns:
        if isinstance(df.index, pd.PeriodIndex):
            df = df.reset_index().rename(columns={"index": "period"})
            df["period"] = df["period"].astype(str)
        else:
            raise ValueError("Observed data must contain a 'period' column or quarterly PeriodIndex.")
    df["period"] = df["period"].astype(str)
    for col in df.columns:
        if col == "period":
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("period").reset_index(drop=True)


def _period_index(periods: pd.Series) -> pd.PeriodIndex:
    return pd.PeriodIndex(periods.astype(str), freq="Q")


def _annual_average(periods: pd.PeriodIndex, values: np.ndarray) -> tuple[list[int], np.ndarray]:
    years = sorted(periods.year.unique())
    annual = []
    for year in years:
        annual.append(float(np.nanmean(values[periods.year == year])))
    return years, np.asarray(annual, dtype=float)


def _annual_growth(values: np.ndarray) -> np.ndarray:
    growth = np.zeros(values.shape, dtype=float)
    for idx in range(1, len(values)):
        prev, curr = values[idx - 1], values[idx]
        if np.isfinite(prev) and np.isfinite(curr) and prev != 0:
            growth[idx] = (curr / prev - 1.0) * 100.0
    return growth


def _annualised_growth(values: np.ndarray) -> np.ndarray:
    growth = np.zeros(values.shape, dtype=float)
    for idx in range(1, len(values)):
        prev, curr = values[idx - 1], values[idx]
        if np.isfinite(prev) and np.isfinite(curr) and prev > 0 and curr > 0:
            growth[idx] = ((curr / prev) ** 4 - 1.0) * 100.0
    return growth


def _annualise_quarterly_flow(values: np.ndarray, target_years: int) -> np.ndarray:
    if len(values) >= target_years * 4 and len(values) % 4 == 0:
        return values.reshape(-1, 4).mean(axis=1) * 4.0
    return np.full(target_years, float(np.nanmean(values) * 4.0), dtype=float)


def _quarter_end_iso(period_label: str) -> str:
    ts = pd.Period(period_label, freq="Q").asfreq("Q").to_timestamp(how="end")
    return ts.normalize().date().isoformat()


def _expand_broad_vector(values: list[float] | np.ndarray, target_count: int) -> np.ndarray:
    broad = np.asarray(values, dtype=float)
    if target_count == len(broad):
        return broad.copy()
    if target_count != sum(BEFOREIT62_BUCKETS):
        raise ValueError(f"Unsupported target_count={target_count}; expected {sum(BEFOREIT62_BUCKETS)}")
    expanded: list[float] = []
    for value, bucket_size in zip(broad, BEFOREIT62_BUCKETS):
        expanded.extend([value / bucket_size] * bucket_size)
    return np.asarray(expanded, dtype=float)


def _expand_broad_parameter(values: list[float] | np.ndarray, target_count: int) -> np.ndarray:
    broad = np.asarray(values, dtype=float)
    if target_count == len(broad):
        return broad.copy()
    if target_count != sum(BEFOREIT62_BUCKETS):
        raise ValueError(f"Unsupported target_count={target_count}; expected {sum(BEFOREIT62_BUCKETS)}")
    expanded: list[float] = []
    for value, bucket_size in zip(broad, BEFOREIT62_BUCKETS):
        expanded.extend([value] * bucket_size)
    return np.asarray(expanded, dtype=float)


def _matrix_from_totals(totals: np.ndarray, supplier_weights: np.ndarray, scale: float = 1.0) -> np.ndarray:
    matrix = np.outer(supplier_weights, totals * scale)
    col_sums = matrix.sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        factors = np.where(col_sums > 0, totals / col_sums, 0.0)
    return matrix * factors


def _series_or_default(df: pd.DataFrame, name: str, default: np.ndarray | None = None) -> np.ndarray | None:
    if name not in df.columns:
        return None if default is None else np.asarray(default, dtype=float)
    return df[name].astype(float).to_numpy()


def build_bootstrap_timeseries(raw: pd.DataFrame) -> dict[str, Any]:
    """Build the Julia `data` dict from a quarterly observed panel."""
    df = _normalise_observed(raw)
    periods = _period_index(df["period"])
    period_labels = periods.astype(str).tolist()
    quarter_dates = periods.asfreq("Q").to_timestamp(how="end").normalize()

    gdp = df["GDPC1"].to_numpy(dtype=float)
    pce = df["PCECC96"].to_numpy(dtype=float)
    residential = df["PRFI"].to_numpy(dtype=float)
    nonresidential = _series_or_default(df, "PNFIC1", residential / 0.165 - residential)
    fixed_capital = residential + nonresidential
    capitalformation = fixed_capital * 1.02
    government = _series_or_default(df, "GCEC1")
    if government is None:
        government = gdp * 0.17
    exports = _series_or_default(df, "EXPGSC1")
    if exports is None:
        exports = gdp * 0.12
    imports = _series_or_default(df, "IMPGSC1")
    if imports is None:
        imports = gdp * 0.15
    final_consumption = pce + government
    real_gva = gdp * 0.92

    cpi = df["CPIAUCSL"].to_numpy(dtype=float)
    core_cpi = _series_or_default(df, "CPILFESL", cpi)
    fci = _series_or_default(df, "FCI", np.zeros_like(gdp))
    gdpdef = _series_or_default(df, "GDPDEF")
    price_index = (gdpdef / gdpdef[0]) if gdpdef is not None else (cpi / cpi[0])
    core_price_index = core_cpi / core_cpi[0]

    nominal_gdp = gdp * price_index
    nominal_household_consumption = pce * price_index
    nominal_government_consumption = government * price_index
    nominal_final_consumption = final_consumption * price_index
    nominal_capitalformation = capitalformation * price_index
    nominal_fixed_capitalformation = fixed_capital * price_index
    nominal_exports = exports * price_index
    nominal_imports = imports * price_index
    nominal_gva = real_gva * price_index
    wages = nominal_gdp * 0.44
    compensation_employees = nominal_gdp * 0.57
    operating_surplus = nominal_gdp * 0.28

    years, real_gdp_annual = _annual_average(periods, gdp)
    _, real_household_consumption_annual = _annual_average(periods, pce)
    _, real_government_consumption_annual = _annual_average(periods, government)
    _, real_final_consumption_annual = _annual_average(periods, final_consumption)
    _, real_capitalformation_annual = _annual_average(periods, capitalformation)
    _, real_fixed_capitalformation_annual = _annual_average(periods, fixed_capital)
    _, real_exports_annual = _annual_average(periods, exports)
    _, real_imports_annual = _annual_average(periods, imports)
    _, real_gva_annual = _annual_average(periods, real_gva)

    _, nominal_gdp_annual = _annual_average(periods, nominal_gdp)
    _, nominal_household_consumption_annual = _annual_average(periods, nominal_household_consumption)
    _, nominal_government_consumption_annual = _annual_average(periods, nominal_government_consumption)
    _, nominal_final_consumption_annual = _annual_average(periods, nominal_final_consumption)
    _, nominal_capitalformation_annual = _annual_average(periods, nominal_capitalformation)
    _, nominal_fixed_capitalformation_annual = _annual_average(periods, nominal_fixed_capitalformation)
    _, nominal_exports_annual = _annual_average(periods, nominal_exports)
    _, nominal_imports_annual = _annual_average(periods, nominal_imports)
    _, nominal_gva_annual = _annual_average(periods, nominal_gva)
    _, wages_annual = _annual_average(periods, wages)
    _, compensation_employees_annual = _annual_average(periods, compensation_employees)
    _, operating_surplus_annual = _annual_average(periods, operating_surplus)
    _, unemployment_annual = _annual_average(periods, df["UNRATE"].to_numpy(dtype=float) / 100.0)
    _, policy_rate_annual = _annual_average(periods, df["FEDFUNDS"].to_numpy(dtype=float) / 100.0)
    _, deflator_annual = _annual_average(periods, price_index)
    _, core_price_index_annual = _annual_average(periods, core_price_index)

    deflator_growth_q = _annualised_growth(price_index + np.finfo(float).eps)
    deflator_growth_y = _annual_growth(deflator_annual)
    nominal_gdp_growth_q = _annualised_growth(nominal_gdp)
    nominal_household_consumption_growth_q = _annualised_growth(nominal_household_consumption)
    nominal_government_consumption_growth_q = _annualised_growth(nominal_government_consumption)
    nominal_final_consumption_growth_q = _annualised_growth(nominal_final_consumption)
    nominal_capitalformation_growth_q = _annualised_growth(nominal_capitalformation)
    nominal_fixed_capitalformation_growth_q = _annualised_growth(nominal_fixed_capitalformation)
    nominal_exports_growth_q = _annualised_growth(nominal_exports)
    nominal_imports_growth_q = _annualised_growth(nominal_imports)
    nominal_gva_growth_q = _annualised_growth(nominal_gva)
    real_gdp_growth_q = _annualised_growth(gdp)
    real_household_consumption_growth_q = _annualised_growth(pce)
    real_government_consumption_growth_q = _annualised_growth(government)
    real_final_consumption_growth_q = _annualised_growth(final_consumption)
    real_capitalformation_growth_q = _annualised_growth(capitalformation)
    real_fixed_capitalformation_growth_q = _annualised_growth(fixed_capital)
    real_exports_growth_q = _annualised_growth(exports)
    real_imports_growth_q = _annualised_growth(imports)
    real_gva_growth_q = _annualised_growth(real_gva)
    nominal_gdp_growth_y = _annual_growth(nominal_gdp_annual)
    nominal_household_consumption_growth_y = _annual_growth(nominal_household_consumption_annual)
    nominal_government_consumption_growth_y = _annual_growth(nominal_government_consumption_annual)
    nominal_final_consumption_growth_y = _annual_growth(nominal_final_consumption_annual)
    nominal_capitalformation_growth_y = _annual_growth(nominal_capitalformation_annual)
    nominal_fixed_capitalformation_growth_y = _annual_growth(nominal_fixed_capitalformation_annual)
    nominal_exports_growth_y = _annual_growth(nominal_exports_annual)
    nominal_imports_growth_y = _annual_growth(nominal_imports_annual)
    nominal_gva_growth_y = _annual_growth(nominal_gva_annual)
    real_gdp_growth_y = _annual_growth(real_gdp_annual)
    real_household_consumption_growth_y = _annual_growth(real_household_consumption_annual)
    real_government_consumption_growth_y = _annual_growth(real_government_consumption_annual)
    real_final_consumption_growth_y = _annual_growth(real_final_consumption_annual)
    real_capitalformation_growth_y = _annual_growth(real_capitalformation_annual)
    real_fixed_capitalformation_growth_y = _annual_growth(real_fixed_capitalformation_annual)
    real_exports_growth_y = _annual_growth(real_exports_annual)
    real_imports_growth_y = _annual_growth(real_imports_annual)
    real_gva_growth_y = _annual_growth(real_gva_annual)

    quarters_num = [matlab_datenum(pd.Timestamp(ts)) for ts in quarter_dates]
    years_num = [matlab_datenum(pd.Timestamp(year=year, month=12, day=31)) for year in years]

    return {
        "periods": period_labels,
        "years": years,
        "quarters_num": quarters_num,
        "years_num": years_num,
        "real_gdp_quarterly": gdp.tolist(),
        "real_gdp": real_gdp_annual.tolist(),
        "real_household_consumption_quarterly": pce.tolist(),
        "real_household_consumption": real_household_consumption_annual.tolist(),
        "real_government_consumption_quarterly": government.tolist(),
        "real_government_consumption": real_government_consumption_annual.tolist(),
        "real_final_consumption_quarterly": final_consumption.tolist(),
        "real_final_consumption": real_final_consumption_annual.tolist(),
        "real_capitalformation_quarterly": capitalformation.tolist(),
        "real_capitalformation": real_capitalformation_annual.tolist(),
        "real_fixed_capitalformation_quarterly": fixed_capital.tolist(),
        "real_fixed_capitalformation": real_fixed_capitalformation_annual.tolist(),
        "real_exports_quarterly": exports.tolist(),
        "real_exports": real_exports_annual.tolist(),
        "real_imports_quarterly": imports.tolist(),
        "real_imports": real_imports_annual.tolist(),
        "real_gva_quarterly": real_gva.tolist(),
        "real_gva": real_gva_annual.tolist(),
        "nominal_gdp_quarterly": nominal_gdp.tolist(),
        "nominal_gdp": nominal_gdp_annual.tolist(),
        "nominal_household_consumption_quarterly": nominal_household_consumption.tolist(),
        "nominal_household_consumption": nominal_household_consumption_annual.tolist(),
        "nominal_government_consumption_quarterly": nominal_government_consumption.tolist(),
        "nominal_government_consumption": nominal_government_consumption_annual.tolist(),
        "nominal_final_consumption_quarterly": nominal_final_consumption.tolist(),
        "nominal_final_consumption": nominal_final_consumption_annual.tolist(),
        "nominal_capitalformation_quarterly": nominal_capitalformation.tolist(),
        "nominal_capitalformation": nominal_capitalformation_annual.tolist(),
        "nominal_fixed_capitalformation_quarterly": nominal_fixed_capitalformation.tolist(),
        "nominal_fixed_capitalformation": nominal_fixed_capitalformation_annual.tolist(),
        "nominal_exports_quarterly": nominal_exports.tolist(),
        "nominal_exports": nominal_exports_annual.tolist(),
        "nominal_imports_quarterly": nominal_imports.tolist(),
        "nominal_imports": nominal_imports_annual.tolist(),
        "nominal_gva_quarterly": nominal_gva.tolist(),
        "nominal_gva": nominal_gva_annual.tolist(),
        "wages_quarterly": wages.tolist(),
        "wages": wages_annual.tolist(),
        "compensation_employees_quarterly": compensation_employees.tolist(),
        "compensation_employees": compensation_employees_annual.tolist(),
        "operating_surplus_quarterly": operating_surplus.tolist(),
        "operating_surplus": operating_surplus_annual.tolist(),
        "unemployment_rate_quarterly": (df["UNRATE"].to_numpy(dtype=float) / 100.0).tolist(),
        "unemployment_rate": unemployment_annual.tolist(),
        "euribor": (df["FEDFUNDS"].to_numpy(dtype=float) / 100.0).tolist(),
        "euribor_annual": policy_rate_annual.tolist(),
        "euribor_yearly": policy_rate_annual.tolist(),
        "gdp_deflator_quarterly": price_index.tolist(),
        "gdp_deflator": deflator_annual.tolist(),
        "household_consumption_deflator_quarterly": price_index.tolist(),
        "household_consumption_deflator": deflator_annual.tolist(),
        "government_consumption_deflator_quarterly": price_index.tolist(),
        "government_consumption_deflator": deflator_annual.tolist(),
        "final_consumption_deflator_quarterly": price_index.tolist(),
        "final_consumption_deflator": deflator_annual.tolist(),
        "capitalformation_deflator_quarterly": price_index.tolist(),
        "capitalformation_deflator": deflator_annual.tolist(),
        "fixed_capitalformation_deflator_quarterly": price_index.tolist(),
        "fixed_capitalformation_deflator": deflator_annual.tolist(),
        "exports_deflator_quarterly": price_index.tolist(),
        "exports_deflator": deflator_annual.tolist(),
        "imports_deflator_quarterly": price_index.tolist(),
        "imports_deflator": deflator_annual.tolist(),
        "gva_deflator_quarterly": price_index.tolist(),
        "gva_deflator": deflator_annual.tolist(),
        "nace10_gva_deflator_quarterly": price_index.tolist(),
        "nace10_gva_deflator": deflator_annual.tolist(),
        "gdp_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "gdp_deflator_growth": deflator_growth_y.tolist(),
        "household_consumption_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "household_consumption_deflator_growth": deflator_growth_y.tolist(),
        "government_consumption_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "government_consumption_deflator_growth": deflator_growth_y.tolist(),
        "final_consumption_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "final_consumption_deflator_growth": deflator_growth_y.tolist(),
        "capitalformation_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "capitalformation_deflator_growth": deflator_growth_y.tolist(),
        "fixed_capitalformation_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "fixed_capitalformation_deflator_growth": deflator_growth_y.tolist(),
        "exports_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "exports_deflator_growth": deflator_growth_y.tolist(),
        "imports_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "imports_deflator_growth": deflator_growth_y.tolist(),
        "gva_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "gva_deflator_growth": deflator_growth_y.tolist(),
        "nace10_gva_deflator_growth_quarterly": deflator_growth_q.tolist(),
        "nace10_gva_deflator_growth": deflator_growth_y.tolist(),
        "real_gdp_growth_quarterly": real_gdp_growth_q.tolist(),
        "real_household_consumption_growth_quarterly": real_household_consumption_growth_q.tolist(),
        "real_government_consumption_growth_quarterly": real_government_consumption_growth_q.tolist(),
        "real_final_consumption_growth_quarterly": real_final_consumption_growth_q.tolist(),
        "real_capitalformation_growth_quarterly": real_capitalformation_growth_q.tolist(),
        "real_fixed_capitalformation_growth_quarterly": real_fixed_capitalformation_growth_q.tolist(),
        "real_exports_growth_quarterly": real_exports_growth_q.tolist(),
        "real_imports_growth_quarterly": real_imports_growth_q.tolist(),
        "real_gva_growth_quarterly": real_gva_growth_q.tolist(),
        "nominal_gdp_growth_quarterly": nominal_gdp_growth_q.tolist(),
        "nominal_household_consumption_growth_quarterly": nominal_household_consumption_growth_q.tolist(),
        "nominal_government_consumption_growth_quarterly": nominal_government_consumption_growth_q.tolist(),
        "nominal_final_consumption_growth_quarterly": nominal_final_consumption_growth_q.tolist(),
        "nominal_capitalformation_growth_quarterly": nominal_capitalformation_growth_q.tolist(),
        "nominal_fixed_capitalformation_growth_quarterly": nominal_fixed_capitalformation_growth_q.tolist(),
        "nominal_exports_growth_quarterly": nominal_exports_growth_q.tolist(),
        "nominal_imports_growth_quarterly": nominal_imports_growth_q.tolist(),
        "nominal_gva_growth_quarterly": nominal_gva_growth_q.tolist(),
        "real_gdp_growth": real_gdp_growth_y.tolist(),
        "real_household_consumption_growth": real_household_consumption_growth_y.tolist(),
        "real_government_consumption_growth": real_government_consumption_growth_y.tolist(),
        "real_final_consumption_growth": real_final_consumption_growth_y.tolist(),
        "real_capitalformation_growth": real_capitalformation_growth_y.tolist(),
        "real_fixed_capitalformation_growth": real_fixed_capitalformation_growth_y.tolist(),
        "real_exports_growth": real_exports_growth_y.tolist(),
        "real_imports_growth": real_imports_growth_y.tolist(),
        "real_gva_growth": real_gva_growth_y.tolist(),
        "nominal_gdp_growth": nominal_gdp_growth_y.tolist(),
        "nominal_household_consumption_growth": nominal_household_consumption_growth_y.tolist(),
        "nominal_government_consumption_growth": nominal_government_consumption_growth_y.tolist(),
        "nominal_final_consumption_growth": nominal_final_consumption_growth_y.tolist(),
        "nominal_capitalformation_growth": nominal_capitalformation_growth_y.tolist(),
        "nominal_fixed_capitalformation_growth": nominal_fixed_capitalformation_growth_y.tolist(),
        "nominal_exports_growth": nominal_exports_growth_y.tolist(),
        "nominal_imports_growth": nominal_imports_growth_y.tolist(),
        "nominal_gva_growth": nominal_gva_growth_y.tolist(),
        "core_price_index_quarterly": core_price_index.tolist(),
        "core_price_index": core_price_index_annual.tolist(),
        "fci_quarterly": fci.tolist(),
    }


def build_bootstrap_ea(data: dict[str, Any]) -> dict[str, Any]:
    """Build a coarse `global_ex_us`/EA-compatible block."""
    foreign_gdp = np.asarray(data["real_gdp_quarterly"], dtype=float) * 3.0
    foreign_deflator = np.asarray(data["gdp_deflator_quarterly"], dtype=float) * 1.02
    years = data["years"]
    periods = _period_index(pd.Series(data["periods"]))
    _, foreign_gdp_annual = _annual_average(periods, foreign_gdp)
    _, foreign_nominal_gdp_annual = _annual_average(periods, foreign_gdp * foreign_deflator)
    _, foreign_deflator_annual = _annual_average(periods, foreign_deflator)
    return {
        "periods": list(data["periods"]),
        "years": years,
        "quarters_num": list(data["quarters_num"]),
        "years_num": list(data["years_num"]),
        "real_gdp_quarterly": foreign_gdp.tolist(),
        "real_gdp": foreign_gdp_annual.tolist(),
        "nominal_gdp_quarterly": (foreign_gdp * foreign_deflator).tolist(),
        "nominal_gdp": foreign_nominal_gdp_annual.tolist(),
        "gdp_deflator_quarterly": foreign_deflator.tolist(),
        "gdp_deflator": foreign_deflator_annual.tolist(),
        "gdp_deflator_growth_quarterly": _annualised_growth(foreign_deflator).tolist(),
        "gdp_deflator_growth": _annual_growth(foreign_deflator_annual).tolist(),
    }


def build_bootstrap_structural_bundle(
    data: dict[str, Any],
    *,
    reference_quarter: str,
    sector_count: int = 62,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Create a Julia-facing structural bundle from the bootstrap calibration seed."""
    seed = build_us_2019q4_calibration()
    if sector_count != 6 and sector_count != sum(BEFOREIT62_BUCKETS):
        raise ValueError(f"Unsupported sector_count={sector_count}")

    broad_weights = np.asarray(seed.structural.sector_weights, dtype=float)
    sector_weights = _expand_broad_vector(broad_weights, sector_count)
    broad_tau_y = _expand_broad_parameter(seed.structural.tau_Y, sector_count)
    broad_tau_k = _expand_broad_parameter(seed.structural.tau_K_sect, sector_count)
    broad_delta = _expand_broad_parameter(seed.structural.delta, sector_count)

    years = list(map(int, data["years"]))
    year_count = len(years)
    nominal_gdp_annual = np.asarray(data["nominal_gdp"], dtype=float)
    nominal_household_consumption_annual = np.asarray(data["nominal_household_consumption"], dtype=float)
    nominal_government_consumption_annual = np.asarray(data["nominal_government_consumption"], dtype=float)
    nominal_fixed_capitalformation_annual = np.asarray(data["nominal_fixed_capitalformation"], dtype=float)
    nominal_exports_annual = np.asarray(data["nominal_exports"], dtype=float)
    nominal_imports_annual = np.asarray(data["nominal_imports"], dtype=float)
    compensation_annual = np.asarray(data["compensation_employees"], dtype=float)
    wages_annual = np.asarray(data["wages"], dtype=float)
    operating_surplus_annual = np.asarray(data["operating_surplus"], dtype=float)
    unemployment_rate_annual = np.asarray(data["unemployment_rate"], dtype=float)

    firms_total = 6_100_000.0
    employees_total = 158_000_000.0
    population_total = 330_000_000.0
    firms_by_sector = np.outer(sector_weights, np.ones(year_count)) * firms_total
    employees_by_sector = np.outer(sector_weights, np.ones(year_count)) * employees_total
    unemployed = unemployment_rate_annual * employees_total
    inactive = np.full(year_count, population_total) - employees_total - unemployed - firms_total - 1.0

    nominal_output_by_sector = np.outer(sector_weights, nominal_gdp_annual * 1.55)
    compensation_by_sector = np.outer(sector_weights, compensation_annual)
    wages_by_sector = np.outer(sector_weights, wages_annual)
    capital_consumption_by_sector = nominal_output_by_sector * broad_delta[:, None]
    gross_operating_surplus_by_sector = np.outer(sector_weights, operating_surplus_annual) + capital_consumption_by_sector
    taxes_products_by_sector = nominal_output_by_sector * broad_tau_y[:, None]
    taxes_production_by_sector = nominal_output_by_sector * broad_tau_k[:, None]
    government_by_sector = np.outer(sector_weights, nominal_government_consumption_annual)
    household_by_sector = np.outer(sector_weights, nominal_household_consumption_annual)
    fixed_capitalformation_by_sector = np.outer(sector_weights, nominal_fixed_capitalformation_annual)
    exports_by_sector = np.outer(sector_weights, nominal_exports_annual)
    imports_by_sector = np.outer(sector_weights, nominal_imports_annual)
    intermediate_consumption = np.stack(
        [
            _matrix_from_totals(nominal_output_by_sector[:, idx] * 0.50, sector_weights, scale=1.0)
            for idx in range(year_count)
        ],
        axis=2,
    )

    fixed_assets_by_sector = nominal_output_by_sector * 2.50
    dwellings_by_sector = fixed_assets_by_sector * 0.10
    eu7_groups = 7
    eu7_weights = np.full(eu7_groups, 1.0 / eu7_groups)
    fixed_assets_eu7 = np.outer(eu7_weights, nominal_gdp_annual * 2.50)
    dwellings_eu7 = fixed_assets_eu7 * 0.10
    nominal_output_eu7 = np.outer(eu7_weights, nominal_gdp_annual * 1.55)

    social_contributions = compensation_annual - wages_annual
    social_benefits = nominal_gdp_annual * 0.13
    unemployment_benefits = social_benefits * 0.12
    pension_benefits = social_benefits * 0.45
    income_tax = nominal_gdp_annual * 0.12
    corporate_tax = nominal_gdp_annual * 0.015
    capital_taxes = nominal_gdp_annual * 0.010
    property_income = nominal_gdp_annual * 0.080
    mixed_income = nominal_gdp_annual * 0.060
    household_cash = nominal_household_consumption_annual.mean() * 0.25 * np.ones(len(data["quarters_num"]))
    firm_cash = np.asarray(data["nominal_gdp_quarterly"], dtype=float) * 0.10
    firm_debt = np.asarray(data["nominal_gdp_quarterly"], dtype=float) * 0.50
    government_debt = np.full(len(data["quarters_num"]), seed.initial_distributions.L_G)
    bank_equity = np.full(len(data["quarters_num"]), seed.initial_distributions.E_k)
    firm_interest_q = firm_debt * 0.010
    government_interest_q = government_debt * 0.005
    government_deficit_q = np.asarray(data["nominal_government_consumption_quarterly"], dtype=float) * 0.05

    calibration = {
        "years_num": list(data["years_num"]),
        "quarters_num": list(data["quarters_num"]),
        "firms": firms_by_sector.tolist(),
        "employees": employees_by_sector.tolist(),
        "population": (np.full(year_count, population_total)).tolist(),
        "inactive_census": inactive.tolist(),
        "unemployed_census": unemployed.tolist(),
        "wages": wages_annual.tolist(),
        "wages_by_sector": wages_by_sector.tolist(),
        "property_income": property_income.tolist(),
        "mixed_income": mixed_income.tolist(),
        "social_benefits": social_benefits.tolist(),
        "unemployment_benefits": unemployment_benefits.tolist(),
        "pension_benefits": pension_benefits.tolist(),
        "corporate_tax": corporate_tax.tolist(),
        "social_contributions": social_contributions.tolist(),
        "income_tax": income_tax.tolist(),
        "capital_taxes": capital_taxes.tolist(),
        "fixed_assets": fixed_assets_by_sector.tolist(),
        "dwellings": dwellings_by_sector.tolist(),
        "fixed_assets_eu7": fixed_assets_eu7.tolist(),
        "dwellings_eu7": dwellings_eu7.tolist(),
        "nominal_nace64_output_eu7": nominal_output_eu7.tolist(),
        "gross_capitalformation_dwellings": (nominal_fixed_capitalformation_annual * seed.mapping.I_resid_share).tolist(),
        "capital_consumption": capital_consumption_by_sector.tolist(),
        "nace64_capital_consumption": capital_consumption_by_sector.tolist(),
        "nominal_nace64_output": nominal_output_by_sector.tolist(),
        "household_cash_quarterly": household_cash.tolist(),
        "firm_cash_quarterly": firm_cash.tolist(),
        "firm_debt_quarterly": firm_debt.tolist(),
        "government_debt_quarterly": government_debt.tolist(),
        "bank_equity_quarterly": bank_equity.tolist(),
        "firm_interest": _annualise_quarterly_flow(firm_interest_q, year_count).tolist(),
        "firm_interest_quarterly": firm_interest_q.tolist(),
        "interest_government_debt": _annualise_quarterly_flow(government_interest_q, year_count).tolist(),
        "interest_government_debt_quarterly": government_interest_q.tolist(),
        "government_deficit": _annualise_quarterly_flow(government_deficit_q, year_count).tolist(),
        "government_deficit_quarterly": government_deficit_q.tolist(),
    }

    figaro = {
        "intermediate_consumption": intermediate_consumption.tolist(),
        "household_consumption": household_by_sector.tolist(),
        "fixed_capitalformation": fixed_capitalformation_by_sector.tolist(),
        "exports": exports_by_sector.tolist(),
        "imports": imports_by_sector.tolist(),
        "compensation_employees": compensation_by_sector.tolist(),
        "operating_surplus": gross_operating_surplus_by_sector.tolist(),
        "government_consumption": government_by_sector.tolist(),
        "taxes_products_household": (nominal_household_consumption_annual * 0.06).tolist(),
        "taxes_products_capitalformation": (nominal_fixed_capitalformation_annual * 0.04).tolist(),
        "taxes_products_government": (nominal_government_consumption_annual * 0.02).tolist(),
        "taxes_products": taxes_products_by_sector.tolist(),
        "taxes_production": taxes_production_by_sector.tolist(),
    }

    provenance = {
        "mode": "bootstrap",
        "reference_quarter": reference_quarter,
        "calibration": {key: {"kind": "constructed-from-source", "sources": ["legacy_observed_panel", "bootstrap_seed_2019q4"]} for key in calibration},
        "figaro": {key: {"kind": "constructed-from-source", "sources": ["legacy_observed_panel", "bootstrap_seed_2019q4"]} for key in figaro},
        "data": {key: {"kind": "direct-source" if key in {"periods", "quarters_num", "years_num"} else "constructed-from-source", "sources": ["legacy_observed_panel"]} for key in data},
        "ea": {"kind": "fallback", "sources": ["scaled_domestic_proxy"]},
    }
    return calibration, figaro, provenance


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(val) for key, val in value.items()}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.Series):
        return value.tolist()
    if isinstance(value, pd.PeriodIndex):
        return value.astype(str).tolist()
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def validate_bundle_dicts(
    calibration: dict[str, Any],
    figaro: dict[str, Any],
    data: dict[str, Any],
    ea: dict[str, Any],
) -> None:
    missing = [key for key in REQUIRED_CALIBRATION_KEYS if key not in calibration]
    if missing:
        raise ValueError(f"Missing calibration keys: {missing}")
    missing = [key for key in REQUIRED_FIGARO_KEYS if key not in figaro]
    if missing:
        raise ValueError(f"Missing figaro keys: {missing}")
    missing = [key for key in REQUIRED_TIMESERIES_KEYS if key not in data]
    if missing:
        raise ValueError(f"Missing data keys: {missing}")
    missing = [key for key in ("real_gdp_quarterly", "nominal_gdp_quarterly", "gdp_deflator_quarterly") if key not in ea]
    if missing:
        raise ValueError(f"Missing ea keys: {missing}")


def write_calibration_bundle(
    bundle_dir: str | Path,
    *,
    manifest: CalibrationArtifactManifest,
    observed_macro: pd.DataFrame,
    calibration: dict[str, Any],
    figaro: dict[str, Any],
    data: dict[str, Any],
    ea: dict[str, Any],
    provenance: dict[str, Any],
    release_manifest: dict[str, Any] | None = None,
) -> Path:
    bundle_dir = Path(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    observed_macro.to_csv(bundle_dir / manifest.observed_macro_file, index=False)
    (bundle_dir / manifest.calibration_file).write_text(json.dumps(_json_ready(calibration), indent=2))
    (bundle_dir / manifest.figaro_file).write_text(json.dumps(_json_ready(figaro), indent=2))
    (bundle_dir / manifest.data_file).write_text(json.dumps(_json_ready(data), indent=2))
    (bundle_dir / manifest.ea_file).write_text(json.dumps(_json_ready(ea), indent=2))
    (bundle_dir / manifest.provenance_file).write_text(json.dumps(_json_ready(provenance), indent=2))
    (bundle_dir / manifest.release_manifest_file).write_text(json.dumps(release_manifest or {"entries": []}, indent=2))
    (bundle_dir / "manifest.json").write_text(json.dumps(asdict(manifest), indent=2))
    return bundle_dir


def build_bootstrap_bundle_from_observed(
    raw: pd.DataFrame,
    output_dir: str | Path,
    *,
    reference_quarter: str = "2019Q4",
    sector_count: int = 62,
    source_mode: str = "bootstrap",
) -> Path:
    observed = _normalise_observed(raw)
    data = build_bootstrap_timeseries(observed)
    calibration, figaro, provenance = build_bootstrap_structural_bundle(
        data,
        reference_quarter=reference_quarter,
        sector_count=sector_count,
    )
    ea = build_bootstrap_ea(data)
    provenance["ea"] = {
        key: {"kind": "fallback", "sources": ["scaled_domestic_proxy"]}
        for key in ea
    }
    validate_bundle_dicts(calibration, figaro, data, ea)
    manifest = CalibrationArtifactManifest(
        schema_version="1.0",
        compiler_version="0.1.0",
        reference_quarter=reference_quarter,
        sector_count=sector_count,
        source_mode=source_mode,
        observed_macro_file="observed_macro.csv",
        calibration_file="calibration.json",
        figaro_file="figaro.json",
        data_file="data.json",
        ea_file="ea.json",
        provenance_file="provenance.json",
        release_manifest_file="release_manifest.json",
        max_calibration_date=f"{reference_quarter[:4]}-12-31",
        estimation_date=_quarter_end_iso(str(observed["period"].iloc[0])),
        generated_at=_utcnow_iso(),
    )
    return write_calibration_bundle(
        output_dir,
        manifest=manifest,
        observed_macro=observed,
        calibration=calibration,
        figaro=figaro,
        data=data,
        ea=ea,
        provenance=provenance,
    )
