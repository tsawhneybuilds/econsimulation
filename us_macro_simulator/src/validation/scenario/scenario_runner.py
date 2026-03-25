"""Scenario runner used by the validation harness."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Dict

import pandas as pd

from src.engine.core.state import SimulationState
from src.engine.shocks.shock_protocol import NoShock, RateShock
from src.forecasting.runners.us_runner import USForecastRunner


@dataclass
class ScenarioResult:
    """Compact scenario comparison."""

    name: str
    baseline: pd.DataFrame
    shocked: pd.DataFrame
    deltas: Dict[str, float]

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "baseline_last_row": self.baseline.tail(1).to_dict(orient="records"),
            "shocked_last_row": self.shocked.tail(1).to_dict(orient="records"),
            "deltas": self.deltas,
        }


class ScenarioRunner:
    """Run a small baseline-vs-rate-shock comparison."""

    def run_rate_shock(
        self,
        state: SimulationState,
        horizon: int = 4,
    ) -> ScenarioResult:
        runner = USForecastRunner()
        baseline = runner.run(copy.deepcopy(state), T=horizon, shock=NoShock(), seed=101)
        shocked = runner.run(
            copy.deepcopy(state),
            T=horizon,
            shock=RateShock(delta_r=0.005, duration=2),
            seed=101,
        )

        common_cols = sorted(set(baseline.point_forecasts.columns) & set(shocked.point_forecasts.columns))
        deltas = {
            column: float(shocked.point_forecasts[column].iloc[-1] - baseline.point_forecasts[column].iloc[-1])
            for column in common_cols
        }
        return ScenarioResult(
            name="rate_shock",
            baseline=baseline.point_forecasts,
            shocked=shocked.point_forecasts,
            deltas=deltas,
        )
