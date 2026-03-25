"""DatasetBuilder: builds ObservedDataset from config and vintage date."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import yaml

from .loaders import load_fixture, build_metadata_map
from .schema import SERIES_REGISTRY, SeriesMetadata
from .vintages import VintageDataset


@dataclass
class ObservedDataset:
    """Processed, validated dataset ready for use in calibration/initialization."""
    vintage: datetime
    frequency: str
    data: pd.DataFrame          # index=PeriodIndex(freq=frequency), cols=series_id
    metadata: Dict[str, SeriesMetadata]

    def __post_init__(self):
        if not isinstance(self.data.index, pd.PeriodIndex):
            # Attempt conversion
            self.data.index = pd.PeriodIndex(self.data.index, freq=self.frequency)

    @property
    def series_ids(self) -> list[str]:
        return list(self.data.columns)

    @property
    def n_periods(self) -> int:
        return len(self.data)

    def get_series(self, series_id: str) -> pd.Series:
        if series_id not in self.data.columns:
            raise KeyError(f"Series '{series_id}' not in dataset")
        return self.data[series_id]

    def latest_period(self, series_id: str | None = None) -> pd.Period | None:
        """Return the latest period with data."""
        if self.data.empty:
            return None

        if series_id is None:
            non_empty_rows = self.data.dropna(how="all")
            if non_empty_rows.empty:
                return None
            return non_empty_rows.index[-1]

        series = self.get_series(series_id).dropna()
        if series.empty:
            return None
        return series.index[-1]

    def latest_value(self, series_id: str, default: float | None = None) -> float | None:
        """Return the most recent non-null value for *series_id*."""
        series = self.get_series(series_id).dropna()
        if series.empty:
            return default
        return float(series.iloc[-1])

    def latest_snapshot(self, series_ids: list[str]) -> Dict[str, float | None]:
        """Return latest non-null values for a list of series IDs."""
        return {series_id: self.latest_value(series_id) for series_id in series_ids}


class DatasetBuilder:
    """Builds ObservedDataset from config and optional vintage date."""

    FIXTURE_DIR = Path(__file__).parents[4] / "data" / "fixtures"

    def build(
        self,
        config: Dict[str, Any],
        vintage_date: Optional[datetime] = None,
    ) -> ObservedDataset:
        source = config.get("source", "fixture")
        frequency = config.get("frequency", "Q")
        series_ids = config.get("series", list(SERIES_REGISTRY.keys()))

        if vintage_date is None:
            vd_str = config.get("vintage_date", "2019-12-31")
            vintage_date = datetime.fromisoformat(vd_str)

        if source == "fixture":
            tier = config.get("fixture_tier", "tier_a")
            df = self._load_fixture(tier, series_ids)
        elif source == "fred":
            df = self._load_fred(config, series_ids, vintage_date)
        else:
            raise ValueError(f"Unknown data source: {source}")

        # Ensure PeriodIndex
        if not isinstance(df.index, pd.PeriodIndex):
            df.index = pd.PeriodIndex(df.index, freq=frequency)

        # Build metadata
        metadata = build_metadata_map(series_ids)

        mask_unavailable = config.get("mask_unavailable", True)
        allow_leakage = config.get("allow_leakage", False)
        vintage_dataset = VintageDataset(
            vintage=vintage_date,
            frequency=frequency,
            data=df.copy(),
            metadata=metadata,
        )

        if mask_unavailable:
            df = vintage_dataset.get_available_series(as_of=vintage_date)
            if isinstance(df.index, pd.PeriodIndex):
                cutoff_period = pd.Period(vintage_date, freq=frequency)
                df = df.loc[df.index <= cutoff_period]
            df = df.dropna(how="all")
            vintage_dataset = VintageDataset(
                vintage=vintage_date,
                frequency=frequency,
                data=df.copy(),
                metadata=metadata,
            )

        obs = ObservedDataset(
            vintage=vintage_date,
            frequency=frequency,
            data=df,
            metadata=metadata,
        )

        # Validate vintage (leakage check)
        if not allow_leakage:
            vintage_dataset.validate_no_leakage(vintage_date)

        return obs

    def _load_fixture(self, tier: str, series_ids: list[str]) -> pd.DataFrame:
        fixture_name = f"{tier}_aggregate.parquet"
        fixture_path = self.FIXTURE_DIR / fixture_name
        if not fixture_path.exists():
            # Generate synthetic fixture on the fly
            from ..data_contracts import _generate_synthetic_fixture
            return _generate_synthetic_fixture(tier, series_ids)
        return load_fixture(fixture_path, series_ids)

    def _load_fred(
        self,
        config: Dict[str, Any],
        series_ids: list[str],
        vintage_date: datetime,
    ) -> pd.DataFrame:
        """Fetch live data from the FRED API.

        Replaces the old CSV-directory stub.  Requires the ``requests``
        package and a FRED API key (free at fred.stlouisfed.org).

        Config keys consumed
        --------------------
        fred_api_key : str, optional
            FRED API key.  Preferred: set the ``FRED_API_KEY`` env var instead
            of hardcoding the key in a config file.
        start_date : str, optional
            ISO date for the earliest observation.  Defaults to "1990-01-01".
        """
        from .fred_loader import FREDLiveLoader

        loader = FREDLiveLoader(
            api_key=config.get("fred_api_key"),   # falls back to FRED_API_KEY env
            vintage_date=vintage_date,
            start_date=config.get("start_date", "1990-01-01"),
        )
        return loader.load(series_ids)


def _generate_synthetic_fixture(tier: str, series_ids: list[str]) -> pd.DataFrame:
    """Generate minimal synthetic fixture with known accounting identities."""
    rng = np.random.default_rng(42)
    periods = pd.period_range("2015Q1", "2019Q4", freq="Q")
    n = len(periods)

    data = {}

    # GDP level (billions 2017 USD, SAAR)
    gdp_base = 19_000.0
    gdp_growth = rng.normal(0.005, 0.003, n)
    gdp_level = gdp_base * np.cumprod(1 + gdp_growth)
    data["GDPC1"] = gdp_level
    data["GDPC1_GROWTH"] = gdp_growth * 400  # annualised pct

    # CPI (index, 1982-84=100)
    cpi_base = 255.0
    cpi_infl = rng.normal(0.005, 0.002, n)
    data["CPIAUCSL"] = cpi_base * np.cumprod(1 + cpi_infl)
    data["CPILFESL"] = cpi_base * 0.98 * np.cumprod(1 + rng.normal(0.004, 0.001, n))

    # Unemployment rate (%)
    data["UNRATE"] = np.clip(rng.normal(3.7, 0.3, n), 2.0, 15.0)

    # Fed funds rate (%)
    data["FEDFUNDS"] = np.clip(rng.normal(2.2, 0.4, n), 0.0, 10.0)

    # PCE (levels, billions 2017 USD, SAAR)
    pce_share = 0.68
    data["PCECC96"] = gdp_level * pce_share * (1 + rng.normal(0, 0.005, n))

    # Residential investment (billions 2017 USD, SAAR)
    resid_share = 0.05
    data["PRFI"] = gdp_level * resid_share * (1 + rng.normal(0, 0.02, n))

    # FCI (index, 0=neutral)
    data["FCI"] = rng.normal(0.0, 0.3, n)

    df = pd.DataFrame(data, index=periods)
    return df[series_ids] if all(s in df.columns for s in series_ids) else df
