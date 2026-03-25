"""Coarse cross-sectional realism checks."""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

from src.engine.core.state import SimulationState
from src.validation.models import ValidationCheck


class CrossSectionChecker:
    """Compare simple simulated household and sector shares to fixture targets."""

    def check(
        self,
        state: SimulationState,
        observed_cross_section: pd.DataFrame | None = None,
    ) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        incomes = np.concatenate([state.workers_act.Y_h, state.workers_inact.Y_h])
        consumptions = np.concatenate([state.workers_act.C_h, state.workers_inact.C_h])

        terciles = np.quantile(incomes, [1 / 3, 2 / 3])
        low_mask = incomes <= terciles[0]
        mid_mask = (incomes > terciles[0]) & (incomes <= terciles[1])
        high_mask = incomes > terciles[1]

        simulated_income_shares = np.array([
            incomes[low_mask].sum(),
            incomes[mid_mask].sum(),
            incomes[high_mask].sum(),
        ])
        simulated_income_shares /= max(simulated_income_shares.sum(), 1e-9)

        simulated_consumption_shares = np.array([
            consumptions[low_mask].sum(),
            consumptions[mid_mask].sum(),
            consumptions[high_mask].sum(),
        ])
        simulated_consumption_shares /= max(simulated_consumption_shares.sum(), 1e-9)

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

        latest = observed_cross_section.dropna(how="all").iloc[-1]
        observed_income = np.array([
            latest.get("income_low", np.nan),
            latest.get("income_middle", np.nan),
            latest.get("income_high", np.nan),
        ], dtype=float)
        observed_income /= max(observed_income.sum(), 1e-9)
        observed_consumption = np.array([
            latest.get("consumption_low", np.nan),
            latest.get("consumption_middle", np.nan),
            latest.get("consumption_high", np.nan),
        ], dtype=float)
        observed_consumption /= max(observed_consumption.sum(), 1e-9)

        income_diff = float(np.max(np.abs(simulated_income_shares - observed_income)))
        cons_diff = float(np.max(np.abs(simulated_consumption_shares - observed_consumption)))
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

        sector_output = np.bincount(
            state.firms.G_i,
            weights=state.firms.Y_i,
            minlength=max(int(state.firms.G_i.max()) + 1, 6),
        )
        total_output = max(float(sector_output.sum()), 1e-9)
        simulated_sector_shares = {
            "gva_mfg": float(sector_output[1] / total_output),
            "gva_construction": float(sector_output[2] / total_output),
            "gva_services": float(sector_output[5] / total_output),
        }
        observed_sector = {
            "gva_mfg": float(latest.get("gva_mfg", np.nan)),
            "gva_construction": float(latest.get("gva_construction", np.nan)),
            "gva_services": float(latest.get("gva_services", np.nan)),
        }
        obs_total = max(sum(observed_sector.values()), 1e-9)
        observed_sector = {key: value / obs_total for key, value in observed_sector.items()}
        max_sector_diff = float(
            max(abs(simulated_sector_shares[key] - observed_sector[key]) for key in simulated_sector_shares)
        )
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
