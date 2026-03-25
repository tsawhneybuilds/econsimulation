"""Data-quality checks for observed datasets."""
from __future__ import annotations

from typing import List

from src.us.data_contracts.build_dataset import ObservedDataset
from src.us.data_contracts.vintages import VintageDataset, VintageLeakageError
from src.validation.models import ValidationCheck


REQUIRED_SERIES = {
    "GDPC1",
    "GDPC1_GROWTH",
    "CPIAUCSL",
    "CPILFESL",
    "UNRATE",
    "FEDFUNDS",
    "PCECC96",
    "PRFI",
    "FCI",
}


class DataQualityChecker:
    """Validate observed data schema, index quality, and vintage masking."""

    def check(self, dataset: ObservedDataset) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        missing = sorted(REQUIRED_SERIES - set(dataset.data.columns))
        checks.append(
            ValidationCheck(
                name="required_series",
                passed=not missing,
                severity="hard",
                summary="All required Stage 1 aggregate series are present.",
                details={"missing": missing},
            )
        )

        duplicate_count = int(dataset.data.index.duplicated().sum())
        checks.append(
            ValidationCheck(
                name="duplicate_timestamps",
                passed=duplicate_count == 0,
                severity="hard",
                summary="Observed dataset index has no duplicate timestamps.",
                details={"duplicate_count": duplicate_count},
            )
        )

        checks.append(
            ValidationCheck(
                name="monotonic_time_index",
                passed=bool(dataset.data.index.is_monotonic_increasing),
                severity="hard",
                summary="Observed dataset index is monotonic increasing.",
                details={"n_periods": dataset.n_periods},
            )
        )

        try:
            VintageDataset(
                vintage=dataset.vintage,
                frequency=dataset.frequency,
                data=dataset.data,
                metadata=dataset.metadata,
            ).validate_no_leakage(dataset.vintage)
            leakage_passed = True
            leakage_detail = {}
        except VintageLeakageError as exc:
            leakage_passed = False
            leakage_detail = {"error": str(exc)}

        checks.append(
            ValidationCheck(
                name="vintage_leakage",
                passed=leakage_passed,
                severity="hard",
                summary="Observed dataset respects release-lag constraints.",
                details=leakage_detail,
            )
        )

        missing_share = float(dataset.data.isna().mean().mean()) if not dataset.data.empty else 1.0
        checks.append(
            ValidationCheck(
                name="missingness",
                passed=missing_share <= 0.35,
                severity="soft",
                summary="Observed dataset missingness stays within a coarse Stage 1 tolerance.",
                details={"missing_share": missing_share},
            )
        )

        return checks
