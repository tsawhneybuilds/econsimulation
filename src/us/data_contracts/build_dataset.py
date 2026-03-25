"""Build a vintage-aware observed dataset artifact."""
from __future__ import annotations

import argparse
from datetime import datetime

from _helpers import REPO_ROOT, build_dataset_from_config, ensure_output_dir
from src.utils.serialization import save_artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(REPO_ROOT / "configs" / "stage1" / "data.yaml"))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--vintage-date", default=None)
    args = parser.parse_args()

    vintage = datetime.fromisoformat(args.vintage_date) if args.vintage_date else None
    dataset, _config = build_dataset_from_config(args.config, vintage_date=vintage)
    output_dir = ensure_output_dir(args.output_dir, "dataset")
    path = output_dir / "observed_dataset.parquet"
    save_artifact(dataset.data, path)
    print(path)


if __name__ == "__main__":
    main()
