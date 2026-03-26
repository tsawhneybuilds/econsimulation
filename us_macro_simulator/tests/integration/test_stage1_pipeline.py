"""End-to-end test for the Julia-first Stage 1 pipeline."""
from __future__ import annotations

import subprocess
from pathlib import Path


def test_run_stage1_pipeline(tmp_path):
    repo_root = Path(__file__).parents[3]
    output_dir = tmp_path / "stage1_output"
    subprocess.run(
        [
            str(repo_root / "scripts" / "run_stage1.sh"),
            "--output-dir",
            str(output_dir),
            "--start-origin",
            "2017Q1",
            "--end-origin",
            "2017Q1",
            "--horizon",
            "1",
            "--n-sims",
            "1",
        ],
        check=True,
        cwd=repo_root,
    )

    assert (output_dir / "julia_bundle" / "observed_dataset.csv").exists()
    assert (output_dir / "julia_bundle" / "simulator_forecasts.csv").exists()
    assert (output_dir / "julia_bundle" / "manifest.json").exists()
    assert (output_dir / "inputs" / "calibration_bundle" / "manifest.json").exists()
    assert (output_dir / "inputs" / "calibration_bundle" / "calibration.json").exists()
    assert (output_dir / "backtest_forecasts.parquet").exists()
    assert (output_dir / "comparison_table.parquet").exists()
    assert (output_dir / "validation_report.json").exists()
    assert (output_dir / "validation_report.html").exists()
