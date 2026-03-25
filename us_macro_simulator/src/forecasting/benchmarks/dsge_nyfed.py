"""NY Fed DSGE benchmark: loads published historical forecast vintages.

The Federal Reserve Bank of New York publishes historical forecast vintages
from their DSGE model quarterly. This benchmark downloads (and caches) that
data and serves the pre-computed DSGE forecast for the relevant vintage,
making it a genuine DSGE comparison without requiring model estimation.

Data source
-----------
NY Fed DSGE historical forecasts:
  https://www.newyorkfed.org/research/policy/dsge/estimating

The Excel file contains forecasts for:
  - Real GDP growth (annualised QoQ, %)
  - Core PCE inflation (annualised, %)
  - Unemployment rate (%)
  - Federal funds rate (%)

Coverage: ~2010Q3 onward, updated quarterly.

Setup
-----
Run the fetch script once to download and cache the data:
    python us_macro_simulator/scripts/fetch_dsge_data.py

Or provide the path to a manually downloaded Excel:
    NYFedDSGEBenchmark(data_path="path/to/nyfed_dsge_forecasts.xlsx")

Variable mapping
----------------
NY Fed name       →  internal name
-----------           -------------
GDP Growth        →  gdp_growth
Core PCE          →  cpi_inflation
Unemployment      →  unemployment_rate
Fed Funds Rate    →  fed_funds_rate
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# Default cache location (written by fetch_dsge_data.py)
_DEFAULT_CACHE = Path(__file__).parents[3] / "data" / "external" / "nyfed_dsge_forecasts.parquet"

# NY Fed variable name → internal variable name
# The Excel may use slightly different column labels across vintages;
# we try each alias in order.
_VAR_MAP = {
    "gdp_growth": [
        "gdp growth", "real gdp growth", "gdpg", "output growth",
        "real gdp", "gdp",
    ],
    "cpi_inflation": [
        "core pce", "core pce inflation", "pce inflation", "inflation",
        "pi", "pce", "cpi",
    ],
    "unemployment_rate": [
        "unemployment", "unemployment rate", "u", "unrate",
    ],
    "fed_funds_rate": [
        "federal funds rate", "fed funds", "ffr", "r", "interest rate",
        "policy rate",
    ],
}


class NYFedDSGEBenchmark:
    """Serve NY Fed DSGE published forecast vintages as a benchmark.

    Parameters
    ----------
    data_path:
        Path to the cached parquet file produced by ``fetch_dsge_data.py``.
        Defaults to ``data/external/nyfed_dsge_forecasts.parquet``.
    fallback:
        Benchmark instance to use when no DSGE forecast is found for the
        inferred vintage.  Defaults to None (returns zeros with a warning).
    """

    name = "dsge_nyfed"

    def __init__(
        self,
        data_path: Optional[Path | str] = None,
        fallback=None,
    ) -> None:
        self._data_path = Path(data_path) if data_path else _DEFAULT_CACHE
        self._fallback = fallback
        self._cache: Optional[pd.DataFrame] = None  # loaded lazily

    # ------------------------------------------------------------------
    # Public interface — matches SemiStructuralBenchmark.forecast()
    # ------------------------------------------------------------------

    def forecast(
        self,
        history: pd.DataFrame,
        horizon: int,
        variables: Iterable[str] | None = None,
    ) -> pd.DataFrame:
        """Return the DSGE forecast for the vintage inferred from *history*.

        Parameters
        ----------
        history:
            DataFrame with PeriodIndex (freq="Q") and variable columns.
            The last index period is used to identify the forecast vintage.
        horizon:
            Number of quarters ahead to return.
        variables:
            Subset of column names to return.  Defaults to all DSGE variables.

        Returns
        -------
        pd.DataFrame of shape (horizon, n_variables).
        """
        variables = list(variables or history.columns)
        vintage = self._infer_vintage(history)

        df = self._load_data()
        if df is None or df.empty:
            log.warning("dsge_nyfed: no data available — returning zeros")
            return self._zeros(horizon, variables)

        # Find the closest vintage in the DSGE data
        vintage_forecast = self._lookup_vintage(df, vintage, horizon, variables)
        if vintage_forecast is None:
            if self._fallback is not None:
                log.warning(
                    "dsge_nyfed: vintage %s not found — using fallback benchmark", vintage
                )
                return self._fallback.forecast(history, horizon=horizon, variables=variables)
            log.warning(
                "dsge_nyfed: vintage %s not found and no fallback — returning zeros", vintage
            )
            return self._zeros(horizon, variables)

        return vintage_forecast

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _infer_vintage(self, history: pd.DataFrame) -> str:
        """Return the vintage label (e.g. '2017Q4') from the last history period."""
        if isinstance(history.index, pd.PeriodIndex) and len(history.index) > 0:
            return str(history.index[-1])
        if isinstance(history.index, pd.DatetimeIndex) and len(history.index) > 0:
            return str(pd.Period(history.index[-1], freq="Q"))
        return "unknown"

    def _load_data(self) -> Optional[pd.DataFrame]:
        """Load the cached DSGE forecast parquet, or return None."""
        if self._cache is not None:
            return self._cache

        if not self._data_path.exists():
            log.warning(
                "dsge_nyfed: cache file not found at %s\n"
                "Run: python us_macro_simulator/scripts/fetch_dsge_data.py",
                self._data_path,
            )
            return None

        try:
            df = pd.read_parquet(self._data_path)
            self._cache = df
            log.info(
                "dsge_nyfed: loaded %d forecast rows from %s",
                len(df),
                self._data_path,
            )
            return df
        except Exception as exc:  # noqa: BLE001
            log.warning("dsge_nyfed: failed to load cache: %s", exc)
            return None

    def _lookup_vintage(
        self,
        df: pd.DataFrame,
        vintage: str,
        horizon: int,
        variables: list[str],
    ) -> Optional[pd.DataFrame]:
        """Find the DSGE forecast for *vintage* and return a (horizon, variables) DataFrame."""
        # Expected columns: vintage, period, variable, mean, [p10, p90]
        required_cols = {"vintage", "period", "variable", "mean"}
        if not required_cols.issubset(df.columns):
            log.warning(
                "dsge_nyfed: unexpected parquet schema — expected %s, got %s",
                required_cols,
                set(df.columns),
            )
            return None

        # Exact vintage match first, then closest prior vintage
        available_vintages = sorted(df["vintage"].unique())
        matched_vintage = self._match_vintage(vintage, available_vintages)
        if matched_vintage is None:
            return None

        subset = df[df["vintage"] == matched_vintage].copy()
        if subset.empty:
            return None

        # Build (horizon x variable) DataFrame
        result_rows = []
        for h in range(1, horizon + 1):
            row = {}
            for var in variables:
                dsge_var = self._map_variable(var, subset["variable"].unique())
                if dsge_var is None:
                    row[var] = np.nan
                    continue
                h_rows = subset[
                    (subset["variable"] == dsge_var) & (subset["horizon"] == h)
                ] if "horizon" in subset.columns else pd.DataFrame()

                if h_rows.empty:
                    # Try period-based lookup: periods are offset from vintage
                    try:
                        vintage_period = pd.Period(matched_vintage, freq="Q")
                        target_period = str(vintage_period + h)
                        p_rows = subset[
                            (subset["variable"] == dsge_var) &
                            (subset["period"] == target_period)
                        ]
                        row[var] = float(p_rows["mean"].iloc[0]) if not p_rows.empty else np.nan
                    except Exception:  # noqa: BLE001
                        row[var] = np.nan
                else:
                    row[var] = float(h_rows["mean"].iloc[0])
            result_rows.append(row)

        return pd.DataFrame(result_rows, columns=variables)

    @staticmethod
    def _match_vintage(vintage: str, available: list[str]) -> Optional[str]:
        """Return the best-matching vintage — exact first, then latest prior."""
        if vintage in available:
            return vintage
        # Find latest vintage that is <= the requested vintage
        try:
            target = pd.Period(vintage, freq="Q")
            prior = [v for v in available if pd.Period(v, freq="Q") <= target]
            if prior:
                return max(prior, key=lambda v: pd.Period(v, freq="Q"))
        except Exception:  # noqa: BLE001
            pass
        return None

    @staticmethod
    def _map_variable(internal: str, dsge_vars: np.ndarray) -> Optional[str]:
        """Map an internal variable name to the DSGE dataset variable name."""
        # Try direct match first
        if internal in dsge_vars:
            return internal

        # Try alias matching
        aliases = _VAR_MAP.get(internal, [])
        for alias in aliases:
            for dv in dsge_vars:
                if alias.lower() == str(dv).lower():
                    return dv

        # Partial match fallback
        for alias in aliases:
            for dv in dsge_vars:
                if alias.lower() in str(dv).lower() or str(dv).lower() in alias.lower():
                    return dv

        return None

    @staticmethod
    def _zeros(horizon: int, variables: list[str]) -> pd.DataFrame:
        return pd.DataFrame(
            np.zeros((horizon, len(variables))),
            columns=variables,
        )
