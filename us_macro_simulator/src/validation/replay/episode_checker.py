"""Directional replay checks using simple shocks."""
from __future__ import annotations

import copy
from typing import List

import numpy as np

from src.engine.core.engine import USMacroEngine
from src.engine.core.state import SimulationState
from src.engine.shocks.shock_protocol import ImportPriceShock, NoShock, RateShock
from src.validation.models import ValidationCheck


class ReplayEpisodeChecker:
    """Run reduced scenario/replay checks on the initialized state."""

    def check(self, state: SimulationState) -> List[ValidationCheck]:
        engine = USMacroEngine()
        base = copy.deepcopy(state)
        shocked_rate = copy.deepcopy(state)
        shocked_import = copy.deepcopy(state)

        base.rng_state = np.random.default_rng(7)
        shocked_rate.rng_state = np.random.default_rng(7)
        shocked_import.rng_state = np.random.default_rng(7)

        engine.step(base, shock=NoShock())
        engine.step(shocked_rate, shock=RateShock(delta_r=0.005, duration=1))
        engine.step(shocked_import, shock=ImportPriceShock(delta_pm=0.10, duration=1))

        return [
            ValidationCheck(
                name="rate_shock_direction",
                passed=shocked_rate.central_bank.r_bar >= base.central_bank.r_bar,
                severity="soft",
                summary="Rate shock raises the policy rate relative to baseline.",
                details={
                    "baseline_rate": base.central_bank.r_bar,
                    "shocked_rate": shocked_rate.central_bank.r_bar,
                },
            ),
            ValidationCheck(
                name="import_price_shock_direction",
                passed=float(shocked_import.firms.P_i.mean()) >= float(base.firms.P_i.mean()),
                severity="soft",
                summary="Import price shock raises average firm prices relative to baseline.",
                details={
                    "baseline_price": float(base.firms.P_i.mean()),
                    "shocked_price": float(shocked_import.firms.P_i.mean()),
                },
            ),
        ]
