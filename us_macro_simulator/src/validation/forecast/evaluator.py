"""Forecast quality and benchmark comparison checks."""
from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np

from src.forecasting.runners.backtest_runner import BacktestResult
from src.validation.models import ValidationCheck


def _match_variable(suffix: str, variables: Iterable[str]) -> str | None:
    variables = list(variables)
    if suffix in variables:
        return suffix
    for variable in variables:
        if variable.startswith(suffix + "_") or suffix in variable:
            return variable
    return None


class ForecastEvaluator:
    """Evaluate forecast scorecards against configured gates."""

    def check(
        self,
        result: BacktestResult,
        forecast_gates: Dict[str, float],
        benchmark_gates: Dict[str, float],
    ) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        variable_metrics: Dict[str, Dict[str, List[float]]] = {}

        for card in result.simulator_scorecards.values():
            for score in card.scores:
                bucket = variable_metrics.setdefault(score.variable, {})
                for metric_name, metric_value in score.to_dict().items():
                    if metric_name == "variable":
                        continue
                    if metric_value is None or np.isnan(metric_value):
                        continue
                    bucket.setdefault(metric_name, []).append(float(metric_value))

        checks.append(
            ValidationCheck(
                name="scorecards_present",
                passed=bool(result.simulator_scorecards),
                severity="hard",
                summary="Backtest produced simulator scorecards.",
                details={"n_scorecards": len(result.simulator_scorecards)},
            )
        )

        for gate_name, threshold in forecast_gates.items():
            if gate_name.startswith("max_rmse_"):
                suffix = gate_name[len("max_rmse_"):]
                matched = _match_variable(suffix, variable_metrics.keys())
                values = variable_metrics.get(matched or "", {}).get("rmse", [])
                avg_value = float(np.mean(values)) if values else float("nan")
                checks.append(
                    ValidationCheck(
                        name=gate_name,
                        passed=bool(values) and avg_value <= threshold,
                        severity="hard",
                        summary=f"Average RMSE for {matched or suffix} stays below the configured gate.",
                        details={"average_rmse": avg_value, "threshold": threshold},
                    )
                )
            elif gate_name.startswith("min_coverage_"):
                metric = "coverage_50" if "50" in gate_name else "coverage_90"
                values = [
                    value
                    for metric_map in variable_metrics.values()
                    for value in metric_map.get(metric, [])
                ]
                avg_value = float(np.mean(values)) if values else float("nan")
                checks.append(
                    ValidationCheck(
                        name=gate_name,
                        passed=bool(values) and avg_value >= threshold,
                        severity="soft",
                        summary=f"Average {metric} meets the configured gate when density data exists.",
                        details={"average_value": avg_value, "threshold": threshold},
                    )
                )

        relative_values = [
            float(score.relative_rmse)
            for card in result.simulator_scorecards.values()
            for score in card.scores
            if score.relative_rmse is not None and not np.isnan(score.relative_rmse)
        ]
        relative_threshold = benchmark_gates.get("relative_rmse_threshold", 1.0)
        avg_relative = float(np.mean(relative_values)) if relative_values else float("nan")
        checks.append(
            ValidationCheck(
                name="relative_rmse_vs_random_walk",
                passed=bool(relative_values) and avg_relative <= relative_threshold,
                severity="soft",
                summary="Simulator relative RMSE against the random walk benchmark is within tolerance.",
                details={"average_relative_rmse": avg_relative, "threshold": relative_threshold},
            )
        )

        if benchmark_gates.get("must_beat_random_walk", False):
            checks.append(
                ValidationCheck(
                    name="must_beat_random_walk",
                    passed=bool(relative_values) and avg_relative < 1.0,
                    severity="hard",
                    summary="Simulator beats the random walk benchmark on average RMSE.",
                    details={"average_relative_rmse": avg_relative},
                )
            )

        return checks
