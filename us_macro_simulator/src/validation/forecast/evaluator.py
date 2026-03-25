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
        dsge_gates: Dict[str, float] | None = None,
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

        # DSGE comparison check
        if dsge_gates and not result.comparison_table.empty:
            checks.extend(self._check_dsge(result, dsge_gates))

        return checks

    def _check_dsge(
        self,
        result: BacktestResult,
        dsge_gates: Dict[str, float],
    ) -> List[ValidationCheck]:
        """Compare simulator RMSE against the NY Fed DSGE benchmark."""
        checks: List[ValidationCheck] = []
        ct = result.comparison_table

        if "model" not in ct.columns or "rmse" not in ct.columns:
            return checks

        dsge_rows = ct[ct["model"] == "dsge_nyfed"]
        sim_rows = ct[ct["model"] == "simulator"] if "simulator" in ct["model"].values else ct[ct["model"] == "sim"]

        if dsge_rows.empty or sim_rows.empty:
            checks.append(
                ValidationCheck(
                    name="dsge_nyfed_available",
                    passed=False,
                    severity="soft",
                    summary="NY Fed DSGE benchmark rows not found in comparison table — cache may be missing.",
                    details={"models_present": ct["model"].unique().tolist()},
                )
            )
            return checks

        checks.append(
            ValidationCheck(
                name="dsge_nyfed_available",
                passed=True,
                severity="soft",
                summary="NY Fed DSGE benchmark forecasts loaded and compared.",
                details={"n_dsge_rows": len(dsge_rows)},
            )
        )

        # Compute average RMSE for simulator vs DSGE across shared variables
        shared_vars = set(dsge_rows["variable"].unique()) & set(sim_rows["variable"].unique())
        if not shared_vars:
            return checks

        ratios = []
        for var in shared_vars:
            sim_rmse_vals = sim_rows[sim_rows["variable"] == var]["rmse"].dropna()
            dsge_rmse_vals = dsge_rows[dsge_rows["variable"] == var]["rmse"].dropna()
            if sim_rmse_vals.empty or dsge_rmse_vals.empty:
                continue
            sim_avg = float(sim_rmse_vals.mean())
            dsge_avg = float(dsge_rmse_vals.mean())
            if dsge_avg > 0:
                ratios.append(sim_avg / dsge_avg)

        if not ratios:
            return checks

        avg_ratio = float(np.mean(ratios))
        threshold = dsge_gates.get("max_relative_rmse_vs_dsge", 3.0)
        must_beat = dsge_gates.get("must_beat_dsge", False)

        checks.append(
            ValidationCheck(
                name="relative_rmse_vs_dsge",
                passed=avg_ratio <= threshold,
                severity="soft",
                summary="Simulator RMSE relative to NY Fed DSGE is within tolerance.",
                details={
                    "average_relative_rmse_vs_dsge": avg_ratio,
                    "threshold": threshold,
                    "variables_compared": sorted(shared_vars),
                },
            )
        )

        if must_beat:
            checks.append(
                ValidationCheck(
                    name="must_beat_dsge",
                    passed=avg_ratio < 1.0,
                    severity="hard",
                    summary="Simulator must outperform the NY Fed DSGE benchmark on average RMSE.",
                    details={"average_relative_rmse_vs_dsge": avg_ratio},
                )
            )

        return checks
