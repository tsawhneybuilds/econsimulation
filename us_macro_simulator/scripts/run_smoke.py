"""Run a single deterministic Stage 1 forecast."""
from __future__ import annotations

import argparse

from _helpers import REPO_ROOT, build_dataset_from_config, ensure_output_dir
from src.forecasting.runners.us_runner import USForecastRunner
from src.us.calibration import build_us_2019q4_calibration
from src.us.initialization import USInitializer
from src.utils.serialization import save_artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-config", default=str(REPO_ROOT / "configs" / "stage1" / "data.yaml"))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset, _config = build_dataset_from_config(args.data_config)
    state = USInitializer().initialize(build_us_2019q4_calibration(), dataset, seed=args.seed)
    artifact = USForecastRunner().run(state, T=args.horizon, seed=args.seed)

    output_dir = ensure_output_dir(args.output_dir, "smoke")
    path = output_dir / "forecast.parquet"
    save_artifact(artifact.point_forecasts, path)
    print(path)


if __name__ == "__main__":
    main()
