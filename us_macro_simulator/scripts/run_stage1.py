"""Run the end-to-end Stage 1 pipeline in one command."""
from __future__ import annotations

import argparse

from _helpers import (
    REPO_ROOT,
    build_backtest_config,
    build_dataset_from_config,
    ensure_output_dir,
    load_cross_section_fixture,
    save_backtest_artifacts,
)
from src.forecasting.runners.backtest_runner import BacktestRunner
from src.us.calibration import build_us_2019q4_calibration
from src.us.initialization import USInitializer
from src.utils.serialization import save_artifact
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

    output_dir = ensure_output_dir(args.output_dir, "stage1")
    dataset, _data_config = build_dataset_from_config(args.data_config)
    save_artifact(dataset.data, output_dir / "observed_dataset.parquet")

    state = USInitializer().initialize(build_us_2019q4_calibration(), dataset, seed=42)
    backtest = BacktestRunner(config=build_backtest_config(args.backtest_config)).run()
    save_backtest_artifacts(backtest, output_dir)

    harness = ValidationHarness.from_yaml(args.gates_config)
    report = harness.run(
        dataset=dataset,
        initial_state=state,
        backtest_result=backtest,
        observed_cross_section=load_cross_section_fixture(),
    )
    json_path = write_json_report(report, output_dir / "validation_report.json")
    html_path = write_html_report(
        report=report,
        backtest_result=backtest,
        actuals=BacktestRunner(config=build_backtest_config(args.backtest_config))._build_actuals(),
        output_dir=output_dir,
    )
    print(output_dir)
    print(json_path)
    print(html_path)


if __name__ == "__main__":
    main()
