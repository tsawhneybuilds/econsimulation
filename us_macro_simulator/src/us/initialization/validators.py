"""InitializationValidator: checks state after initialization."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from src.engine.core.state import SimulationState


@dataclass
class ValidationResult:
    passed: bool
    errors: List[str]
    warnings: List[str]

    def raise_if_failed(self) -> None:
        if not self.passed:
            raise ValueError("Initialization validation failed:\n" + "\n".join(self.errors))


class InitializationValidator:
    """Validates a freshly initialized SimulationState."""

    def validate(self, state: SimulationState) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        # 1. No NaN/Inf
        try:
            state.check_no_nan_inf()
        except ValueError as e:
            errors.append(str(e))

        # 2. No negative prices
        neg_prices = state.firms.P_i[state.firms.P_i < 0]
        if len(neg_prices) > 0:
            errors.append(f"Negative firm prices: {neg_prices[:3]}")

        # 3. No negative capital stocks
        neg_k = state.firms.K_i[state.firms.K_i < 0]
        if len(neg_k) > 0:
            errors.append(f"Negative firm capital: {neg_k[:3]}")

        # 4. Sector weights sum check
        I = state.firms.n_firms
        sector_counts = np.bincount(state.firms.G_i, minlength=6)
        if sector_counts.sum() != I:
            errors.append(f"Firm sector counts sum to {sector_counts.sum()}, expected {I}")

        # 5. Worker occupation consistency
        H_act = state.workers_act.n_workers
        employed = np.sum(state.workers_act.O_h > 0)
        unemployed = np.sum(state.workers_act.O_h == 0)
        if employed + unemployed != H_act:
            errors.append(
                f"Worker occupation mismatch: employed({employed}) + "
                f"unemployed({unemployed}) != H_act({H_act})"
            )

        # 6. Inactive workers all have O_h == -1
        if not np.all(state.workers_inact.O_h == -1):
            errors.append("Some inactive workers have non-(-1) occupation")

        # 7. Aggregate GDP positive
        if state.aggregate.Y <= 0:
            errors.append(f"Aggregate GDP Y={state.aggregate.Y} <= 0")

        # 8. Price index positive
        if state.aggregate.P_bar <= 0:
            errors.append(f"Global price index P_bar={state.aggregate.P_bar} <= 0")

        # 9. Bank equity positive
        if state.bank.E_k <= 0:
            warnings.append(f"Bank equity E_k={state.bank.E_k} <= 0")

        passed = len(errors) == 0
        return ValidationResult(passed=passed, errors=errors, warnings=warnings)
