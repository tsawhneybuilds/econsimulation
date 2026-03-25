"""Run backtest and persist benchmark comparison outputs."""
from __future__ import annotations

import argparse

from _helpers import REPO_ROOT, build_backtest_config, ensure_output_dir
from src.forecasting.runners.backtest_runner import BacktestRunner
from src.utils.serialization import save_artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(REPO_ROOT / "configs" / "stage1" / "backtest.yaml"))
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    result = BacktestRunner(config=build_backtest_config(args.config)).run()
    output_dir = ensure_output_dir(args.output_dir, "benchmarks")
    path = output_dir / "benchmark_comparison.parquet"
    save_artifact(result.comparison_table, path)
    print(path)


if __name__ == "__main__":
    main()
