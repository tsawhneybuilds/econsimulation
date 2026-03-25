"""Cross-sectional checks against exported Julia summaries."""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

from src.validation.models import ValidationCheck


class BundleCrossSectionChecker:
    """Compare exported cross-sectional shares to observed fixture targets."""

    def check(
        self,
        summary: pd.DataFrame,
        observed_cross_section: pd.DataFrame | None = None,
    ) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        if summary.empty:
            checks.append(
                ValidationCheck(
                    name="cross_section_summary_present",
                    passed=False,
                    severity="soft",
                    summary="Cross-sectional summary is missing from the Julia bundle.",
                    details={},
                )
            )
            return checks

        if observed_cross_section is None or observed_cross_section.empty:
            checks.append(
                ValidationCheck(
                    name="cross_section_fixture_available",
                    passed=False,
                    severity="soft",
                    summary="Observed cross-sectional fixture data is unavailable.",
                    details={},
                )
            )
            return checks

        sim = summary.dropna(how="all").iloc[-1]
        obs = observed_cross_section.dropna(how="all").iloc[-1]

        simulated_income = np.array(
            [sim.get("income_low", np.nan), sim.get("income_middle", np.nan), sim.get("income_high", np.nan)],
            dtype=float,
        )
        simulated_income /= max(simulated_income.sum(), 1e-9)
        simulated_consumption = np.array(
            [
                sim.get("consumption_low", np.nan),
                sim.get("consumption_middle", np.nan),
                sim.get("consumption_high", np.nan),
            ],
            dtype=float,
        )
        simulated_consumption /= max(simulated_consumption.sum(), 1e-9)

        observed_income = np.array(
            [obs.get("income_low", np.nan), obs.get("income_middle", np.nan), obs.get("income_high", np.nan)],
            dtype=float,
        )
        observed_income /= max(observed_income.sum(), 1e-9)
        observed_consumption = np.array(
            [
                obs.get("consumption_low", np.nan),
                obs.get("consumption_middle", np.nan),
                obs.get("consumption_high", np.nan),
            ],
            dtype=float,
        )
        observed_consumption /= max(observed_consumption.sum(), 1e-9)

        income_diff = float(np.max(np.abs(simulated_income - observed_income)))
        cons_diff = float(np.max(np.abs(simulated_consumption - observed_consumption)))
        checks.append(
            ValidationCheck(
                name="household_bin_shares",
                passed=income_diff <= 0.20 and cons_diff <= 0.20,
                severity="soft",
                summary="Coarse low/middle/high household shares are within a Stage 1 tolerance.",
                details={
                    "max_income_share_diff": income_diff,
                    "max_consumption_share_diff": cons_diff,
                },
            )
        )

        simulated_sector = {
            "gva_mfg": float(sim.get("gva_mfg", np.nan)),
            "gva_construction": float(sim.get("gva_construction", np.nan)),
            "gva_services": float(sim.get("gva_services", np.nan)),
        }
        observed_sector = {
            "gva_mfg": float(obs.get("gva_mfg", np.nan)),
            "gva_construction": float(obs.get("gva_construction", np.nan)),
            "gva_services": float(obs.get("gva_services", np.nan)),
        }
        obs_total = max(sum(observed_sector.values()), 1e-9)
        observed_sector = {key: value / obs_total for key, value in observed_sector.items()}
        max_sector_diff = float(max(abs(simulated_sector[key] - observed_sector[key]) for key in simulated_sector))
        checks.append(
            ValidationCheck(
                name="sector_share_alignment",
                passed=max_sector_diff <= 0.25,
                severity="soft",
                summary="Broad manufacturing/construction/services output shares are plausible.",
                details={"max_sector_share_diff": max_sector_diff},
            )
        )
        return checks
