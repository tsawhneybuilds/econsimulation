"""Run the Stage 1 validation harness and emit JSON/HTML reports."""
from __future__ import annotations

import argparse

from _helpers import (
    REPO_ROOT,
    build_backtest_config,
    build_dataset_from_config,
    ensure_output_dir,
    load_cross_section_fixture,
)
from src.forecasting.runners.backtest_runner import BacktestRunner
from src.us.calibration import build_us_2019q4_calibration
from src.us.initialization import USInitializer
from src.validation.harness import ValidationHarness
from src.validation.reports.html_report import write_html_report
from src.validation.reports.json_report import write_json_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-config", default=str(REPO_ROOT / "configs" / "stage1" / "data.yaml"))
    parser.add_argument("--backtest-config", default=str(REPO_ROOT / "configs" / "stage1" / "backtest.yaml"))
    parser.add_argument("--gates-config", default=str(REPO_ROOT / "configs" / "validation" / "gates.yaml"))
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    dataset, _data_config = build_dataset_from_config(args.data_config)
    state = USInitializer().initialize(build_us_2019q4_calibration(), dataset, seed=42)
    backtest = BacktestRunner(config=build_backtest_config(args.backtest_config)).run()
    harness = ValidationHarness.from_yaml(args.gates_config)
    report = harness.run(
        dataset=dataset,
        initial_state=state,
        backtest_result=backtest,
        observed_cross_section=load_cross_section_fixture(),
    )

    output_dir = ensure_output_dir(args.output_dir, "validation")
    json_path = write_json_report(report, output_dir / "validation_report.json")
    html_path = write_html_report(
        report=report,
        backtest_result=backtest,
        actuals=BacktestRunner(config=build_backtest_config(args.backtest_config))._build_actuals(),
        output_dir=output_dir,
    )
    print(json_path)
    print(html_path)


if __name__ == "__main__":
    main()
