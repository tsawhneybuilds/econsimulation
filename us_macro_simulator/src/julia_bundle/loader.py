"""Load the Julia-generated Stage 1 artifact bundle."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd

from src.us.data_contracts.build_dataset import ObservedDataset
from src.us.data_contracts.loaders import build_metadata_map


FULL_ACTUALS_ORIGIN = "full_actuals"


@dataclass
class JuliaArtifactBundle:
    bundle_dir: Path
    manifest: Dict[str, Any]
    observed_dataset: pd.DataFrame
    simulator_forecasts: pd.DataFrame
    initial_measurements: Dict[str, Any]
    cross_section_summary: pd.DataFrame
    scenario_bundle: Dict[str, Any]

    @property
    def origins(self) -> list[str]:
        return list(self.manifest.get("origins", []))

    @property
    def variables(self) -> list[str]:
        return list(self.manifest.get("variables", []))

    def raw_history_for_origin(self, origin: str) -> pd.DataFrame:
        rows = self.observed_dataset.loc[self.observed_dataset["origin"] == origin].copy()
        if rows.empty:
            raise KeyError(f"Origin '{origin}' not present in observed_dataset.csv")
        rows["period"] = pd.PeriodIndex(rows["period"], freq="Q")
        rows = rows.set_index("period").drop(columns=["origin"])
        return rows.sort_index()

    def full_actuals_raw(self) -> pd.DataFrame:
        origin = self.manifest.get("observed_origin_label", FULL_ACTUALS_ORIGIN)
        return self.raw_history_for_origin(origin)

    def full_actuals_dataset(self) -> ObservedDataset:
        raw = self.full_actuals_raw()
        return ObservedDataset(
            vintage=datetime(2100, 1, 1),
            frequency="Q",
            data=raw,
            metadata=build_metadata_map(list(raw.columns)),
        )

    def forecast_matrix_for_origin(self, origin: str, value_col: str = "mean") -> pd.DataFrame:
        rows = self.simulator_forecasts.loc[self.simulator_forecasts["origin"] == origin].copy()
        if rows.empty:
            raise KeyError(f"Origin '{origin}' not present in simulator_forecasts.csv")
        pivot = rows.pivot(index="period", columns="variable", values=value_col)
        pivot.index = pd.PeriodIndex(pivot.index, freq="Q")
        return pivot.sort_index()

    def bundle_artifacts(self) -> Dict[str, str]:
        return {
            "manifest": str(self.bundle_dir / "manifest.json"),
            "observed_dataset": str(self.bundle_dir / "observed_dataset.csv"),
            "simulator_forecasts": str(self.bundle_dir / "simulator_forecasts.csv"),
            "initial_measurements": str(self.bundle_dir / "initial_measurements.json"),
            "cross_section_summary": str(self.bundle_dir / "cross_section_summary.csv"),
            "scenario_bundle": str(self.bundle_dir / "scenario_bundle.json"),
        }


def _require_files(bundle_dir: Path, files: Iterable[str]) -> None:
    missing = [name for name in files if not (bundle_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Bundle is missing required files: {missing}")


def load_bundle(bundle_dir: str | Path) -> JuliaArtifactBundle:
    root = Path(bundle_dir)
    _require_files(
        root,
        [
            "manifest.json",
            "observed_dataset.csv",
            "simulator_forecasts.csv",
            "initial_measurements.json",
            "cross_section_summary.csv",
            "scenario_bundle.json",
        ],
    )

    manifest = json.loads((root / "manifest.json").read_text())
    observed_dataset = pd.read_csv(root / "observed_dataset.csv")
    simulator_forecasts = pd.read_csv(root / "simulator_forecasts.csv")
    initial_measurements = json.loads((root / "initial_measurements.json").read_text())
    cross_section_summary = pd.read_csv(root / "cross_section_summary.csv")
    scenario_bundle = json.loads((root / "scenario_bundle.json").read_text())

    return JuliaArtifactBundle(
        bundle_dir=root,
        manifest=manifest,
        observed_dataset=observed_dataset,
        simulator_forecasts=simulator_forecasts,
        initial_measurements=initial_measurements,
        cross_section_summary=cross_section_summary,
        scenario_bundle=scenario_bundle,
    )
