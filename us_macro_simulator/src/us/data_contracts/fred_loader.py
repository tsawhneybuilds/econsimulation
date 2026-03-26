"""
FRED live data fetcher for the Stage 1 data contracts layer.

File: src/us/data_contracts/fred_loader.py

This module replaces the CSV-stub in DatasetBuilder._load_fred() with a live
FRED API client.  It is designed to be a drop-in: it accepts the same
series_ids drawn from SERIES_REGISTRY and returns a pd.DataFrame with a
quarterly PeriodIndex and those IDs as column names — exactly what
DatasetBuilder.build() expects before it creates a VintageDataset.

FRED series map
---------------
Internal ID     FRED series        Source frequency   Transform
-----------     -----------        ----------------   ---------
GDPC1           GDPC1              Q                  level (bn 2017 USD SAAR)
GDPC1_GROWTH    A191RL1Q225SBEA    Q                  level (QoQ ann %, BEA)
CPIAUCSL        CPIAUCSL           M → Q              quarterly mean of index
CPILFESL        CPILFESL           M → Q              quarterly mean of index
UNRATE          UNRATE             M → Q              quarterly mean (%)
FEDFUNDS        FEDFUNDS           M → Q              quarterly mean (%)
PCECC96         PCECC96            Q                  level (bn 2017 USD SAAR)
PRFI            PRFIA              Q                  level (bn 2017 USD SAAR)
FCI             NFCI               W → Q              quarterly mean (z-score)
TB3MS           TB3MS              M → Q              quarterly mean (%)
GS10            GS10               M → Q              quarterly mean (%)

Any series_id passed in that is not in the map is silently skipped (matching
the old CSV-stub behaviour where a missing file meant a missing column).
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapping: internal series_id → (fred_series_id, source_freq, transform)
# ---------------------------------------------------------------------------
# transform options:
#   "level"           – use as-is after quarterly resampling
#   "quarterly_mean"  – take quarterly mean (same result as level for Q series)
#   "qoq_ann"         – 100 * (X_t/X_{t-1} - 1) * 4  annualised QoQ growth
# ---------------------------------------------------------------------------
_MAP: Dict[str, Tuple[str, str, str]] = {
    # (fred_id, source_freq, transform)
    "GDPC1":        ("GDPC1",           "Q", "level"),
    "GDPC1_GROWTH": ("A191RL1Q225SBEA", "Q", "level"),   # BEA publishes SAAR %
    "CPIAUCSL":     ("CPIAUCSL",        "M", "quarterly_mean"),
    "CPILFESL":     ("CPILFESL",        "M", "quarterly_mean"),
    "UNRATE":       ("UNRATE",          "M", "quarterly_mean"),
    "FEDFUNDS":     ("FEDFUNDS",        "M", "quarterly_mean"),
    "PCECC96":      ("PCECC96",         "Q", "level"),
    "PRFI":         ("PRFI",            "Q", "level"),
    "FCI":          ("NFCI",            "W", "quarterly_mean"),
    "TB3MS":        ("TB3MS",           "M", "quarterly_mean"),
    "GS10":         ("GS10",            "M", "quarterly_mean"),
    "GDPDEF":       ("GDPDEF",          "Q", "level"),
    "PNFIC1":       ("PNFIC1",          "Q", "level"),
    "HOANBS":       ("HOANBS",          "Q", "level"),
    "CES0500000003": ("CES0500000003",  "M", "quarterly_mean"),
}

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


class FREDLiveLoader:
    """Fetch FRED series and return a quarterly PeriodIndex DataFrame.

    Parameters
    ----------
    api_key:
        FRED API key.  Falls back to the ``FRED_API_KEY`` environment
        variable.  Free key: https://fred.stlouisfed.org/docs/api/api_key.html
    vintage_date:
        Hard ceiling for observations.  Passed as ``observation_end`` and
        ``realtime_end`` to pin the vintage exactly.
    start_date:
        Earliest date to request.  Default "1990-01-01".
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        vintage_date: Optional[datetime | date | str] = None,
        start_date: str = "1990-01-01",
    ) -> None:
        self.api_key = api_key or os.environ.get("FRED_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "FRED API key required.  Pass api_key= or set FRED_API_KEY.\n"
                "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
            )
        self.vintage_date: date = _coerce_date(vintage_date or date.today())
        self.start_date = start_date

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def load(self, series_ids: List[str]) -> pd.DataFrame:
        """Fetch *series_ids* from FRED and return a quarterly DataFrame.

        Columns that are not in the FRED map are skipped with a warning.
        The returned DataFrame has a quarterly ``PeriodIndex`` (freq="Q").
        """
        try:
            import requests  # noqa: F401 – presence check
        except ImportError as exc:
            raise ImportError(
                "The 'requests' package is required for FRED live loading.\n"
                "Run: pip install requests"
            ) from exc

        frames: Dict[str, pd.Series] = {}
        unmapped: List[str] = []

        for sid in series_ids:
            if sid not in _MAP:
                unmapped.append(sid)
                continue
            fred_id, src_freq, transform = _MAP[sid]
            log.info("FRED fetch: %s → internal id %s", fred_id, sid)
            try:
                raw = self._fetch_series(fred_id)
                q = self._to_quarterly(raw, src_freq, transform)
                frames[sid] = q
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to fetch %s (%s): %s — skipping", sid, fred_id, exc)

        if unmapped:
            log.warning(
                "series_ids not in FRED map (skipped): %s\n"
                "Add them to _MAP in fred_loader.py if needed.",
                unmapped,
            )

        if not frames:
            raise RuntimeError(
                f"No series could be loaded from FRED for ids: {series_ids}"
            )

        df = pd.concat(frames, axis=1)
        df = df.sort_index()

        # Ensure PeriodIndex
        if not isinstance(df.index, pd.PeriodIndex):
            df.index = pd.PeriodIndex(df.index, freq="Q")

        # Belt-and-suspenders vintage mask
        cutoff = pd.Period(self.vintage_date, freq="Q")
        df = df.loc[df.index <= cutoff]

        log.info(
            "FRED dataset ready: %d quarters × %d series  (%s → %s)",
            len(df),
            len(df.columns),
            df.index[0] if len(df) else "n/a",
            df.index[-1] if len(df) else "n/a",
        )
        return df

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_series(self, fred_id: str) -> pd.Series:
        import requests

        params = {
            "series_id": fred_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": self.start_date,
            "observation_end": self.vintage_date.isoformat(),
            # realtime_end pins the vintage — prevents post-vintage revisions
            # from leaking in, which is critical for backtest integrity.
            "realtime_end": self.vintage_date.isoformat(),
        }
        resp = requests.get(FRED_BASE, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        if "observations" not in payload:
            raise RuntimeError(f"Unexpected FRED response for {fred_id}: {payload}")

        records = [
            (obs["date"], float(obs["value"]))
            for obs in payload["observations"]
            if obs["value"] not in (".", "")
        ]
        if not records:
            raise RuntimeError(f"Zero observations returned for {fred_id}")

        dates, values = zip(*records)
        s = pd.Series(list(values), index=pd.to_datetime(list(dates)), name=fred_id)
        return s[~s.index.duplicated(keep="last")].sort_index()

    @staticmethod
    def _to_quarterly(raw: pd.Series, src_freq: str, transform: str) -> pd.Series:
        """Resample *raw* to quarterly and apply *transform*."""
        # Resample sub-quarterly series to Q-end
        if src_freq in ("M", "W", "D"):
            q = raw.resample("QE").mean()
        else:
            # Already quarterly — normalise to period-end timestamps
            q = raw.copy()
            q.index = pd.PeriodIndex(q.index.to_period("Q")).to_timestamp("Q")

        if transform in ("level", "quarterly_mean"):
            result = q
        elif transform == "qoq_ann":
            result = 100.0 * (q / q.shift(1) - 1.0) * 4.0
        else:
            raise ValueError(f"Unknown transform: {transform!r}")

        # Convert to PeriodIndex to match ObservedDataset contract
        result.index = pd.PeriodIndex(result.index.to_period("Q"))
        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce_date(d: datetime | date | str) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        return date.fromisoformat(d)
    return d
