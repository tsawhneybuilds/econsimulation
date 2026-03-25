"""Random walk benchmark: forecast = last observation."""
from __future__ import annotations

import numpy as np
import pandas as pd


class RandomWalkBenchmark:
    """Naive no-change forecast: every future value equals the last observed value."""

    name = "random_walk"

    def forecast(self, history: pd.Series, horizon: int) -> np.ndarray:
        """Return array of length *horizon*, all equal to the last observed value.

        Edge cases
        ----------
        * If *history* is entirely NaN or empty, returns an array of zeros.
        """
        clean = history.dropna()
        if len(clean) == 0:
            return np.zeros(horizon)
        last = float(clean.iloc[-1])
        return np.full(horizon, last)
