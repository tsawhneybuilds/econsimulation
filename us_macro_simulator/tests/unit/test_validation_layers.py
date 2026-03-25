"""Validation subsystem tests."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.forecasting.runners.backtest_runner import BacktestConfig, BacktestRunner
from src.us.calibration import build_us_2019q4_calibration
from src.us.data_contracts.build_dataset import DatasetBuilder
from src.us.initialization import USInitializer
from src.validation.harness import ValidationHarness
from src.validation.reports.html_report import write_html_report
from src.validation.reports.json_report import write_json_report


def test_validation_harness_runs(tmp_path):
    builder = DatasetBuilder()
    dataset = builder.build(
        {
            "source": "fixture",
            "frequency": "Q",
            "fixture_tier": "tier_a",
            "vintage_date": "2019-12-31",
            "mask_unavailable": True,
            "allow_leakage": False,
        },
    )
    state = USInitializer().initialize(build_us_2019q4_calibration(), dataset, seed=42)
    backtest = BacktestRunner(
        config=BacktestConfig(start_origin="2017Q1", end_origin="2017Q2", horizon=2)
    ).run()
    cross_section = pd.read_parquet(
        Path(__file__).parents[2] / "data" / "fixtures" / "tier_a_crosssection.parquet"
    )
    harness = ValidationHarness.from_yaml(Path(__file__).parents[2] / "configs" / "validation" / "gates.yaml")
    report = harness.run(
        dataset=dataset,
        initial_state=state,
        backtest_result=backtest,
        observed_cross_section=cross_section,
    )
    check_names = {check.name for check in report.checks}
    assert "vintage_leakage" in check_names
    assert "scorecards_present" in check_names
    json_path = write_json_report(report, tmp_path / "report.json")
    html_path = write_html_report(
        report=report,
        backtest_result=backtest,
        actuals=BacktestRunner(config=BacktestConfig(start_origin="2017Q1", end_origin="2017Q2", horizon=2))._build_actuals(),
        output_dir=tmp_path,
    )
    assert json_path.exists()
    assert html_path.exists()
