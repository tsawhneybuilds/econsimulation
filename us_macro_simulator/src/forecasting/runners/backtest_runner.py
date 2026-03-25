"""BacktestRunner: recursive pseudo-real-time backtesting with benchmarks."""
from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.engine.shocks.shock_protocol import NoShock, ShockProtocol
from src.forecasting.benchmarks.registry import get_benchmark
from src.forecasting.evaluation.scorecard import ForecastScorecard, build_scorecard
from src.forecasting.runners.us_runner import ForecastArtifact, USForecastRunner
from src.us.calibration import build_us_2019q4_calibration
from src.us.data_contracts.build_dataset import DatasetBuilder, ObservedDataset
from src.us.initialization import USInitializer

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    start_origin: str = "2017Q1"
    end_origin: str = "2019Q4"
    horizon: int = 4
    seed: int = 42
    fixture_tier: str = "tier_b"
    data_source: str = "fixture"
    variables: List[str] = field(default_factory=lambda: [
        "gdp_growth",
        "cpi_inflation",
        "unemployment_rate",
        "fed_funds_rate",
        "consumption_growth",
        "residential_inv_growth",
        "fci",
    ])
    benchmark_names: List[str] = field(default_factory=lambda: [
        "random_walk",
        "ar4",
        "local_mean",
        "factor_model",
        "semi_structural",
    ])


@dataclass
class BacktestResult:
    """Results from a full backtest."""

    config: BacktestConfig
    origins: List[str]
    artifacts: Dict[str, ForecastArtifact]
    scorecards: Dict[str, Dict[str, float]] = field(default_factory=dict)
    simulator_scorecards: Dict[str, ForecastScorecard] = field(default_factory=dict)
    benchmark_scorecards: Dict[str, Dict[str, ForecastScorecard]] = field(default_factory=dict)
    benchmark_forecasts: Dict[str, Dict[str, pd.DataFrame]] = field(default_factory=dict)
    comparison_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    runtime_seconds: float = 0.0
    notes: List[str] = field(default_factory=list)

    def get_forecasts_at_horizon(self, h: int, variable: str) -> pd.Series:
        values = {}
        for origin_label, artifact in self.artifacts.items():
            pf = artifact.point_forecasts
            if variable not in pf.columns:
                continue
            if h < 1 or h > len(pf):
                raise ValueError(
                    f"Horizon h={h} out of range for origin {origin_label} "
                    f"(max {len(pf)} steps stored)."
                )
            values[origin_label] = float(pf[variable].iloc[h - 1])
        return pd.Series(values, name=f"{variable}_h{h}")

    def to_dataframe(self) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for origin_label, artifact in self.artifacts.items():
            pf = artifact.point_forecasts
            for h_idx in range(len(pf)):
                for var in pf.columns:
                    rows.append({
                        "origin": origin_label,
                        "horizon": h_idx + 1,
                        "variable": var,
                        "forecast_value": float(pf[var].iloc[h_idx]),
                    })
        return pd.DataFrame(rows)


class BacktestRunner:
    """Recursive pseudo-real-time backtest over quarterly forecast origins."""

    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        shock: Optional[ShockProtocol] = None,
    ) -> None:
        self.config = config or BacktestConfig()
        self.shock = shock

    def run(
        self,
        actuals: Optional[pd.DataFrame] = None,
    ) -> BacktestResult:
        t0 = time.perf_counter()
        cfg = self.config
        origins = self._generate_origins(cfg.start_origin, cfg.end_origin)
        calib = build_us_2019q4_calibration()
        initializer = USInitializer()
        runner = USForecastRunner()

        if actuals is None:
            actuals = self._build_actuals()

        artifacts: Dict[str, ForecastArtifact] = {}
        benchmark_forecasts: Dict[str, Dict[str, pd.DataFrame]] = {}
        simulator_scorecards: Dict[str, ForecastScorecard] = {}
        benchmark_scorecards: Dict[str, Dict[str, ForecastScorecard]] = {}
        flat_scorecards: Dict[str, Dict[str, float]] = {}

        for i, origin_label in enumerate(origins):
            origin_seed = self._derive_seed(cfg.seed, origin_label)
            origin_period = pd.Period(origin_label, freq="Q")
            as_of = origin_period.to_timestamp(how="end").floor("D").to_pydatetime()
            logger.info(
                "Backtest [%d/%d] origin=%s as_of=%s seed=%d",
                i + 1,
                len(origins),
                origin_label,
                as_of.date(),
                origin_seed,
            )

            obs_data = self._build_observed_dataset(as_of)
            history = self._to_target_variables(obs_data.data)
            state = initializer.initialize(calib=calib, obs_data=obs_data, seed=origin_seed)
            state.origin_quarter = origin_label

            origin_shock = copy.deepcopy(self.shock) if self.shock else NoShock()
            artifact = runner.run(
                state=state,
                T=cfg.horizon,
                shock=origin_shock,
                config_hash=calib.version_hash,
                calibration_hash=calib.version_hash,
                data_vintage_hash=self._dataset_hash_token(obs_data),
                seed=origin_seed,
            )
            artifacts[origin_label] = artifact

            benchmark_df_by_name = self._run_benchmarks(
                history=history,
                forecast_index=artifact.point_forecasts.index,
            )
            benchmark_forecasts[origin_label] = benchmark_df_by_name

            actual_slice = actuals.loc[actuals.index.intersection(artifact.point_forecasts.index)]
            random_walk = benchmark_df_by_name.get("random_walk")
            simulator_card = build_scorecard(
                forecasts=artifact.point_forecasts,
                actuals=actual_slice,
                origin=origin_label,
                horizon=cfg.horizon,
                benchmark=random_walk,
            )
            simulator_scorecards[origin_label] = simulator_card
            flat_scorecards[origin_label] = self._flatten_scorecard("sim", simulator_card)

            benchmark_scorecards[origin_label] = {}
            for bench_name, bench_df in benchmark_df_by_name.items():
                benchmark_scorecards[origin_label][bench_name] = build_scorecard(
                    forecasts=bench_df,
                    actuals=actual_slice,
                    origin=origin_label,
                    horizon=cfg.horizon,
                )

        t1 = time.perf_counter()
        return BacktestResult(
            config=cfg,
            origins=origins,
            artifacts=artifacts,
            scorecards=flat_scorecards,
            simulator_scorecards=simulator_scorecards,
            benchmark_scorecards=benchmark_scorecards,
            benchmark_forecasts=benchmark_forecasts,
            comparison_table=self._build_comparison_table(
                simulator_scorecards=simulator_scorecards,
                benchmark_scorecards=benchmark_scorecards,
            ),
            runtime_seconds=t1 - t0,
            notes=[
                "Observed aggregates are vintage-masked per origin.",
                "Structural parameters remain anchored to the 2019Q4 calibration bundle.",
            ],
        )

    @staticmethod
    def _generate_origins(start: str, end: str) -> List[str]:
        rng = pd.period_range(
            start=pd.Period(start, freq="Q"),
            end=pd.Period(end, freq="Q"),
            freq="Q",
        )
        return [str(p) for p in rng]

    @staticmethod
    def _derive_seed(base_seed: int, origin_label: str) -> int:
        origin_hash = hash(origin_label) & 0xFFFFFFFF
        return (base_seed * 2654435761 + origin_hash) & 0x7FFFFFFF

    def _build_observed_dataset(self, as_of: datetime) -> ObservedDataset:
        builder = DatasetBuilder()
        effective_as_of = (pd.Timestamp(as_of).floor("D") + pd.Timedelta(days=1)).to_pydatetime()
        config = {
            "source": self.config.data_source,
            "frequency": "Q",
            "fixture_tier": self.config.fixture_tier,
            "vintage_date": effective_as_of.date().isoformat(),
            "mask_unavailable": True,
            "allow_leakage": False,
        }
        return builder.build(config, vintage_date=effective_as_of)

    def _build_actuals(self) -> pd.DataFrame:
        builder = DatasetBuilder()
        config = {
            "source": self.config.data_source,
            "frequency": "Q",
            "fixture_tier": self.config.fixture_tier,
            "vintage_date": "2100-01-01",
            "mask_unavailable": True,
            "allow_leakage": False,
        }
        dataset = builder.build(config, vintage_date=datetime(2100, 1, 1))
        return self._to_target_variables(dataset.data)

    def _run_benchmarks(
        self,
        history: pd.DataFrame,
        forecast_index: pd.PeriodIndex,
    ) -> Dict[str, pd.DataFrame]:
        benchmark_results: Dict[str, pd.DataFrame] = {}
        available_history = history[self.config.variables].copy()

        for bench_name in self.config.benchmark_names:
            benchmark = get_benchmark(bench_name)
            bench_df = pd.DataFrame(index=forecast_index, columns=self.config.variables, dtype=float)

            if bench_name == "semi_structural":
                predicted = benchmark.forecast(
                    available_history,
                    horizon=len(forecast_index),
                    variables=self.config.variables,
                )
                predicted.index = forecast_index
                bench_df.loc[:, predicted.columns] = predicted.values
            elif bench_name == "factor_model":
                for variable in self.config.variables:
                    if variable not in available_history.columns:
                        continue
                    bench_df[variable] = benchmark.forecast(
                        available_history,
                        horizon=len(forecast_index),
                        target_col=variable,
                    )
            else:
                for variable in self.config.variables:
                    if variable not in available_history.columns:
                        continue
                    bench_df[variable] = benchmark.forecast(
                        available_history[variable],
                        horizon=len(forecast_index),
                    )

            benchmark_results[bench_name] = bench_df

        return benchmark_results

    @staticmethod
    def _annualised_growth_from_level(series: pd.Series) -> pd.Series:
        growth = ((series / series.shift(1)) ** 4 - 1.0) * 100.0
        return growth.replace([np.inf, -np.inf], np.nan)

    def _to_target_variables(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        df = raw_data.copy()
        if not isinstance(df.index, pd.PeriodIndex):
            df.index = pd.PeriodIndex(df.index, freq="Q")

        target = pd.DataFrame(index=df.index)
        if "GDPC1_GROWTH" in df.columns:
            target["gdp_growth"] = df["GDPC1_GROWTH"]
        elif "GDPC1" in df.columns:
            target["gdp_growth"] = self._annualised_growth_from_level(df["GDPC1"])

        if "CPIAUCSL" in df.columns:
            target["cpi_inflation"] = self._annualised_growth_from_level(df["CPIAUCSL"])
        if "CPILFESL" in df.columns:
            target["core_cpi_inflation"] = self._annualised_growth_from_level(df["CPILFESL"])
        if "UNRATE" in df.columns:
            target["unemployment_rate"] = df["UNRATE"]
        if "FEDFUNDS" in df.columns:
            target["fed_funds_rate"] = df["FEDFUNDS"]
        if "PCECC96" in df.columns:
            target["consumption_growth"] = self._annualised_growth_from_level(df["PCECC96"])
        if "PRFI" in df.columns:
            target["residential_inv_growth"] = self._annualised_growth_from_level(df["PRFI"])
        if "FCI" in df.columns:
            target["fci"] = df["FCI"]

        return target[self.config.variables].dropna(how="all")

    @staticmethod
    def _dataset_hash_token(obs_data: ObservedDataset) -> str:
        return f"{obs_data.frequency}:{obs_data.vintage.date()}:{obs_data.n_periods}"

    @staticmethod
    def _flatten_scorecard(prefix: str, scorecard: ForecastScorecard) -> Dict[str, float]:
        flat: Dict[str, float] = {
            f"{prefix}_overall_rmse": scorecard.overall_rmse,
            f"{prefix}_overall_mae": scorecard.overall_mae,
        }
        for score in scorecard.scores:
            score_dict = score.to_dict()
            variable = score_dict.pop("variable")
            for metric_name, metric_value in score_dict.items():
                flat[f"{prefix}_{variable}_{metric_name}"] = float(metric_value)
        return flat

    @staticmethod
    def _build_comparison_table(
        simulator_scorecards: Dict[str, ForecastScorecard],
        benchmark_scorecards: Dict[str, Dict[str, ForecastScorecard]],
    ) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []

        for origin, card in simulator_scorecards.items():
            for score in card.scores:
                rows.append({
                    "origin": origin,
                    "model": "us_macro_simulator",
                    **score.to_dict(),
                })

        for origin, model_cards in benchmark_scorecards.items():
            for model_name, card in model_cards.items():
                for score in card.scores:
                    rows.append({
                        "origin": origin,
                        "model": model_name,
                        **score.to_dict(),
                    })

        return pd.DataFrame(rows)
