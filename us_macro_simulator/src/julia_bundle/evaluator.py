"""Evaluate Julia artifact bundles with Python benchmark models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd

from src.forecasting.evaluation.scorecard import ForecastScorecard, build_scorecard
from src.forecasting.runners.backtest_runner import BacktestConfig, BacktestResult, BacktestRunner
from src.forecasting.runners.us_runner import ForecastArtifact
from src.julia_bundle.loader import JuliaArtifactBundle


@dataclass
class JuliaBundleBacktestEvaluator:
    bundle: JuliaArtifactBundle

    def run(self) -> BacktestResult:
        config = BacktestConfig(
            start_origin=self.bundle.manifest["start_origin"],
            end_origin=self.bundle.manifest["end_origin"],
            horizon=int(self.bundle.manifest["horizon"]),
            variables=self.bundle.variables,
        )
        runner = BacktestRunner(config=config)
        actuals = runner._to_target_variables(self.bundle.full_actuals_raw())

        artifacts: Dict[str, ForecastArtifact] = {}
        benchmark_forecasts: Dict[str, Dict[str, pd.DataFrame]] = {}
        simulator_scorecards: Dict[str, ForecastScorecard] = {}
        benchmark_scorecards: Dict[str, Dict[str, ForecastScorecard]] = {}
        flat_scorecards: Dict[str, Dict[str, float]] = {}

        for origin in self.bundle.origins:
            point_forecasts = self.bundle.forecast_matrix_for_origin(origin, value_col="mean")
            history = runner._to_target_variables(self.bundle.raw_history_for_origin(origin))
            benchmark_df_by_name = runner._run_benchmarks(
                history=history,
                forecast_index=point_forecasts.index,
            )
            benchmark_forecasts[origin] = benchmark_df_by_name

            artifacts[origin] = ForecastArtifact(
                run_id=str(self.bundle.manifest.get("run_id", "unknown")),
                config_hash="",
                calibration_hash="",
                data_vintage_hash="",
                seed=int(self.bundle.manifest.get("seed", 42)),
                origin_quarter=origin,
                horizon=len(point_forecasts),
                point_forecasts=point_forecasts,
                density_summaries=point_forecasts.copy(),
                validation_summary={},
                runtime_seconds=float(self.bundle.manifest.get("runtime_seconds", 0.0)),
                manifest=None,
            )

            actual_slice = actuals.loc[actuals.index.intersection(point_forecasts.index)]
            random_walk = benchmark_df_by_name.get("random_walk")
            simulator_card = build_scorecard(
                forecasts=point_forecasts,
                actuals=actual_slice,
                origin=origin,
                horizon=config.horizon,
                benchmark=random_walk,
            )
            simulator_scorecards[origin] = simulator_card
            flat_scorecards[origin] = runner._flatten_scorecard("sim", simulator_card)

            benchmark_scorecards[origin] = {}
            for bench_name, bench_df in benchmark_df_by_name.items():
                benchmark_scorecards[origin][bench_name] = build_scorecard(
                    forecasts=bench_df,
                    actuals=actual_slice,
                    origin=origin,
                    horizon=config.horizon,
                )

        return BacktestResult(
            config=config,
            origins=self.bundle.origins,
            artifacts=artifacts,
            scorecards=flat_scorecards,
            simulator_scorecards=simulator_scorecards,
            benchmark_scorecards=benchmark_scorecards,
            benchmark_forecasts=benchmark_forecasts,
            comparison_table=runner._build_comparison_table(
                simulator_scorecards=simulator_scorecards,
                benchmark_scorecards=benchmark_scorecards,
            ),
            runtime_seconds=float(self.bundle.manifest.get("runtime_seconds", 0.0)),
            notes=[
                "Simulator forecasts were loaded from the Julia Stage 1 bundle.",
                "Benchmarks were recomputed in Python on the same origin/horizon grid.",
            ],
        )
