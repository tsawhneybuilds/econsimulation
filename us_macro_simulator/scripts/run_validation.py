"""Validate a Julia Stage 1 artifact bundle and emit JSON/HTML reports."""
from __future__ import annotations

import argparse

from _helpers import REPO_ROOT, ensure_output_dir, load_cross_section_fixture
from src.forecasting.runners.backtest_runner import BacktestRunner
from src.julia_bundle import JuliaBundleBacktestEvaluator, load_bundle
from src.validation.harness import ValidationHarness
from src.validation.reports.html_report import write_html_report
from src.validation.reports.json_report import write_json_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-dir", required=True)
    parser.add_argument("--gates-config", default=str(REPO_ROOT / "configs" / "validation" / "gates.yaml"))
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    bundle = load_bundle(args.bundle_dir)
    backtest = JuliaBundleBacktestEvaluator(bundle).run()
    harness = ValidationHarness.from_yaml(args.gates_config)
    report = harness.run_bundle(
        bundle=bundle,
        backtest_result=backtest,
        observed_cross_section=load_cross_section_fixture(),
    )

    output_dir = ensure_output_dir(args.output_dir, "validation")
    json_path = write_json_report(report, output_dir / "validation_report.json")
    actuals = BacktestRunner(config=backtest.config)._to_target_variables(bundle.full_actuals_raw())
    html_path = write_html_report(
        report=report,
        backtest_result=backtest,
        actuals=actuals,
        output_dir=output_dir,
    )
    print(json_path)
    print(html_path)


if __name__ == "__main__":
    main()
