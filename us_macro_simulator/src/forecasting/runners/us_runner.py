"""USForecastRunner: run a full forecast and collect ForecastArtifact."""
from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.engine.core.engine import USMacroEngine
from src.engine.core.state import SimulationState
from src.engine.measurement.nipa_mapper import NIPAMapper, ObservableSnapshot
from src.engine.shocks.shock_protocol import ShockProtocol, NoShock
from src.utils.manifest import RunManifest


@dataclass
class ForecastArtifact:
    run_id: str
    config_hash: str
    calibration_hash: str
    data_vintage_hash: str
    seed: int
    origin_quarter: str
    horizon: int
    point_forecasts: pd.DataFrame    # index=quarter (PeriodIndex), cols=variables
    density_summaries: pd.DataFrame  # quantiles (same structure for single-path)
    validation_summary: Dict[str, Any]
    runtime_seconds: float = 0.0
    manifest: Optional[RunManifest] = None

    def get_variable(self, var: str) -> pd.Series:
        return self.point_forecasts[var]


class USForecastRunner:
    """
    Run a single deterministic forecast trajectory.

    Usage
    -----
    >>> runner = USForecastRunner()
    >>> artifact = runner.run(state, T=8, seed=42)
    >>> artifact.point_forecasts["gdp_growth"]
    """

    VARIABLES = [
        "gdp_growth",
        "cpi_inflation",
        "core_cpi_inflation",
        "unemployment_rate",
        "fed_funds_rate",
        "consumption_growth",
        "residential_inv_growth",
        "fci",
    ]

    def __init__(self) -> None:
        self.engine = USMacroEngine()

    def run(
        self,
        state: SimulationState,
        T: int,
        shock: Optional[ShockProtocol] = None,
        config_hash: str = "",
        calibration_hash: str = "",
        data_vintage_hash: str = "",
        seed: Optional[int] = None,
    ) -> ForecastArtifact:
        """
        Run T-step forecast from state, collecting observables each step.

        Parameters
        ----------
        state : SimulationState
            Initial state (deep-copied internally; caller's state is not mutated).
        T : int
            Forecast horizon in quarters.
        shock : ShockProtocol, optional
            Shock applied at each step.  Defaults to NoShock().
        seed : int, optional
            If provided, overrides the RNG seed in the copied state.

        Returns
        -------
        ForecastArtifact
        """
        t0 = time.perf_counter()
        run_id = str(uuid.uuid4())[:8]

        if shock is None:
            shock = NoShock()

        # Deep-copy state so we don't mutate the caller's state
        run_state = copy.deepcopy(state)
        if seed is not None:
            run_state.rng_state = np.random.default_rng(seed)

        mapper = NIPAMapper()
        snapshots: List[ObservableSnapshot] = []

        for _ in range(T):
            self.engine.step(run_state, shock=shock)
            snap = mapper.map(run_state)
            snapshots.append(snap)

        # Build point forecasts DataFrame
        origin = pd.Period(state.origin_quarter, freq="Q")
        idx = pd.period_range(start=origin + 1, periods=T, freq="Q")

        records = [s.to_dict() for s in snapshots]
        df = pd.DataFrame(records, index=idx)

        # Rename internal names → standard variable names
        rename = {
            "gdp_growth_qoq": "gdp_growth",
            "cpi_inflation_qoq": "cpi_inflation",
            "core_cpi_inflation_qoq": "core_cpi_inflation",
            "fed_funds_rate_annual": "fed_funds_rate",
            "consumption_growth_qoq": "consumption_growth",
            "residential_inv_growth_qoq": "residential_inv_growth",
        }
        df = df.rename(columns=rename)

        # Keep only target variables that are present
        available_vars = [v for v in self.VARIABLES if v in df.columns]
        point_forecasts = df[available_vars]

        # For a single deterministic path the density summary equals the
        # point forecast (no distributional information available).
        density_summaries = point_forecasts.copy()

        t1 = time.perf_counter()

        manifest = RunManifest(
            run_id=run_id,
            config_hash=config_hash,
            calibration_hash=calibration_hash,
            data_vintage_hash=data_vintage_hash,
            seed=seed if seed is not None else 42,
            origin_quarter=state.origin_quarter,
            horizon=T,
            mode="forecast",
        )

        return ForecastArtifact(
            run_id=run_id,
            config_hash=config_hash,
            calibration_hash=calibration_hash,
            data_vintage_hash=data_vintage_hash,
            seed=seed if seed is not None else 42,
            origin_quarter=state.origin_quarter,
            horizon=T,
            point_forecasts=point_forecasts,
            density_summaries=density_summaries,
            validation_summary={},
            runtime_seconds=t1 - t0,
            manifest=manifest,
        )
