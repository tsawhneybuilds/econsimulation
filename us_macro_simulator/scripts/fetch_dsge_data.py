"""
Fetch and cache professional forecast benchmark data.

Why not NY Fed DSGE directly
------------------------------
The NY Fed DSGE model publishes forecasts quarterly on Liberty Street Economics,
but historical vintage data is NOT available as a bulk download.  The interactive
tool at newyorkfed.org/research/policy/dsge only serves the two most recent vintages.
The blog posts embed forecast charts in JavaScript; there is no API endpoint for
historical data.

What we use instead (SPF — the standard academic benchmark)
------------------------------------------------------------
The Philadelphia Fed Survey of Professional Forecasters (SPF) is:
  - The oldest quarterly US forecast survey (since 1968)
  - Published every quarter with per-horizon forecasts at h=1,2,3,4
  - Used as the benchmark by the NY Fed DSGE team themselves in their papers
  - Freely downloadable in machine-readable Excel format

This script downloads the SPF mean forecast files and converts them to the
tidy parquet format expected by NYFedDSGEBenchmark.

Data sources
-------------
Mean growth forecasts (RGDP):
  https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/
      survey-of-professional-forecasters/historical-data/meanGrowth.xlsx

Mean level forecasts (UNEMP, TBILL, CORECPI):
  https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/
      survey-of-professional-forecasters/historical-data/meanLevel.xlsx

Variable mapping (SPF → internal)
----------------------------------
SPF name   Sheet       Columns used     Internal name
--------   -----       ------------     -------------
RGDP       meanGrowth  drgdp3-6         gdp_growth       (QoQ annualized %)
CORECPI    meanLevel   CORECPI3-6       cpi_inflation    (annualized %)
UNEMP      meanLevel   UNEMP3-6         unemployment_rate (%)
TBILL      meanLevel   TBILL3-6         fed_funds_rate   (%)

Column suffix key (SPF convention):
  suffix 2 = nowcast (current quarter)
  suffix 3 = h=1 (1 quarter ahead)
  suffix 4 = h=2
  suffix 5 = h=3
  suffix 6 = h=4

Usage
-----
    cd us_macro_simulator
    python scripts/fetch_dsge_data.py

    # Custom output path:
    python scripts/fetch_dsge_data.py --output path/to/output.parquet

Output format
-------------
Parquet with columns: vintage, period, horizon, variable, mean, p10, p90
"""
from __future__ import annotations

import argparse
import logging
import sys
import urllib.request
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO_ROOT / "us_macro_simulator"))

_DEFAULT_OUTPUT = _REPO_ROOT / "us_macro_simulator" / "data" / "external" / "nyfed_dsge_forecasts.parquet"

_SPF_GROWTH_URL = (
    "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
    "survey-of-professional-forecasters/historical-data/meanGrowth.xlsx"
)
_SPF_LEVEL_URL = (
    "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
    "survey-of-professional-forecasters/historical-data/meanLevel.xlsx"
)

_BACKTEST_START = pd.Period("2017Q1", freq="Q")
_BACKTEST_END   = pd.Period("2019Q4", freq="Q")

# horizon suffix index: h → column suffix
_H_TO_SUFFIX = {1: "3", 2: "4", 3: "5", 4: "6"}


def fetch_spf(output_path: Optional[Path] = None) -> pd.DataFrame:
    output_path = Path(output_path) if output_path else _DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)

    growth_xl, level_xl = _download_spf()
    if growth_xl is None or level_xl is None:
        log.error("Failed to download SPF data — aborting.")
        return pd.DataFrame()

    rows = []
    rows += _extract_rgdp_growth(growth_xl)
    rows += _extract_level_var(level_xl, "CORECPI", "cpi_inflation")
    rows += _extract_level_var(level_xl, "UNEMP",   "unemployment_rate")
    rows += _extract_level_var(level_xl, "TBILL",   "fed_funds_rate")

    if not rows:
        log.error("No rows extracted from SPF data.")
        return pd.DataFrame()

    tidy = pd.DataFrame(rows)
    tidy = tidy.sort_values(["vintage", "variable", "horizon"]).reset_index(drop=True)
    _validate_coverage(tidy)

    tidy.to_parquet(output_path, index=False)
    log.info("Wrote %d rows to %s", len(tidy), output_path)

    print("\n=== Philadelphia Fed SPF Forecast Data ===")
    print(f"Vintages: {sorted(tidy['vintage'].unique())[:3]} ... {sorted(tidy['vintage'].unique())[-3:]}")
    print(f"Variables: {sorted(tidy['variable'].unique())}")
    print(f"Horizons:  {sorted(tidy['horizon'].unique())}")
    print(f"Total rows: {len(tidy)}")
    print(f"Output:     {output_path}")
    print("")

    return tidy


def _download_spf():
    """Download both SPF Excel files. Returns (growth_xl, level_xl) or (None, None)."""
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        log.error("openpyxl required: pip install openpyxl")
        return None, None

    cache_dir = _DEFAULT_OUTPUT.parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    growth_path = cache_dir / "spf_mean_growth.xlsx"
    level_path  = cache_dir / "spf_mean_level.xlsx"

    for url, path in [(_SPF_GROWTH_URL, growth_path), (_SPF_LEVEL_URL, level_path)]:
        if path.exists():
            log.info("Using cached %s", path.name)
        else:
            log.info("Downloading %s ...", url)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    path.write_bytes(resp.read())
                log.info("Saved %s (%.0f KB)", path.name, path.stat().st_size / 1024)
            except Exception as exc:
                log.error("Download failed for %s: %s", url, exc)
                return None, None

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            growth_xl = pd.ExcelFile(growth_path)
            level_xl  = pd.ExcelFile(level_path)
        return growth_xl, level_xl
    except Exception as exc:
        log.error("Failed to open SPF Excel files: %s", exc)
        return None, None


def _extract_rgdp_growth(xl: pd.ExcelFile) -> list[dict]:
    """Extract RGDP QoQ annualized growth → gdp_growth."""
    rows = []
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df = pd.read_excel(xl, "RGDP")
    except Exception as exc:
        log.warning("Could not read RGDP sheet: %s", exc)
        return rows

    for _, row in df.iterrows():
        vintage = _make_vintage(row)
        if vintage is None:
            continue
        for h, sfx in _H_TO_SUFFIX.items():
            col = f"drgdp{sfx}"
            val = row.get(col, np.nan)
            if pd.isna(val):
                continue
            period = str(pd.Period(vintage, freq="Q") + h)
            rows.append({
                "vintage":  vintage,
                "period":   period,
                "horizon":  h,
                "variable": "gdp_growth",
                "mean":     float(val),
                "p10":      np.nan,
                "p90":      np.nan,
            })
    return rows


def _extract_level_var(xl: pd.ExcelFile, sheet: str, var_name: str) -> list[dict]:
    """Extract a level-forecast variable (CORECPI, UNEMP, TBILL) per horizon."""
    rows = []
    prefix = sheet  # column prefix = sheet name

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df = pd.read_excel(xl, sheet)
    except Exception as exc:
        log.warning("Could not read %s sheet: %s", sheet, exc)
        return rows

    for _, row in df.iterrows():
        vintage = _make_vintage(row)
        if vintage is None:
            continue
        for h, sfx in _H_TO_SUFFIX.items():
            col = f"{prefix}{sfx}"
            val = row.get(col, np.nan)
            if pd.isna(val):
                continue
            period = str(pd.Period(vintage, freq="Q") + h)
            rows.append({
                "vintage":  vintage,
                "period":   period,
                "horizon":  h,
                "variable": var_name,
                "mean":     float(val),
                "p10":      np.nan,
                "p90":      np.nan,
            })
    return rows


def _make_vintage(row) -> Optional[str]:
    """Convert YEAR + QUARTER columns to vintage string like '2017Q1'."""
    try:
        year = int(row["YEAR"])
        qtr  = int(row["QUARTER"])
        if not (1 <= qtr <= 4):
            return None
        return f"{year}Q{qtr}"
    except Exception:
        return None


def _validate_coverage(tidy: pd.DataFrame) -> None:
    vintages = set(tidy["vintage"].unique())
    required = [str(p) for p in pd.period_range(_BACKTEST_START, _BACKTEST_END, freq="Q")]
    missing  = [v for v in required if v not in vintages]
    if missing:
        log.warning("Missing %d vintages from backtest window: %s", len(missing), missing)
    else:
        log.info("Coverage OK: all %d vintages in 2017Q1–2019Q4 present.", len(required))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help=f"Output parquet path (default: {_DEFAULT_OUTPUT})")
    args = parser.parse_args()
    fetch_spf(output_path=args.output)


if __name__ == "__main__":
    main()
