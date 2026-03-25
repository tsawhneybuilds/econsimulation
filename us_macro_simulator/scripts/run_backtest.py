"""Run the Stage 1 pseudo-real-time backtest."""
from __future__ import annotations

import argparse

from _helpers import REPO_ROOT, build_backtest_config, ensure_output_dir, save_backtest_artifacts
from src.forecasting.runners.backtest_runner import BacktestRunner


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(REPO_ROOT / "configs" / "stage1" / "backtest.yaml"))
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    result = BacktestRunner(config=build_backtest_config(args.config)).run()
    output_dir = ensure_output_dir(args.output_dir, "backtest")
    paths = save_backtest_artifacts(result, output_dir)
    print(paths["summary"])


if __name__ == "__main__":
    main()
