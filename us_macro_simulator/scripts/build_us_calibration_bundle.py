"""Build a Julia-facing U.S. calibration bundle from observed macro data."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from _helpers import REPO_ROOT
from src.us.calibration import build_bootstrap_bundle_from_observed


def _load_observed_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path).copy()
    if "period" not in df.columns:
        first = df.columns[0]
        df = df.rename(columns={first: "period"})
    df["period"] = df["period"].astype(str)
    return df


def _load_fixture_tier(tier: str) -> pd.DataFrame:
    fixture_path = REPO_ROOT / "data" / "fixtures" / f"{tier}_aggregate.parquet"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Missing fixture parquet: {fixture_path}")
    df = pd.read_parquet(fixture_path).copy()
    df.index = df.index.astype(str)
    return df.reset_index(names="period")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--aggregate-csv", default="")
    parser.add_argument("--fixture-tier", default="tier_b")
    parser.add_argument("--reference-quarter", default="2019Q4")
    parser.add_argument("--sector-count", type=int, default=62)
    parser.add_argument("--source-mode", default="bootstrap")
    args = parser.parse_args()

    observed = (
        _load_observed_csv(args.aggregate_csv)
        if args.aggregate_csv
        else _load_fixture_tier(args.fixture_tier)
    )
    bundle_dir = build_bootstrap_bundle_from_observed(
        observed,
        args.output_dir,
        reference_quarter=args.reference_quarter,
        sector_count=args.sector_count,
        source_mode=args.source_mode,
    )
    print(bundle_dir)


if __name__ == "__main__":
    main()

