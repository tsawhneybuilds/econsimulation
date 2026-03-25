"""Export the existing U.S. fixture parquet to CSV for the Julia runner."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-tier", default="tier_b")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    fixture_path = repo_root / "data" / "fixtures" / f"{args.fixture_tier}_aggregate.parquet"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Missing fixture parquet: {fixture_path}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(fixture_path).copy()
    df.index = df.index.astype(str)
    df = df.reset_index(names="period")
    path = output_dir / f"{args.fixture_tier}_aggregate.csv"
    df.to_csv(path, index=False)
    print(path)


if __name__ == "__main__":
    main()
