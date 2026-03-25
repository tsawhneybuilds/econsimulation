"""Artifact-based internal consistency checks."""
from __future__ import annotations

from typing import Dict, List

from src.validation.models import ValidationCheck


class BundleIdentityChecker:
    """Check basic accounting identities from exported Julia measurements."""

    def check(self, measurements: Dict[str, float], tolerance: float) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        no_nan_inf = bool(measurements.get("no_nan_inf", False))
        checks.append(
            ValidationCheck(
                name="no_nan_inf",
                passed=no_nan_inf,
                severity="hard",
                summary="Exported initial measurements contain no NaN/Inf values.",
                details={},
            )
        )

        gdp = float(measurements.get("gdp_real", 0.0))
        consumption = float(measurements.get("consumption_real", 0.0))
        investment = float(measurements.get("investment_real", 0.0))
        government = float(measurements.get("government_real", 0.0))
        exports = float(measurements.get("exports_real", 0.0))
        imports = float(measurements.get("imports_real", 0.0))
        expenditure_side = consumption + investment + government + exports - imports
        rel_gap = abs(expenditure_side - gdp) / max(abs(gdp), 1.0)

        checks.append(
            ValidationCheck(
                name="accounting_identity",
                passed=rel_gap <= tolerance,
                severity="hard",
                summary="Expenditure-side GDP is close to exported aggregate GDP.",
                details={
                    "gdp": gdp,
                    "expenditure_side": expenditure_side,
                    "relative_gap": rel_gap,
                    "tolerance": tolerance,
                },
            )
        )
        return checks
