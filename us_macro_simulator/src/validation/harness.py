"""Validation harness for Stage 1 outputs."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import yaml

from src.engine.core.state import SimulationState
from src.forecasting.runners.backtest_runner import BacktestResult
from src.us.data_contracts.build_dataset import ObservedDataset
from src.validation.cross_section.checker import CrossSectionChecker
from src.validation.data_quality.checker import DataQualityChecker
from src.validation.forecast.evaluator import ForecastEvaluator
from src.validation.identities.checker import IdentityChecker
from src.validation.models import ValidationCheck, ValidationReport
from src.validation.performance.checker import PerformanceChecker
from src.validation.replay.episode_checker import ReplayEpisodeChecker
from src.validation.scenario.scenario_runner import ScenarioRunner


class ValidationHarness:
    """Run the configured validation checks over Stage 1 artifacts."""

    def __init__(self, gates: Dict[str, Dict[str, float]]) -> None:
        self.gates = gates

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ValidationHarness":
        with open(path) as handle:
            gates = yaml.safe_load(handle)
        return cls(gates=gates)

    def run(
        self,
        *,
        dataset: ObservedDataset,
        initial_state: SimulationState,
        backtest_result: BacktestResult,
        observed_cross_section: Optional[pd.DataFrame] = None,
    ) -> ValidationReport:
        checks: list[ValidationCheck] = []
        checks.extend(DataQualityChecker().check(dataset))
        checks.extend(
            IdentityChecker().check(
                initial_state,
                tolerance=float(self.gates["hard_gates"].get("accounting_identity_tolerance", 1.0e-6)),
            )
        )
        checks.extend(
            ForecastEvaluator().check(
                backtest_result,
                forecast_gates=self.gates.get("forecast_gates", {}),
                benchmark_gates=self.gates.get("benchmark_gates", {}),
            )
        )
        checks.extend(CrossSectionChecker().check(initial_state, observed_cross_section))
        checks.extend(
            PerformanceChecker().check(
                runtime_seconds=backtest_result.runtime_seconds,
                gates=self.gates.get("performance_gates", {}),
            )
        )
        checks.extend(ReplayEpisodeChecker().check(initial_state))

        scenario_result = ScenarioRunner().run_rate_shock(initial_state)
        hard_failures = [check for check in checks if check.severity == "hard" and not check.passed]

        return ValidationReport(
            run_id=next(iter(backtest_result.artifacts.values())).run_id if backtest_result.artifacts else "unknown",
            overall_passed=len(hard_failures) == 0,
            checks=checks,
            summary={
                "n_checks": len(checks),
                "n_hard_failures": len(hard_failures),
                "n_soft_failures": len([check for check in checks if check.severity != "hard" and not check.passed]),
                "comparison_rows": len(backtest_result.comparison_table),
                "scenario": scenario_result.to_dict(),
            },
            notes=list(backtest_result.notes),
        )
