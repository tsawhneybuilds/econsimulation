"""MCRunner: Monte Carlo forecast over multiple simulation paths."""
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
from src.forecasting.runners.us_runner import ForecastArtifact, USForecastRunner


QUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]


@dataclass
class MCForecastArtifact:
    run_id: str
    config_hash: str
    calibration_hash: str
    data_vintage_hash: str
    seed: int
    origin_quarter: str
    horizon: int
    n_sims: int
    point_forecasts: pd.DataFrame     # median across sims; index=PeriodIndex
    density_summaries: pd.DataFrame   # MultiIndex: (variable, quantile) x horizon
    all_paths: Dict[str, np.ndarray]  # variable → [n_sims × T] array
    runtime_seconds: float = 0.0


class MCRunner:
    """
    Monte Carlo runner: generates n_sims independent simulation paths
    and computes quantile forecasts.

    Each simulation draws a different random seed, so the stochastic
    shocks (ROW innovations, credit-market frictions, etc.) differ
    across paths.  The initial CalibrationBundle and state are shared
    across all paths (deep-copied before each run).

    Usage
    -----
    >>> mc = MCRunner()
    >>> artifact = mc.run(state, T=8, n_sims=200, seed=42)
    >>> artifact.density_summaries.loc[("gdp_growth", 0.50)]
    """

    VARIABLES = USForecastRunner.VARIABLES

    def __init__(self) -> None:
        self.engine = USMacroEngine()

    def run(
        self,
        state: SimulationState,
        T: int,
        n_sims: int = 100,
        seed: int = 42,
        shock: Optional[ShockProtocol] = None,
        config_hash: str = "",
        calibration_hash: str = "",
        data_vintage_hash: str = "",
    ) -> MCForecastArtifact:
        """
        Run n_sims independent paths and return quantile summaries.

        Parameters
        ----------
        state : SimulationState
            Initial state (deep-copied per simulation; never mutated).
        T : int
            Forecast horizon in quarters.
        n_sims : int
            Number of Monte Carlo draws.
        seed : int
            Master seed for reproducibility.  Per-simulation seeds are
            derived deterministically from this master.
        shock : ShockProtocol, optional
            Structural shock applied at each step (deep-copied per sim).

        Returns
        -------
        MCForecastArtifact
        """
        t0 = time.perf_counter()
        run_id = str(uuid.uuid4())[:8]

        if shock is None:
            shock = NoShock()

        origin = pd.Period(state.origin_quarter, freq="Q")
        idx = pd.period_range(start=origin + 1, periods=T, freq="Q")

        # Collect all paths: {variable: list of per-sim T-length lists}
        all_paths_raw: Dict[str, List[List[float]]] = {v: [] for v in self.VARIABLES}
        rng_master = np.random.default_rng(seed)

        for _sim_i in range(n_sims):
            sim_seed = int(rng_master.integers(0, 2**31))
            runner = USForecastRunner()
            sim_shock = copy.deepcopy(shock)

            artifact = runner.run(
                state=state,
                T=T,
                shock=sim_shock,
                seed=sim_seed,
                config_hash=config_hash,
                calibration_hash=calibration_hash,
                data_vintage_hash=data_vintage_hash,
            )

            for var in self.VARIABLES:
                if var in artifact.point_forecasts.columns:
                    all_paths_raw[var].append(
                        artifact.point_forecasts[var].tolist()
                    )
                else:
                    all_paths_raw[var].append([float("nan")] * T)

        # Convert to ndarray: shape [n_sims × T]
        path_arrays: Dict[str, np.ndarray] = {
            var: np.array(all_paths_raw[var])
            for var in self.VARIABLES
        }

        # Point forecasts = cross-simulation medians
        point_data: Dict[str, np.ndarray] = {}
        for var in self.VARIABLES:
            point_data[var] = np.nanmedian(path_arrays[var], axis=0)
        point_forecasts = pd.DataFrame(point_data, index=idx)

        # Density summaries: MultiIndex (variable, quantile) × quarter
        rows: List[Dict[str, Any]] = []
        for var in self.VARIABLES:
            arr = path_arrays[var]   # [n_sims × T]
            for q in QUANTILES:
                row_vals = np.nanquantile(arr, q, axis=0)
                for t_i, quarter in enumerate(idx):
                    rows.append({
                        "variable": var,
                        "quantile": q,
                        "quarter": str(quarter),
                        "value": row_vals[t_i],
                    })

        density_df = (
            pd.DataFrame(rows)
            .pivot_table(
                index=["variable", "quantile"],
                columns="quarter",
                values="value",
            )
        )

        t1 = time.perf_counter()

        return MCForecastArtifact(
            run_id=run_id,
            config_hash=config_hash,
            calibration_hash=calibration_hash,
            data_vintage_hash=data_vintage_hash,
            seed=seed,
            origin_quarter=state.origin_quarter,
            horizon=T,
            n_sims=n_sims,
            point_forecasts=point_forecasts,
            density_summaries=density_df,
            all_paths=path_arrays,
            runtime_seconds=t1 - t0,
        )
