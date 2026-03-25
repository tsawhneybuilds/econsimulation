"""AR(4) benchmark – pure-numpy OLS implementation."""
from __future__ import annotations

import numpy as np
import pandas as pd


class ARBenchmark:
    """Autoregressive benchmark of configurable order (default 4).

    The model is fit via ordinary least squares on a Hankel-style lag
    matrix built from the supplied history.  Multi-step forecasts are
    produced iteratively (each predicted value is fed back as input for
    the next step).
    """

    name = "ar4"

    def __init__(self, order: int = 4):
        self.order = order
        self._coefs: np.ndarray | None = None  # shape (order,)
        self._intercept: float = 0.0

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------
    def fit(self, history: pd.Series) -> "ARBenchmark":
        """Fit AR(order) via OLS on *history*.

        If the usable history (after dropping NaNs) is shorter than
        ``order + 2`` observations the model falls back to a random-walk
        parameterisation (intercept = 0, first lag coefficient = 1,
        remaining coefficients = 0).
        """
        y = history.dropna().values.astype(float)
        effective_order = min(self.order, len(y) - 1)

        if effective_order < 1 or len(y) < effective_order + 2:
            # Not enough data – fall back to random walk.
            self._coefs = np.zeros(self.order)
            self._coefs[0] = 1.0
            self._intercept = 0.0
            return self

        # Build lag matrix X and target vector Y.
        n = len(y) - effective_order
        X = np.ones((n, effective_order + 1))  # +1 for intercept column
        for lag in range(1, effective_order + 1):
            X[:, lag] = y[effective_order - lag : effective_order - lag + n]
        Y = y[effective_order:]

        # Solve normal equations:  beta = (X'X)^{-1} X'Y
        try:
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        except np.linalg.LinAlgError:
            # Singular matrix – fall back to random walk.
            self._coefs = np.zeros(self.order)
            self._coefs[0] = 1.0
            self._intercept = 0.0
            return self

        self._intercept = beta[0]
        fitted = beta[1 : effective_order + 1]

        # Pad with zeros if effective_order < self.order.
        if effective_order < self.order:
            self._coefs = np.zeros(self.order)
            self._coefs[:effective_order] = fitted
        else:
            self._coefs = fitted

        return self

    # ------------------------------------------------------------------
    # Forecasting
    # ------------------------------------------------------------------
    def forecast(self, history: pd.Series, horizon: int) -> np.ndarray:
        """Fit on *history* then produce *horizon*-step iterative forecasts."""
        self.fit(history)

        y = history.dropna().values.astype(float)
        if len(y) == 0:
            return np.zeros(horizon)

        # Seed the rolling buffer with the last `order` observations
        # (or fewer if history is short).
        buf = list(y[-self.order :]) if len(y) >= self.order else list(y)

        preds = np.empty(horizon)
        for h in range(horizon):
            # Build the lag vector (most recent first).
            lags = np.array(buf[-self.order :][::-1]) if len(buf) >= self.order else np.array(buf[::-1])
            n_lags = len(lags)
            yhat = self._intercept + float(self._coefs[:n_lags] @ lags)
            preds[h] = yhat
            buf.append(yhat)

        return preds
