"""Factor model benchmark: PCA-based multivariate forecast (numpy SVD)."""
from __future__ import annotations

import numpy as np
import pandas as pd


class FactorModelBenchmark:
    """Simple principal-component factor model.

    Steps
    -----
    1. Standardise every column in the multivariate *history* DataFrame.
    2. Extract the first *n_factors* principal components via truncated SVD.
    3. Fit an AR(*ar_order*) model on each factor series (OLS, same
       approach as :class:`ARBenchmark`).
    4. Iteratively forecast each factor *horizon* steps ahead.
    5. Project the forecasted factors back to the *target_col* variable
       using the corresponding loading vector and undo the standardisation.
    """

    name = "factor_model"

    def __init__(self, n_factors: int = 2, ar_order: int = 2):
        if n_factors < 1:
            raise ValueError(f"n_factors must be >= 1, got {n_factors}")
        if ar_order < 1:
            raise ValueError(f"ar_order must be >= 1, got {ar_order}")
        self.n_factors = n_factors
        self.ar_order = ar_order

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _fit_ar_ols(y: np.ndarray, order: int) -> tuple[float, np.ndarray]:
        """Fit AR(order) on 1-D array *y* via OLS.

        Returns (intercept, coefs) where *coefs* has shape ``(order,)``
        with coefs[0] corresponding to lag-1.

        Falls back to random-walk parameters when data is insufficient.
        """
        effective_order = min(order, len(y) - 1)
        if effective_order < 1 or len(y) < effective_order + 2:
            coefs = np.zeros(order)
            coefs[0] = 1.0
            return 0.0, coefs

        n = len(y) - effective_order
        X = np.ones((n, effective_order + 1))
        for lag in range(1, effective_order + 1):
            X[:, lag] = y[effective_order - lag : effective_order - lag + n]
        Y = y[effective_order:]

        try:
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        except np.linalg.LinAlgError:
            coefs = np.zeros(order)
            coefs[0] = 1.0
            return 0.0, coefs

        intercept = beta[0]
        fitted = beta[1 : effective_order + 1]

        if effective_order < order:
            coefs = np.zeros(order)
            coefs[:effective_order] = fitted
        else:
            coefs = fitted

        return intercept, coefs

    @staticmethod
    def _ar_forecast(
        intercept: float, coefs: np.ndarray, tail: np.ndarray, horizon: int
    ) -> np.ndarray:
        """Iterate an AR model forward *horizon* steps.

        *tail* should contain the last ``len(coefs)`` observations
        (oldest first).
        """
        order = len(coefs)
        buf = list(tail[-order:]) if len(tail) >= order else list(tail)
        preds = np.empty(horizon)
        for h in range(horizon):
            lags = np.array(buf[-order:][::-1]) if len(buf) >= order else np.array(buf[::-1])
            n_lags = len(lags)
            yhat = intercept + float(coefs[:n_lags] @ lags)
            preds[h] = yhat
            buf.append(yhat)
        return preds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def forecast(
        self, history: pd.DataFrame, horizon: int, target_col: str
    ) -> np.ndarray:
        """Produce *horizon*-step forecasts for *target_col*.

        Parameters
        ----------
        history : pd.DataFrame
            Multivariate time-series history (rows = time, columns = variables).
        horizon : int
            Number of steps to forecast.
        target_col : str
            Column name of the variable to forecast.

        Edge cases
        ----------
        * If *target_col* is not in *history*, raises ``KeyError``.
        * If the usable history has fewer rows than ``n_factors + ar_order + 2``
          the method falls back to a univariate local-mean forecast.
        """
        if target_col not in history.columns:
            raise KeyError(
                f"target_col '{target_col}' not found in history columns: "
                f"{list(history.columns)}"
            )

        # Drop rows with any NaN to get a clean rectangular block.
        clean = history.dropna()
        if len(clean) < self.n_factors + self.ar_order + 2 or clean.shape[1] < 2:
            # Not enough data for factor extraction – fall back.
            return self._fallback(history[target_col], horizon)

        data = clean.values.astype(float)  # (T, K)
        T, K = data.shape

        # ---- 1. Standardise ----
        means = data.mean(axis=0)
        stds = data.std(axis=0, ddof=1)
        stds[stds == 0] = 1.0  # avoid division by zero for constant columns
        Z = (data - means) / stds  # (T, K)

        # ---- 2. SVD ----
        n_factors = min(self.n_factors, K, T)
        U, S, Vt = np.linalg.svd(Z, full_matrices=False)
        # Factors: F = U[:, :n_factors] * S[:n_factors]  shape (T, n_factors)
        F = U[:, :n_factors] * S[:n_factors]
        # Loadings: Lambda = Vt[:n_factors, :]  shape (n_factors, K)
        Lambda = Vt[:n_factors, :]

        # ---- 3. Fit AR on each factor ----
        ar_params: list[tuple[float, np.ndarray]] = []
        for j in range(n_factors):
            intercept, coefs = self._fit_ar_ols(F[:, j], self.ar_order)
            ar_params.append((intercept, coefs))

        # ---- 4. Forecast factors ----
        F_fcast = np.empty((horizon, n_factors))
        for j in range(n_factors):
            intercept, coefs = ar_params[j]
            F_fcast[:, j] = self._ar_forecast(intercept, coefs, F[:, j], horizon)

        # ---- 5. Project back to target variable ----
        target_idx = list(clean.columns).index(target_col)
        loadings_target = Lambda[:, target_idx]  # (n_factors,)

        # Forecasted standardised target = F_fcast @ loadings_target
        z_fcast = F_fcast @ loadings_target  # (horizon,)

        # Undo standardisation.
        y_fcast = z_fcast * stds[target_idx] + means[target_idx]
        return y_fcast

    # ------------------------------------------------------------------
    def _fallback(self, series: pd.Series, horizon: int) -> np.ndarray:
        """Simple local-mean fallback when factor extraction is not viable."""
        clean = series.dropna()
        if len(clean) == 0:
            return np.zeros(horizon)
        mean_val = float(clean.iloc[-8:].mean())
        return np.full(horizon, mean_val)
