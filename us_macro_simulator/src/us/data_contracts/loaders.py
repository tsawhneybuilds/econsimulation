"""Data loaders: FRED CSV and synthetic fixtures."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .schema import SERIES_REGISTRY, SeriesMetadata


def load_fred_csv(path: Path, series_id: str) -> pd.Series:
    """Load a FRED-format CSV (DATE, VALUE columns) and return a quarterly Series."""
    df = pd.read_csv(path, parse_dates=["DATE"], index_col="DATE")
    if "VALUE" not in df.columns:
        # Try the series_id as column name
        if series_id in df.columns:
            series = df[series_id]
        else:
            series = df.iloc[:, 0]
    else:
        series = df["VALUE"]

    series.name = series_id
    series = series.replace(".", float("nan")).astype(float)
    return series


def load_fixture(
    path: Path,
    series_ids: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Load a Parquet fixture file and optionally select columns."""
    df = pd.read_parquet(path)
    if series_ids is not None:
        available = [s for s in series_ids if s in df.columns]
        missing = [s for s in series_ids if s not in df.columns]
        if missing:
            import warnings
            warnings.warn(f"Series not in fixture: {missing}")
        df = df[available]
    return df


def build_metadata_map(series_ids: list[str]) -> Dict[str, SeriesMetadata]:
    """Build metadata dict from SERIES_REGISTRY for given series IDs."""
    return {
        sid: SERIES_REGISTRY[sid].metadata
        for sid in series_ids
        if sid in SERIES_REGISTRY
    }
