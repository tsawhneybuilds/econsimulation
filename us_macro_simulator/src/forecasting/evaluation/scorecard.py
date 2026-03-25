"""Scorecard: aggregate forecast metrics across variables and horizons."""
from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.forecasting.evaluation.metrics import (
    compute_all_metrics,
    coverage,
    crps_gaussian,
    directional_accuracy,
    mae,
    relative_rmse,
    rmse,
)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class VariableScore:
    """Per-variable summary of forecast quality."""

    variable: str
    rmse: float
    mae: float
    directional_accuracy: float
    relative_rmse: Optional[float] = None
    coverage_50: Optional[float] = None
    coverage_90: Optional[float] = None
    crps: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "variable": self.variable,
            "rmse": self.rmse,
            "mae": self.mae,
            "directional_accuracy": self.directional_accuracy,
        }
        if self.relative_rmse is not None:
            d["relative_rmse"] = self.relative_rmse
        if self.coverage_50 is not None:
            d["coverage_50"] = self.coverage_50
        if self.coverage_90 is not None:
            d["coverage_90"] = self.coverage_90
        if self.crps is not None:
            d["crps"] = self.crps
        return d


@dataclass
class ForecastScorecard:
    """Aggregated scorecard across all forecast variables for a single
    origin / horizon combination."""

    origin: str
    horizon: int
    scores: List[VariableScore]
    overall_rmse: float
    overall_mae: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    # ---- serialisation helpers -------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation suitable for JSON / YAML."""
        return {
            "origin": self.origin,
            "horizon": self.horizon,
            "overall_rmse": self.overall_rmse,
            "overall_mae": self.overall_mae,
            "timestamp": self.timestamp,
            "scores": [s.to_dict() for s in self.scores],
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Return a tidy ``DataFrame`` with one row per variable."""
        rows = [s.to_dict() for s in self.scores]
        df = pd.DataFrame(rows)
        df.insert(0, "origin", self.origin)
        df.insert(1, "horizon", self.horizon)
        return df

    # ---- quality-gate check ----------------------------------------------

    def passes_gates(
        self,
        gates: Dict[str, float],
    ) -> Tuple[bool, List[str]]:
        """Check the scorecard against quality-gate thresholds.

        *gates* mirrors the ``forecast_gates`` section of
        ``configs/validation/gates.yaml``.  Recognised keys:

        * ``max_rmse_<variable>`` -- upper bound on per-variable RMSE
        * ``min_coverage_50pct``  -- minimum 50 % coverage rate
        * ``min_coverage_90pct``  -- minimum 90 % coverage rate

        Parameters
        ----------
        gates : Dict[str, float]
            Threshold name -> threshold value.

        Returns
        -------
        Tuple[bool, List[str]]
            ``(all_passed, list_of_failure_messages)``.
        """
        failures: List[str] = []

        score_by_var: Dict[str, VariableScore] = {
            s.variable: s for s in self.scores
        }

        for key, threshold in gates.items():
            # --- max_rmse_<variable> ---
            if key.startswith("max_rmse_"):
                var_suffix = key[len("max_rmse_"):]
                # Try to match the suffix against known variable names.
                matched = _match_variable(var_suffix, score_by_var)
                if matched is not None:
                    score = score_by_var[matched]
                    if not np.isnan(score.rmse) and score.rmse > threshold:
                        failures.append(
                            f"RMSE for {matched} = {score.rmse:.4f} "
                            f"exceeds max {threshold}"
                        )

            # --- min_coverage_50pct ---
            elif key == "min_coverage_50pct":
                for score in self.scores:
                    if score.coverage_50 is not None and not np.isnan(score.coverage_50):
                        if score.coverage_50 < threshold:
                            failures.append(
                                f"50% coverage for {score.variable} = "
                                f"{score.coverage_50:.4f} below min {threshold}"
                            )

            # --- min_coverage_90pct ---
            elif key == "min_coverage_90pct":
                for score in self.scores:
                    if score.coverage_90 is not None and not np.isnan(score.coverage_90):
                        if score.coverage_90 < threshold:
                            failures.append(
                                f"90% coverage for {score.variable} = "
                                f"{score.coverage_90:.4f} below min {threshold}"
                            )

        return (len(failures) == 0, failures)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_scorecard(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    origin: str,
    horizon: int,
    benchmark: Optional[pd.DataFrame] = None,
    lower_50: Optional[pd.DataFrame] = None,
    upper_50: Optional[pd.DataFrame] = None,
    lower_90: Optional[pd.DataFrame] = None,
    upper_90: Optional[pd.DataFrame] = None,
    forecast_std: Optional[pd.DataFrame] = None,
) -> ForecastScorecard:
    """Build a :class:`ForecastScorecard` from aligned DataFrames.

    Parameters
    ----------
    forecasts : pd.DataFrame
        Point forecasts.  Index is a ``PeriodIndex`` (quarters); columns
        are variable names.
    actuals : pd.DataFrame
        Realised values with the same structure.
    origin : str
        Forecast origin label (e.g. ``"2024Q4"``).
    horizon : int
        Forecast horizon in quarters.
    benchmark : pd.DataFrame, optional
        Benchmark forecasts for relative RMSE.
    lower_50, upper_50 : pd.DataFrame, optional
        Bounds of the 50 % prediction interval.
    lower_90, upper_90 : pd.DataFrame, optional
        Bounds of the 90 % prediction interval.
    forecast_std : pd.DataFrame, optional
        Per-variable forecast standard deviations for CRPS.

    Returns
    -------
    ForecastScorecard
    """
    # Align on common columns and index.
    common_cols = sorted(set(forecasts.columns) & set(actuals.columns))
    common_idx = forecasts.index.intersection(actuals.index)

    if len(common_cols) == 0 or len(common_idx) == 0:
        return ForecastScorecard(
            origin=origin,
            horizon=horizon,
            scores=[],
            overall_rmse=float("nan"),
            overall_mae=float("nan"),
        )

    fc = forecasts.loc[common_idx, common_cols]
    ac = actuals.loc[common_idx, common_cols]

    scores: List[VariableScore] = []
    all_rmse: List[float] = []
    all_mae: List[float] = []

    for col in common_cols:
        f_arr = fc[col].to_numpy(dtype=float)
        a_arr = ac[col].to_numpy(dtype=float)

        var_rmse = rmse(f_arr, a_arr)
        var_mae = mae(f_arr, a_arr)
        var_da = directional_accuracy(f_arr, a_arr)

        var_rel_rmse: Optional[float] = None
        if benchmark is not None and col in benchmark.columns:
            b_arr = benchmark.loc[common_idx, col].to_numpy(dtype=float)
            var_rel_rmse = relative_rmse(f_arr, a_arr, b_arr)

        var_cov50: Optional[float] = None
        if lower_50 is not None and upper_50 is not None:
            if col in lower_50.columns and col in upper_50.columns:
                lo50 = lower_50.loc[common_idx, col].to_numpy(dtype=float)
                hi50 = upper_50.loc[common_idx, col].to_numpy(dtype=float)
                var_cov50 = coverage(lo50, hi50, a_arr)

        var_cov90: Optional[float] = None
        if lower_90 is not None and upper_90 is not None:
            if col in lower_90.columns and col in upper_90.columns:
                lo90 = lower_90.loc[common_idx, col].to_numpy(dtype=float)
                hi90 = upper_90.loc[common_idx, col].to_numpy(dtype=float)
                var_cov90 = coverage(lo90, hi90, a_arr)

        var_crps: Optional[float] = None
        if forecast_std is not None and col in forecast_std.columns:
            std_arr = forecast_std.loc[common_idx, col].to_numpy(dtype=float)
            var_crps = crps_gaussian(f_arr, std_arr, a_arr)

        scores.append(
            VariableScore(
                variable=col,
                rmse=var_rmse,
                mae=var_mae,
                directional_accuracy=var_da,
                relative_rmse=var_rel_rmse,
                coverage_50=var_cov50,
                coverage_90=var_cov90,
                crps=var_crps,
            )
        )

        if not np.isnan(var_rmse):
            all_rmse.append(var_rmse)
        if not np.isnan(var_mae):
            all_mae.append(var_mae)

    overall_rmse = float(np.mean(all_rmse)) if all_rmse else float("nan")
    overall_mae = float(np.mean(all_mae)) if all_mae else float("nan")

    return ForecastScorecard(
        origin=origin,
        horizon=horizon,
        scores=scores,
        overall_rmse=overall_rmse,
        overall_mae=overall_mae,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _match_variable(
    suffix: str,
    score_map: Dict[str, VariableScore],
) -> Optional[str]:
    """Best-effort match of a gate key suffix (e.g. ``"gdp"``) to a
    variable name in *score_map* (e.g. ``"gdp_growth"``).

    Matching rules (in priority order):
    1. Exact match.
    2. Suffix appears as a prefix of a variable name (``"gdp"`` -> ``"gdp_growth"``).
    3. Suffix is contained anywhere in a variable name.
    """
    if suffix in score_map:
        return suffix

    # Prefix match.
    for var in score_map:
        if var.startswith(suffix + "_") or var.startswith(suffix):
            return var

    # Substring match.
    for var in score_map:
        if suffix in var:
            return var

    return None
