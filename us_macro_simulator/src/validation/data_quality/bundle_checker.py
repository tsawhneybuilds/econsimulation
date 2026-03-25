"""Bundle-level data-quality and leakage checks."""
from __future__ import annotations

from datetime import datetime
from typing import List

import pandas as pd

from src.julia_bundle.loader import JuliaArtifactBundle
from src.us.data_contracts.loaders import build_metadata_map
from src.us.data_contracts.vintages import VintageDataset, VintageLeakageError
from src.validation.models import ValidationCheck


class BundleVintageChecker:
    """Validate leakage safety across origin-specific observed histories."""

    def check(self, bundle: JuliaArtifactBundle) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        try:
            for origin in bundle.origins:
                raw = bundle.raw_history_for_origin(origin)
                metadata = build_metadata_map(list(raw.columns))
                as_of_date = (pd.Period(origin, freq="Q").end_time + pd.Timedelta(days=1)).date()
                as_of = datetime.combine(as_of_date, datetime.min.time())
                dataset = VintageDataset(
                    vintage=as_of,
                    frequency="Q",
                    data=raw,
                    metadata=metadata,
                )
                dataset.validate_no_leakage(as_of)
            passed = True
            details = {"origins_checked": len(bundle.origins)}
        except VintageLeakageError as exc:
            passed = False
            details = {"error": str(exc)}

        checks.append(
            ValidationCheck(
                name="bundle_vintage_leakage",
                passed=passed,
                severity="hard",
                summary="Origin-specific observed histories respect release-lag constraints.",
                details=details,
            )
        )
        return checks
