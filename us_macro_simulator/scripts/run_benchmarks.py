"""Run Python benchmarks against a Julia Stage 1 artifact bundle."""
from __future__ import annotations

import argparse

from _helpers import REPO_ROOT, ensure_output_dir, save_backtest_artifacts
from src.julia_bundle import JuliaBundleBacktestEvaluator, load_bundle
from src.utils.serialization import save_artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-dir", required=True)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    bundle = load_bundle(args.bundle_dir)
    result = JuliaBundleBacktestEvaluator(bundle).run()
    output_dir = ensure_output_dir(args.output_dir, "benchmarks")
    path = output_dir / "benchmark_comparison.parquet"
    save_artifact(result.comparison_table, path)
    save_backtest_artifacts(result, output_dir)
    print(path)


if __name__ == "__main__":
    main()
