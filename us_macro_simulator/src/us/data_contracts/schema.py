"""Series schema and registry for U.S. macro data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal


@dataclass(frozen=True)
class SeriesMetadata:
    series_id: str
    description: str
    units: str  # "SAAR_BN_USD", "PCT", "FRAC", "THOUSANDS", "INDEX"
    frequency: str  # "Q", "M", "A"
    release_lag_quarters: int
    transform: str  # "level", "pct_change", "log_diff", "none"
    source: str = "FRED"
    seasonal_adjustment: str = "SA"
    release_calendar_key: str | None = None


@dataclass(frozen=True)
class SeriesSchema:
    metadata: SeriesMetadata
    dtype: str = "float64"
    allow_negative: bool = True
    min_value: float | None = None
    max_value: float | None = None
    expected_freq: str = "Q"


# ──────────────────────────────────────────────────────────────
# SERIES REGISTRY  (series_id → SeriesSchema)
# ──────────────────────────────────────────────────────────────

SERIES_REGISTRY: Dict[str, SeriesSchema] = {
    "GDPC1": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="GDPC1",
            description="Real Gross Domestic Product",
            units="SAAR_BN_2017_USD",
            frequency="Q",
            release_lag_quarters=1,
            transform="pct_change",
        ),
        dtype="float64",
        allow_negative=False,
        min_value=0.0,
    ),
    "GDPC1_GROWTH": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="GDPC1_GROWTH",
            description="Real GDP Growth Rate (QoQ annualised)",
            units="PCT",
            frequency="Q",
            release_lag_quarters=1,
            transform="none",
        ),
        dtype="float64",
    ),
    "CPIAUCSL": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="CPIAUCSL",
            description="Consumer Price Index for All Urban Consumers",
            units="INDEX_1982_84",
            frequency="M",
            release_lag_quarters=0,
            transform="pct_change",
        ),
        dtype="float64",
        allow_negative=False,
        min_value=0.0,
    ),
    "CPILFESL": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="CPILFESL",
            description="CPI Less Food and Energy (Core CPI)",
            units="INDEX_1982_84",
            frequency="M",
            release_lag_quarters=0,
            transform="pct_change",
        ),
        dtype="float64",
        allow_negative=False,
        min_value=0.0,
    ),
    "UNRATE": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="UNRATE",
            description="Unemployment Rate",
            units="PCT",
            frequency="M",
            release_lag_quarters=0,
            transform="none",
        ),
        dtype="float64",
        min_value=0.0,
        max_value=100.0,
    ),
    "FEDFUNDS": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="FEDFUNDS",
            description="Effective Federal Funds Rate",
            units="PCT",
            frequency="M",
            release_lag_quarters=0,
            transform="none",
        ),
        dtype="float64",
        min_value=0.0,
    ),
    "PCECC96": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="PCECC96",
            description="Real Personal Consumption Expenditures",
            units="SAAR_BN_2017_USD",
            frequency="Q",
            release_lag_quarters=1,
            transform="pct_change",
        ),
        dtype="float64",
        allow_negative=False,
        min_value=0.0,
    ),
    "PRFI": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="PRFI",
            description="Real Private Residential Fixed Investment",
            units="SAAR_BN_2017_USD",
            frequency="Q",
            release_lag_quarters=1,
            transform="pct_change",
        ),
        dtype="float64",
        allow_negative=False,
        min_value=0.0,
    ),
    "FCI": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="FCI",
            description="Financial Conditions Index (proxy)",
            units="INDEX",
            frequency="Q",
            release_lag_quarters=0,
            transform="none",
            release_calendar_key="fred_weekly",
        ),
        dtype="float64",
    ),
    "TB3MS": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="TB3MS",
            description="3-Month Treasury Bill Secondary Market Rate",
            units="PCT",
            frequency="M",
            release_lag_quarters=0,
            transform="none",
            release_calendar_key="fred_monthly",
        ),
        dtype="float64",
        min_value=0.0,
    ),
    "GS10": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="GS10",
            description="10-Year Treasury Constant Maturity Rate",
            units="PCT",
            frequency="M",
            release_lag_quarters=0,
            transform="none",
            release_calendar_key="fred_monthly",
        ),
        dtype="float64",
        min_value=0.0,
    ),
    "GDPDEF": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="GDPDEF",
            description="Gross Domestic Product Implicit Price Deflator",
            units="INDEX_2017_100",
            frequency="Q",
            release_lag_quarters=1,
            transform="pct_change",
            release_calendar_key="fred_quarterly",
        ),
        dtype="float64",
        allow_negative=False,
        min_value=0.0,
    ),
    "PNFIC1": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="PNFIC1",
            description="Real Private Nonresidential Fixed Investment",
            units="SAAR_BN_2017_USD",
            frequency="Q",
            release_lag_quarters=1,
            transform="pct_change",
            release_calendar_key="fred_quarterly",
        ),
        dtype="float64",
        allow_negative=False,
        min_value=0.0,
    ),
    "HOANBS": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="HOANBS",
            description="Nonfarm Business Sector: Hours Worked for All Persons",
            units="INDEX_2017_100",
            frequency="Q",
            release_lag_quarters=1,
            transform="pct_change",
            release_calendar_key="fred_quarterly",
        ),
        dtype="float64",
        allow_negative=False,
        min_value=0.0,
    ),
    "CES0500000003": SeriesSchema(
        metadata=SeriesMetadata(
            series_id="CES0500000003",
            description="Average Hourly Earnings of All Employees: Total Private",
            units="USD_PER_HOUR",
            frequency="M",
            release_lag_quarters=0,
            transform="pct_change",
            source="BLS_FRED",
            release_calendar_key="fred_monthly",
        ),
        dtype="float64",
        allow_negative=False,
        min_value=0.0,
    ),
}


def get_schema(series_id: str) -> SeriesSchema:
    if series_id not in SERIES_REGISTRY:
        raise KeyError(f"Series '{series_id}' not found in registry. "
                       f"Available: {list(SERIES_REGISTRY.keys())}")
    return SERIES_REGISTRY[series_id]
