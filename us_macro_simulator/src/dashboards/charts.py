"""Chart generation utilities for Stage 1 reports."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd

from src.forecasting.runners.backtest_runner import BacktestResult


def build_default_charts(
    backtest_result: BacktestResult,
    actuals: pd.DataFrame,
    output_dir: str | Path,
) -> Dict[str, str]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    charts = {}
    charts["rmse_by_model"] = str(_build_rmse_chart(backtest_result.comparison_table, output_root))
    charts["first_origin_gdp"] = str(_build_first_origin_chart(backtest_result, actuals, output_root))
    return charts


def _build_rmse_chart(comparison_table: pd.DataFrame, output_dir: Path) -> Path:
    grouped = comparison_table.groupby("model")["rmse"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(8, 4))
    grouped.plot(kind="bar", ax=ax, color="#446B7A")
    ax.set_title("Average RMSE By Model")
    ax.set_ylabel("RMSE")
    ax.set_xlabel("")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = output_dir / "rmse_by_model.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _build_first_origin_chart(
    backtest_result: BacktestResult,
    actuals: pd.DataFrame,
    output_dir: Path,
    variable: str = "gdp_growth",
) -> Path:
    first_origin = backtest_result.origins[0]
    artifact = backtest_result.artifacts[first_origin]
    forecast = artifact.point_forecasts[variable]
    actual_series = actuals.reindex(forecast.index)[variable]
    random_walk = backtest_result.benchmark_forecasts[first_origin]["random_walk"][variable]
    semi_structural = backtest_result.benchmark_forecasts[first_origin]["semi_structural"][variable]

    fig, ax = plt.subplots(figsize=(8, 4))
    forecast.plot(ax=ax, label="Simulator", linewidth=2.2, color="#AA3A2A")
    actual_series.plot(ax=ax, label="Actual", linewidth=2.0, color="#1B4D3E")
    random_walk.plot(ax=ax, label="Random Walk", linestyle="--", color="#7A6C5D")
    semi_structural.plot(ax=ax, label="Semi-Structural", linestyle=":", color="#2D5F9A")
    ax.set_title(f"{variable.replace('_', ' ').title()} Forecasts At {first_origin}")
    ax.set_ylabel(variable)
    ax.set_xlabel("Quarter")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path = output_dir / f"{variable}_{first_origin}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
