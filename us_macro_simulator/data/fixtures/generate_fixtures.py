"""Generate synthetic Tier-A and Tier-B fixture files."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_DIR = Path(__file__).parent


def make_tier_a_aggregate() -> pd.DataFrame:
    """20-quarter synthetic fixture with known identities. 2015Q1–2019Q4."""
    rng = np.random.default_rng(42)
    periods = pd.period_range("2015Q1", "2019Q4", freq="Q")
    n = len(periods)

    gdp_base = 19_000.0
    gdp_growth = rng.normal(0.005, 0.003, n)
    # Clamp growth for stable baseline
    gdp_growth = np.clip(gdp_growth, -0.02, 0.04)
    gdp_level = gdp_base * np.cumprod(1 + gdp_growth)

    cpi_base = 250.0
    cpi_infl = rng.normal(0.005, 0.002, n)
    cpi = cpi_base * np.cumprod(1 + cpi_infl)
    core_cpi = cpi * 0.985 * np.cumprod(1 + rng.normal(0.004, 0.001, n))

    unrate = np.clip(rng.normal(3.7, 0.3, n), 2.5, 10.0)
    fedfunds = np.clip(rng.normal(2.2, 0.5, n), 0.0, 8.0)

    pce = gdp_level * 0.68 * (1 + rng.normal(0, 0.003, n))
    resid_inv = gdp_level * 0.048 * (1 + rng.normal(0, 0.015, n))
    fci = rng.normal(0.0, 0.25, n)

    df = pd.DataFrame(
        {
            "GDPC1": gdp_level,
            "GDPC1_GROWTH": gdp_growth * 400,
            "CPIAUCSL": cpi,
            "CPILFESL": core_cpi,
            "UNRATE": unrate,
            "FEDFUNDS": fedfunds,
            "PCECC96": pce,
            "PRFI": resid_inv,
            "FCI": fci,
        },
        index=periods,
    )
    return df


def make_tier_b_aggregate() -> pd.DataFrame:
    """40-quarter synthetic fixture. 2010Q1–2019Q4 for backtest use."""
    rng = np.random.default_rng(123)
    periods = pd.period_range("2010Q1", "2019Q4", freq="Q")
    n = len(periods)

    gdp_base = 15_500.0
    gdp_growth = np.clip(rng.normal(0.006, 0.004, n), -0.03, 0.05)
    gdp_level = gdp_base * np.cumprod(1 + gdp_growth)

    cpi_base = 218.0
    cpi_infl = rng.normal(0.004, 0.002, n)
    cpi = cpi_base * np.cumprod(1 + cpi_infl)
    core_cpi = cpi * 0.99 * np.cumprod(1 + rng.normal(0.003, 0.001, n))

    unrate = np.clip(rng.normal(6.0, 1.5, n), 2.5, 12.0)
    fedfunds = np.clip(rng.normal(1.0, 1.0, n), 0.0, 6.0)

    pce = gdp_level * 0.68 * (1 + rng.normal(0, 0.003, n))
    resid_inv = gdp_level * 0.046 * (1 + rng.normal(0, 0.02, n))
    fci = rng.normal(0.0, 0.4, n)

    df = pd.DataFrame(
        {
            "GDPC1": gdp_level,
            "GDPC1_GROWTH": gdp_growth * 400,
            "CPIAUCSL": cpi,
            "CPILFESL": core_cpi,
            "UNRATE": unrate,
            "FEDFUNDS": fedfunds,
            "PCECC96": pce,
            "PRFI": resid_inv,
            "FCI": fci,
        },
        index=periods,
    )
    return df


def make_tier_a_crosssection() -> pd.DataFrame:
    """3 household bins × 3 sectors, 20 quarters."""
    rng = np.random.default_rng(99)
    periods = pd.period_range("2015Q1", "2019Q4", freq="Q")
    n = len(periods)

    rows = []
    for p in periods:
        row = {"period": str(p)}
        # 3 household income bins: low, middle, high
        for bin_name, share in [("low", 0.15), ("middle", 0.55), ("high", 0.30)]:
            gdp = 19000 * (1 + rng.normal(0.005, 0.002))
            row[f"consumption_{bin_name}"] = gdp * share * (1 + rng.normal(0, 0.005))
            row[f"income_{bin_name}"] = gdp * share * (1 + rng.normal(0.01, 0.003))
        # 3 sectors
        for sec, share in [("mfg", 0.12), ("services", 0.55), ("construction", 0.05)]:
            row[f"gva_{sec}"] = 19000 * share * (1 + rng.normal(0.004, 0.003))
        rows.append(row)

    df = pd.DataFrame(rows).set_index("period")
    df.index = pd.PeriodIndex(df.index, freq="Q")
    return df


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tier_a = make_tier_a_aggregate()
    tier_a.to_parquet(OUTPUT_DIR / "tier_a_aggregate.parquet")
    print(f"Saved tier_a_aggregate.parquet ({len(tier_a)} rows)")

    tier_b = make_tier_b_aggregate()
    tier_b.to_parquet(OUTPUT_DIR / "tier_b_aggregate.parquet")
    print(f"Saved tier_b_aggregate.parquet ({len(tier_b)} rows)")

    tier_a_cs = make_tier_a_crosssection()
    tier_a_cs.to_parquet(OUTPUT_DIR / "tier_a_crosssection.parquet")
    print(f"Saved tier_a_crosssection.parquet ({len(tier_a_cs)} rows)")
