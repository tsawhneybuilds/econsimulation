"""Internal-consistency checks for initialized model state."""
from __future__ import annotations

from typing import List

from src.engine.core.state import SimulationState
from src.validation.models import ValidationCheck


class IdentityChecker:
    """Check basic accounting and numerical consistency."""

    def check(self, state: SimulationState, tolerance: float) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        try:
            state.check_no_nan_inf()
            numeric_ok = True
            numeric_detail = {}
        except ValueError as exc:
            numeric_ok = False
            numeric_detail = {"error": str(exc)}

        checks.append(
            ValidationCheck(
                name="no_nan_inf",
                passed=numeric_ok,
                severity="hard",
                summary="Simulation state contains no NaN/Inf values in key numeric fields.",
                details=numeric_detail,
            )
        )

        consumption = (
            state.workers_act.C_h.sum()
            + state.workers_inact.C_h.sum()
            + state.firms.C_h_i.sum()
            + state.bank.C_h
        )
        investment = (
            state.workers_act.I_h.sum()
            + state.workers_inact.I_h.sum()
            + state.firms.I_h_i.sum()
            + state.bank.I_h
            + state.firms.I_i.sum()
        )
        government = state.government.C_G
        net_exports = state.rotw.C_E - state.rotw.Y_I
        expenditure_side = float(consumption + investment + government + net_exports)
        gdp = float(state.aggregate.Y)
        rel_gap = abs(expenditure_side - gdp) / max(abs(gdp), 1.0)

        checks.append(
            ValidationCheck(
                name="accounting_identity",
                passed=rel_gap <= tolerance,
                severity="hard",
                summary="Expenditure-side GDP is close to aggregate GDP.",
                details={
                    "gdp": gdp,
                    "expenditure_side": expenditure_side,
                    "relative_gap": rel_gap,
                    "tolerance": tolerance,
                },
            )
        )

        labour_force = int((state.workers_act.O_h >= 0).sum())
        employed = int((state.workers_act.O_h > 0).sum())
        checks.append(
            ValidationCheck(
                name="labour_force_accounting",
                passed=(labour_force == state.workers_act.n_workers and employed <= labour_force),
                severity="soft",
                summary="Worker occupation coding is internally consistent.",
                details={"labour_force": labour_force, "employed": employed},
            )
        )

        return checks
