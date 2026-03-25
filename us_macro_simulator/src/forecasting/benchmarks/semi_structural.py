"""Reduced semi-structural macro benchmark for Stage 1 comparisons."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

import numpy as np
import pandas as pd


CORE_VARS = (
    "gdp_growth",
    "cpi_inflation",
    "unemployment_rate",
    "fed_funds_rate",
)


@dataclass
class _Equation:
    intercept: float
    coefs: np.ndarray
    regressors: tuple[str, ...]


class SemiStructuralBenchmark:
    """Small macro system with Phillips/Taylor/Okun-style linkages.

    This is intentionally lightweight. It provides a fairer comparator than
    pure univariate baselines without requiring a full DSGE estimation stack.
    """

    name = "semi_structural"

    def forecast(
        self,
        history: pd.DataFrame,
        horizon: int,
        variables: Iterable[str] | None = None,
    ) -> pd.DataFrame:
        if history.empty:
            cols = list(variables or CORE_VARS)
            return pd.DataFrame(
                np.zeros((horizon, len(cols))),
                columns=cols,
            )

        variables = list(variables or history.columns)
        clean = history.dropna(how="all").copy()
        if clean.empty:
            return pd.DataFrame(
                np.zeros((horizon, len(variables))),
                columns=variables,
            )

        equations = self._fit_equations(clean)
        state = {
            var: float(clean[var].dropna().iloc[-1])
            for var in clean.columns
            if not clean[var].dropna().empty
        }

        rows = []
        for _ in range(horizon):
            next_state = state.copy()
            for var in variables:
                if var in equations:
                    next_state[var] = self._predict(equations[var], state)
                else:
                    next_state[var] = self._fallback(clean[var], state.get(var, 0.0))
            rows.append({var: next_state.get(var, 0.0) for var in variables})
            state = next_state

        return pd.DataFrame(rows, columns=variables)

    def _fit_equations(self, history: pd.DataFrame) -> Dict[str, _Equation]:
        equations: Dict[str, _Equation] = {}

        specs: Dict[str, tuple[str, ...]] = {
            "gdp_growth": ("gdp_growth", "fed_funds_rate", "fci"),
            "cpi_inflation": ("cpi_inflation", "gdp_growth", "fed_funds_rate"),
            "unemployment_rate": ("unemployment_rate", "gdp_growth"),
            "fed_funds_rate": ("fed_funds_rate", "cpi_inflation", "gdp_growth"),
            "consumption_growth": ("consumption_growth", "gdp_growth", "fed_funds_rate"),
            "residential_inv_growth": (
                "residential_inv_growth",
                "gdp_growth",
                "fed_funds_rate",
                "fci",
            ),
            "fci": ("fci", "fed_funds_rate"),
        }

        for target, regressors in specs.items():
            if target not in history.columns:
                continue
            available_regressors = [reg for reg in regressors if reg in history.columns]
            if not available_regressors:
                continue
            unique_cols = []
            for col in [target, *available_regressors]:
                if col not in unique_cols:
                    unique_cols.append(col)
            frame = history[unique_cols].dropna().copy()
            if len(frame) < 6:
                continue

            y = frame[target].iloc[1:].to_numpy(dtype=float)
            x_lag = frame[available_regressors].iloc[:-1].to_numpy(dtype=float)
            if len(y) != len(x_lag):
                continue

            x = np.column_stack([np.ones(len(x_lag)), x_lag])
            beta, *_ = np.linalg.lstsq(x, y, rcond=None)
            equations[target] = _Equation(
                intercept=float(beta[0]),
                coefs=beta[1:].astype(float),
                regressors=tuple(available_regressors),
            )

        return equations

    @staticmethod
    def _predict(equation: _Equation, state: Dict[str, float]) -> float:
        reg_vals = np.array([state.get(reg, 0.0) for reg in equation.regressors], dtype=float)
        return float(equation.intercept + equation.coefs @ reg_vals)

    @staticmethod
    def _fallback(series: pd.Series, current_value: float) -> float:
        clean = series.dropna()
        if len(clean) >= 4:
            return float(clean.iloc[-4:].mean())
        if len(clean) > 0:
            return float(clean.iloc[-1])
        return float(current_value)
