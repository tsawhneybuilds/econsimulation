"""Local mean benchmark: forecast = rolling mean of last W observations."""
from __future__ import annotations

import numpy as np
import pandas as pd


class LocalMeanBenchmark:
    """Forecast equals the arithmetic mean of the last *window* observations.

    If the available (non-NaN) history is shorter than *window* the mean
    is taken over whatever observations are available.
    """

    name = "local_mean"

    def __init__(self, window: int = 8):
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        self.window = window

    def forecast(self, history: pd.Series, horizon: int) -> np.ndarray:
        """Return array of length *horizon*, all equal to the local mean.

        Edge cases
        ----------
        * Entirely NaN / empty history  ->  returns zeros.
        * Fewer than *window* valid observations  ->  mean of all available.
        """
        clean = history.dropna()
        if len(clean) == 0:
            return np.zeros(horizon)

        tail = clean.iloc[-self.window :]
        mean_val = float(tail.mean())
        return np.full(horizon, mean_val)
