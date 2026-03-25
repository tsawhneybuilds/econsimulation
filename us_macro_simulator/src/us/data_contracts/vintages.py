"""VintageDataset: vintage timestamp, release-lag enforcement, leakage guard."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from .schema import SERIES_REGISTRY, SeriesMetadata


class VintageLeakageError(Exception):
    """Raised when data vintage would violate release-lag constraints."""


@dataclass
class VintageDataset:
    """A dataset associated with a specific vintage (data release) date."""
    vintage: datetime
    frequency: str
    data: pd.DataFrame          # index=date (PeriodIndex or DatetimeIndex), cols=series_id
    metadata: Dict[str, SeriesMetadata]

    def validate_no_leakage(self, as_of: datetime) -> None:
        """
        Ensure no series contains observations that would not yet have been
        released as of `as_of`, given its release_lag_quarters.
        """
        for series_id, meta in self.metadata.items():
            if series_id not in self.data.columns:
                continue
            lag_periods = meta.release_lag_quarters
            series = self.data[series_id].dropna()
            if series.empty:
                continue

            # Convert index to period end dates for comparison
            idx = self.data.index
            if hasattr(idx, 'to_timestamp'):
                end_dates = idx.to_timestamp(how='end')
            else:
                end_dates = pd.DatetimeIndex(idx)

            # Latest observation date in the series
            valid_mask = self.data[series_id].notna()
            if not valid_mask.any():
                continue
            latest_obs_idx = self.data[series_id][valid_mask].index[-1]

            if hasattr(latest_obs_idx, 'to_timestamp'):
                latest_obs_date = latest_obs_idx.to_timestamp(how='end')
            else:
                latest_obs_date = pd.Timestamp(latest_obs_idx)

            # Earliest date this observation would be released
            release_date = latest_obs_date + pd.DateOffset(months=3 * lag_periods)

            if release_date > pd.Timestamp(as_of):
                raise VintageLeakageError(
                    f"Series '{series_id}': observation at {latest_obs_idx} "
                    f"would only be released {release_date.date()}, "
                    f"but as_of={as_of.date()}. Vintage leakage detected."
                )

    def get_available_series(self, as_of: Optional[datetime] = None) -> pd.DataFrame:
        """Return data with NaN masking applied for lag-adjusted availability."""
        if as_of is None:
            return self.data.copy()

        result = self.data.copy()
        idx = result.index
        if hasattr(idx, 'to_timestamp'):
            end_dates = idx.to_timestamp(how='end')
        else:
            end_dates = pd.DatetimeIndex(idx)

        for series_id, meta in self.metadata.items():
            if series_id not in result.columns:
                continue
            lag_periods = meta.release_lag_quarters
            # Mask observations not yet released
            for i, end_date in enumerate(end_dates):
                release_date = end_date + pd.DateOffset(months=3 * lag_periods)
                if release_date > pd.Timestamp(as_of):
                    result.iloc[i, result.columns.get_loc(series_id)] = float('nan')

        return result
