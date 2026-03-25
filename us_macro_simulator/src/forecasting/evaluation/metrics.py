"""Forecast evaluation metrics: RMSE, MAE, CRPS, coverage, directional accuracy."""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
from scipy.stats import norm


# ---------------------------------------------------------------------------
# Point-forecast metrics
# ---------------------------------------------------------------------------

def rmse(forecast: np.ndarray, actual: np.ndarray) -> float:
    """Root mean squared error.

    Parameters
    ----------
    forecast, actual : np.ndarray
        Arrays of the same shape.

    Returns
    -------
    float
        RMSE value, or ``nan`` if inputs are empty.
    """
    forecast = np.asarray(forecast, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if forecast.size == 0 or actual.size == 0:
        return float("nan")
    errors = forecast - actual
    return float(np.sqrt(np.nanmean(errors ** 2)))


def mae(forecast: np.ndarray, actual: np.ndarray) -> float:
    """Mean absolute error.

    Parameters
    ----------
    forecast, actual : np.ndarray
        Arrays of the same shape.

    Returns
    -------
    float
        MAE value, or ``nan`` if inputs are empty.
    """
    forecast = np.asarray(forecast, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if forecast.size == 0 or actual.size == 0:
        return float("nan")
    return float(np.nanmean(np.abs(forecast - actual)))


def relative_rmse(
    forecast: np.ndarray,
    actual: np.ndarray,
    benchmark: np.ndarray,
) -> float:
    """Relative RMSE: ``RMSE(forecast) / RMSE(benchmark)``.

    A value below 1.0 means the forecast beats the benchmark.

    Parameters
    ----------
    forecast, actual, benchmark : np.ndarray
        Arrays of the same shape.

    Returns
    -------
    float
        Ratio, or ``nan`` if the benchmark RMSE is zero or inputs are empty.
    """
    bench_rmse = rmse(benchmark, actual)
    if np.isnan(bench_rmse) or bench_rmse == 0.0:
        return float("nan")
    return rmse(forecast, actual) / bench_rmse


def directional_accuracy(
    forecast: np.ndarray,
    actual: np.ndarray,
) -> float:
    """Fraction of correct sign predictions.

    Both *forecast* and *actual* are treated as changes (or levels whose
    sign matters).  The metric counts how often ``sign(forecast) ==
    sign(actual)``.  Zeros in *actual* are excluded from the count.

    Parameters
    ----------
    forecast, actual : np.ndarray
        Arrays of the same shape.

    Returns
    -------
    float
        Value in [0, 1], or ``nan`` if no valid observations remain.
    """
    forecast = np.asarray(forecast, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if forecast.size == 0 or actual.size == 0:
        return float("nan")

    # Exclude observations where actual is exactly zero (ambiguous sign).
    mask = actual != 0.0
    if not np.any(mask):
        return float("nan")

    correct = np.sign(forecast[mask]) == np.sign(actual[mask])
    return float(np.mean(correct))


# ---------------------------------------------------------------------------
# Interval / density metrics
# ---------------------------------------------------------------------------

def coverage(
    lower: np.ndarray,
    upper: np.ndarray,
    actual: np.ndarray,
) -> float:
    """Fraction of actuals that fall within ``[lower, upper]``.

    Parameters
    ----------
    lower, upper, actual : np.ndarray
        Arrays of the same shape.

    Returns
    -------
    float
        Coverage rate in [0, 1], or ``nan`` if inputs are empty.
    """
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if actual.size == 0:
        return float("nan")

    inside = (actual >= lower) & (actual <= upper)
    return float(np.nanmean(inside))


def crps_gaussian(
    forecast_mean: np.ndarray,
    forecast_std: np.ndarray,
    actual: np.ndarray,
) -> float:
    """Continuous ranked probability score under a Gaussian assumption.

    Uses the closed-form expression:

        CRPS = sigma * [ z*(2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi) ]

    where ``z = (actual - mean) / sigma``, *Phi* is the standard-normal
    CDF, and *phi* is the standard-normal PDF.

    Parameters
    ----------
    forecast_mean, forecast_std, actual : np.ndarray
        Arrays of the same shape.  ``forecast_std`` must be > 0.

    Returns
    -------
    float
        Mean CRPS across observations, or ``nan`` if inputs are empty or
        any ``forecast_std`` is non-positive.
    """
    forecast_mean = np.asarray(forecast_mean, dtype=float)
    forecast_std = np.asarray(forecast_std, dtype=float)
    actual = np.asarray(actual, dtype=float)

    if actual.size == 0 or forecast_mean.size == 0:
        return float("nan")
    if np.any(forecast_std <= 0):
        return float("nan")

    z = (actual - forecast_mean) / forecast_std
    crps_per_obs = forecast_std * (
        z * (2.0 * norm.cdf(z) - 1.0)
        + 2.0 * norm.pdf(z)
        - 1.0 / np.sqrt(np.pi)
    )
    return float(np.nanmean(crps_per_obs))


# ---------------------------------------------------------------------------
# Convenience aggregator
# ---------------------------------------------------------------------------

def compute_all_metrics(
    forecast: np.ndarray,
    actual: np.ndarray,
    benchmark: Optional[np.ndarray] = None,
    lower: Optional[np.ndarray] = None,
    upper: Optional[np.ndarray] = None,
    forecast_std: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Compute all applicable metrics and return them in a flat dict.

    Parameters
    ----------
    forecast, actual : np.ndarray
        Point forecasts and realised values.
    benchmark : np.ndarray, optional
        Benchmark forecasts for relative RMSE.
    lower, upper : np.ndarray, optional
        Interval bounds for coverage.
    forecast_std : np.ndarray, optional
        Forecast standard deviations for CRPS (Gaussian).

    Returns
    -------
    Dict[str, float]
        Keys are metric names; values are ``nan`` when a metric cannot
        be computed from the supplied arguments.
    """
    results: Dict[str, float] = {
        "rmse": rmse(forecast, actual),
        "mae": mae(forecast, actual),
        "directional_accuracy": directional_accuracy(forecast, actual),
    }

    if benchmark is not None:
        results["relative_rmse"] = relative_rmse(forecast, actual, benchmark)

    if lower is not None and upper is not None:
        results["coverage"] = coverage(lower, upper, actual)

    if forecast_std is not None:
        results["crps"] = crps_gaussian(forecast, forecast_std, actual)

    return results
