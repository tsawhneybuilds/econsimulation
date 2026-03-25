"""End-to-end test for the Stage 1 CLI pipeline."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


def test_run_stage1_pipeline(tmp_path):
    repo_root = Path(__file__).parents[2]
    backtest_config = {
        "origins": {"start": "2017Q1", "end": "2017Q2"},
        "horizon": 2,
        "fixture_tier": "tier_b",
        "metrics": ["rmse", "mae"],
        "variables": [
            "gdp_growth",
            "cpi_inflation",
            "unemployment_rate",
            "fed_funds_rate",
        ],
    }
    backtest_path = tmp_path / "backtest.yaml"
    backtest_path.write_text(yaml.safe_dump(backtest_config))

    output_dir = tmp_path / "stage1_output"
    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_stage1.py"),
            "--data-config",
            str(repo_root / "configs" / "stage1" / "data.yaml"),
            "--backtest-config",
            str(backtest_path),
            "--gates-config",
            str(repo_root / "configs" / "validation" / "gates.yaml"),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        cwd=repo_root,
    )

    assert (output_dir / "observed_dataset.parquet").exists()
    assert (output_dir / "backtest_forecasts.parquet").exists()
    assert (output_dir / "comparison_table.parquet").exists()
    assert (output_dir / "validation_report.json").exists()
    assert (output_dir / "validation_report.html").exists()
