"""Shared helpers for Stage 1 scripts."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.forecasting.runners.backtest_runner import BacktestConfig, BacktestResult
from src.us.data_contracts.build_dataset import DatasetBuilder, ObservedDataset
from src.utils.serialization import save_artifact
from src.validation.models import ValidationCheck, ValidationReport


def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path) as handle:
        return yaml.safe_load(handle)


def ensure_output_dir(path: str | Path | None, stem: str) -> Path:
    if path is not None:
        output_dir = Path(path)
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = REPO_ROOT / "outputs" / f"{stem}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_dataset_from_config(
    config_path: str | Path,
    vintage_date: datetime | None = None,
) -> tuple[ObservedDataset, Dict[str, Any]]:
    config = load_yaml(config_path)
    if vintage_date is None:
        vintage_date = datetime.fromisoformat(config["vintage_date"])
    builder = DatasetBuilder()
    dataset = builder.build(
        {
            "source": config.get("source", "fixture"),
            "frequency": config.get("frequency", "Q"),
            "fixture_tier": config.get("fixture_tier", "tier_a"),
            "series": config.get("series"),
            "vintage_date": vintage_date.date().isoformat(),
            "mask_unavailable": config.get("mask_unavailable", True),
            "allow_leakage": config.get("allow_leakage", False),
            "fred_api_key": config.get("fred_api_key"),
            "start_date": config.get("start_date", "1990-01-01"),
        },
        vintage_date=vintage_date,
    )
    return dataset, config


def build_backtest_config(config_path: str | Path) -> BacktestConfig:
    import os
    config = load_yaml(config_path)
    return BacktestConfig(
        start_origin=config["origins"]["start"],
        end_origin=config["origins"]["end"],
        horizon=int(config["horizon"]),
        fixture_tier=config.get("fixture_tier", "tier_b"),
        data_source=config.get("data_source", "fixture"),
        fred_api_key=config.get("fred_api_key") or os.environ.get("FRED_API_KEY"),
        variables=config.get("variables") or BacktestConfig().variables,
        benchmark_names=config.get("benchmark_names") or BacktestConfig().benchmark_names,
    )


def load_cross_section_fixture(path: str | Path | None = None) -> pd.DataFrame:
    cross_path = Path(path) if path is not None else REPO_ROOT / "data" / "fixtures" / "tier_a_crosssection.parquet"
    return pd.read_parquet(cross_path)


def save_backtest_artifacts(result: BacktestResult, output_dir: str | Path) -> Dict[str, str]:
    output_root = Path(output_dir)
    paths = {
        "forecasts": str(output_root / "backtest_forecasts.parquet"),
        "comparison": str(output_root / "comparison_table.parquet"),
        "summary": str(output_root / "backtest_summary.json"),
    }
    save_artifact(result.to_dataframe(), paths["forecasts"])
    save_artifact(result.comparison_table, paths["comparison"])

    summary = {
        "origins": result.origins,
        "runtime_seconds": result.runtime_seconds,
        "notes": result.notes,
        "scorecards": result.scorecards,
    }
    Path(paths["summary"]).write_text(json.dumps(summary, indent=2))
    return paths


def validation_report_from_dict(data: Dict[str, Any]) -> ValidationReport:
    checks = [ValidationCheck(**check) for check in data.get("checks", [])]
    return ValidationReport(
        run_id=data["run_id"],
        overall_passed=bool(data["overall_passed"]),
        checks=checks,
        summary=data.get("summary", {}),
        artifacts=data.get("artifacts", {}),
        notes=data.get("notes", []),
        generated_at=data.get("generated_at", ""),
    )
