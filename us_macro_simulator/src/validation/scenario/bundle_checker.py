"""Scenario and replay checks for Julia bundle artifacts."""
from __future__ import annotations

from typing import Dict, List

from src.validation.models import ValidationCheck


class BundleScenarioChecker:
    """Check directional responses from exported scenario runs."""

    def check(self, scenario_bundle: Dict[str, object]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        rate = scenario_bundle.get("rate_shock", {})
        rate_delta = float(rate.get("deltas", {}).get("fed_funds_rate", 0.0))
        checks.append(
            ValidationCheck(
                name="rate_shock_direction",
                passed=rate_delta >= 0.0,
                severity="soft",
                summary="Rate shock raises the policy rate relative to baseline.",
                details={"fed_funds_rate_delta": rate_delta},
            )
        )

        import_price = scenario_bundle.get("import_price_shock", {})
        import_delta = float(import_price.get("deltas", {}).get("cpi_inflation", 0.0))
        checks.append(
            ValidationCheck(
                name="import_price_shock_direction",
                passed=import_delta >= 0.0,
                severity="soft",
                summary="Import price shock raises inflation relative to baseline.",
                details={"cpi_inflation_delta": import_delta},
            )
        )
        return checks
