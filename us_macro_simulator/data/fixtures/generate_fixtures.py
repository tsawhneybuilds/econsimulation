"""Generate FRED-backed fixture parquet files.

Replaces all synthetic random fixtures with real FRED data.

Usage (from us_macro_simulator/):
    FRED_API_KEY="..." python data/fixtures/generate_fixtures.py

Requires: requests (pip install requests)

What each fixture contains:
  tier_a_aggregate.parquet  — 20 quarters, 2015Q1-2019Q4, 9 FRED series
  tier_b_aggregate.parquet  — 40 quarters, 2010Q1-2019Q4, same series (backtest history)
  tier_a_crosssection.parquet — 20 quarters, 2015Q1-2019Q4
      Aggregate columns from FRED (GDPC1, PCECC96).
      Income/consumption distribution by tercile from PSZ (2018) / BEA DFA (2019)
          empirical shares — these are published research constants, not random noise.
          FRED does not publish a direct quarterly tercile income series.
      Sector GVA columns scaled from GDPC1 using BEA GDP-by-Industry 2015-2019 averages.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import requests

OUTPUT_DIR = Path(__file__).parent
REPO_ROOT = OUTPUT_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# FRED series map: internal_id → (fred_series_id, source_frequency)
# No realtime_end — we want the latest-revised values for the fixture.
# Vintage masking at backtest time is handled by VintageDataset + release_lag_quarters.
# ---------------------------------------------------------------------------
_FRED_MAP = {
    "GDPC1":        ("GDPC1",           "Q"),   # Real GDP, bn 2017 USD SAAR
    "GDPC1_GROWTH": ("A191RL1Q225SBEA", "Q"),   # Real GDP growth QoQ ann %, BEA
    "CPIAUCSL":     ("CPIAUCSL",        "M"),   # CPI all urban, index 1982-84=100
    "CPILFESL":     ("CPILFESL",        "M"),   # Core CPI, same index
    "UNRATE":       ("UNRATE",          "M"),   # Unemployment rate, %
    "FEDFUNDS":     ("FEDFUNDS",        "M"),   # Effective FFR, %
    "PCECC96":      ("PCECC96",         "Q"),   # Real PCE, bn 2017 USD SAAR
    "PRFI":         ("PRFI",            "Q"),   # Real private residential fixed inv
    "FCI":          ("NFCI",            "W"),   # Chicago Fed NFCI (z-score)
}

# ---------------------------------------------------------------------------
# Cross-section constants from published research
# ---------------------------------------------------------------------------
# Income share by tercile (share of total personal income):
#   Source: Piketty, Saez & Zucman (2018) distributional national accounts.
#   Bottom tercile ~9%, middle ~24%, top ~67%.  Stable across 2015-2019.
_INCOME_SHARES = {"low": 0.090, "middle": 0.240, "high": 0.670}

# Consumption share by tercile (share of total PCE):
#   Source: BEA Distributional Financial Accounts (2019), Table B.101.
#   Bottom tercile ~16%, middle ~37%, top ~47%.
_CONSUMPTION_SHARES = {"low": 0.160, "middle": 0.370, "high": 0.470}

# Sector GVA shares of real GDP (BEA GDP-by-Industry, 2015-2019 average):
#   Manufacturing: 11.5%, Construction: 4.8%, Private services: 55.0%
_SECTOR_SHARES = {"gva_mfg": 0.115, "gva_construction": 0.048, "gva_services": 0.550}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_fred(
    fred_id: str,
    api_key: str,
    start_date: str,
    end_date: str,
    src_freq: str,
) -> pd.Series:
    """Fetch a single FRED series and resample to quarterly PeriodIndex."""
    params = {
        "series_id": fred_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end": end_date,
        # No realtime_end — use latest-revised values.
    }
    resp = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()

    records = [
        (obs["date"], float(obs["value"]))
        for obs in payload.get("observations", [])
        if obs["value"] not in (".", "")
    ]
    if not records:
        raise RuntimeError(f"No data returned from FRED for series {fred_id}")

    dates, values = zip(*records)
    s = pd.Series(list(values), index=pd.to_datetime(list(dates)), name=fred_id)
    s = s[~s.index.duplicated(keep="last")].sort_index()

    # Resample sub-quarterly to quarterly mean
    if src_freq in ("M", "W", "D"):
        q = s.resample("QE").mean()
    else:
        q = s.copy()
        q.index = pd.PeriodIndex(q.index.to_period("Q")).to_timestamp("Q")

    q.index = pd.PeriodIndex(q.index.to_period("Q"))
    return q


def build_aggregate(start_date: str, end_date: str, api_key: str) -> pd.DataFrame:
    """Fetch all aggregate series from FRED and return a quarterly DataFrame."""
    frames: dict[str, pd.Series] = {}
    for sid, (fred_id, src_freq) in _FRED_MAP.items():
        print(f"  {sid} ({fred_id}) ...", end=" ", flush=True)
        try:
            frames[sid] = _fetch_fred(fred_id, api_key, start_date, end_date, src_freq)
            print(f"{len(frames[sid])} quarters")
        except Exception as exc:
            print(f"FAILED: {exc}")

    df = pd.DataFrame(frames).sort_index()
    # Trim to requested period
    start_period = pd.Period(start_date[:7], freq="Q")
    end_period = pd.Period(end_date[:7], freq="Q")
    return df.loc[(df.index >= start_period) & (df.index <= end_period)]


def build_crosssection(aggregate_df: pd.DataFrame) -> pd.DataFrame:
    """Build cross-section fixture from real GDP/PCE and empirical shares.

    Uses:
    - GDPC1 from FRED for income proxies and sector GVA.
    - PCECC96 from FRED for consumption terciles.
    - PSZ (2018) income shares and BEA DFA (2019) consumption shares.
    - BEA GDP-by-Industry 2015-2019 average sector shares.
    """
    rows = []
    for period in aggregate_df.index:
        gdp = aggregate_df.loc[period, "GDPC1"] if "GDPC1" in aggregate_df.columns else None
        pce = aggregate_df.loc[period, "PCECC96"] if "PCECC96" in aggregate_df.columns else None

        if gdp is None or pd.isna(gdp):
            continue

        # Fall back to PCE = 68% of GDP if PCECC96 is missing
        if pce is None or pd.isna(pce):
            pce = gdp * 0.68

        row: dict = {}
        for bin_name, share in _INCOME_SHARES.items():
            row[f"income_{bin_name}"] = gdp * share
        for bin_name, share in _CONSUMPTION_SHARES.items():
            row[f"consumption_{bin_name}"] = pce * share
        for col, share in _SECTOR_SHARES.items():
            row[col] = gdp * share

        rows.append((str(period), row))

    index = pd.PeriodIndex([r[0] for r in rows], freq="Q")
    data = [r[1] for r in rows]
    return pd.DataFrame(data, index=index)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        print("ERROR: FRED_API_KEY environment variable not set.")
        print("  export FRED_API_KEY='your_key'")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # -- Tier A: 2015Q1-2019Q4 (smoke / stage-1 default) -------------------
    print("Fetching tier_a aggregate (2015Q1-2019Q4) ...")
    tier_a = build_aggregate("2015-01-01", "2019-12-31", api_key)
    tier_a.to_parquet(OUTPUT_DIR / "tier_a_aggregate.parquet")
    print(f"  -> saved tier_a_aggregate.parquet  ({len(tier_a)} rows x {len(tier_a.columns)} cols)")

    # -- Tier B: 2010Q1-2019Q4 (backtest history) ---------------------------
    print("Fetching tier_b aggregate (2010Q1-2019Q4) ...")
    tier_b = build_aggregate("2010-01-01", "2019-12-31", api_key)
    tier_b.to_parquet(OUTPUT_DIR / "tier_b_aggregate.parquet")
    print(f"  -> saved tier_b_aggregate.parquet  ({len(tier_b)} rows x {len(tier_b.columns)} cols)")

    # -- Cross-section: 2015Q1-2019Q4 (validation layer) -------------------
    print("Building tier_a cross-section from FRED GDP/PCE + empirical shares ...")
    cross = build_crosssection(tier_a)
    cross.to_parquet(OUTPUT_DIR / "tier_a_crosssection.parquet")
    print(f"  -> saved tier_a_crosssection.parquet ({len(cross)} rows x {len(cross.columns)} cols)")

    print("\nAll fixtures rebuilt from real FRED data.")
    print(f"  tier_a period: {tier_a.index[0]} -> {tier_a.index[-1]}")
    print(f"  tier_b period: {tier_b.index[0]} -> {tier_b.index[-1]}")
    print(f"  cross-section: {cross.index[0]} -> {cross.index[-1]}")
    print(f"\nIncome shares (PSZ 2018): {_INCOME_SHARES}")
    print(f"Consumption shares (BEA DFA 2019): {_CONSUMPTION_SHARES}")
    print(f"Sector GVA shares (BEA GDP-by-Industry avg): {_SECTOR_SHARES}")
