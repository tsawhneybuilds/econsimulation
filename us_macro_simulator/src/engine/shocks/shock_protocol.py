"""Shock protocol: ABC and concrete shocks."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from src.engine.core.state import SimulationState


class ShockProtocol(ABC):
    """Abstract base class for shocks applied during step."""

    @abstractmethod
    def apply(self, state: SimulationState) -> None:
        """Apply shock in-place to state."""

    def __call__(self, state: SimulationState) -> None:
        self.apply(state)


class NoShock(ShockProtocol):
    """No shock (default)."""

    def apply(self, state: SimulationState) -> None:
        pass


class RateShock(ShockProtocol):
    """
    Instantaneous shock to central bank policy rate.
    delta_r: change in quarterly rate (e.g. +0.005 = +20bp annual)
    duration: how many steps to hold the shock
    """

    def __init__(self, delta_r: float = 0.005, duration: int = 4):
        self.delta_r = delta_r
        self.duration = duration
        self._steps_remaining = duration

    def apply(self, state: SimulationState) -> None:
        if self._steps_remaining > 0:
            state.central_bank.r_bar = max(
                0.0, state.central_bank.r_bar + self.delta_r
            )
            state.aggregate.r_bar = state.central_bank.r_bar
            self._steps_remaining -= 1


class ImportPriceShock(ShockProtocol):
    """
    Shock to import prices (supply-side inflation shock).
    delta_pm: fractional change in import price (e.g. 0.10 = +10%)
    duration: how many steps to hold
    """

    def __init__(self, delta_pm: float = 0.10, duration: int = 4):
        self.delta_pm = delta_pm
        self.duration = duration
        self._steps_remaining = duration

    def apply(self, state: SimulationState) -> None:
        if self._steps_remaining > 0:
            # Raise ROW import price index for all sectors
            state.rotw.P_m = state.rotw.P_m * (1.0 + self.delta_pm)
            # Pass-through to firm costs via import component
            import_share = 0.15  # ~15% import content
            state.firms.P_i *= (1 + self.delta_pm * import_share)
            self._steps_remaining -= 1


class TFPShock(ShockProtocol):
    """
    Aggregate TFP shock: scales all firm labour productivities by (1 + delta_tfp).

    Parameters
    ----------
    delta_tfp : float
        Fractional change in TFP (negative = adverse shock).
    duration : int
        Number of steps the shock persists.
    """

    def __init__(self, delta_tfp: float = -0.02, duration: int = 4):
        self.delta_tfp = delta_tfp
        self.duration = duration
        self._steps_remaining = duration

    def apply(self, state: SimulationState) -> None:
        if self._steps_remaining > 0:
            state.firms.alpha_bar_i = state.firms.alpha_bar_i * (1.0 + self.delta_tfp)
            self._steps_remaining -= 1


class DemandShock(ShockProtocol):
    """
    Aggregate demand shock: scales household desired consumption budgets by
    (1 + delta_c) for one step, mimicking a shift in animal spirits.

    Parameters
    ----------
    delta_c : float
        Fractional change in desired consumption.
    duration : int
        Number of steps the shock persists.
    """

    def __init__(self, delta_c: float = -0.05, duration: int = 2):
        self.delta_c = delta_c
        self.duration = duration
        self._steps_remaining = duration

    def apply(self, state: SimulationState) -> None:
        if self._steps_remaining > 0:
            state.workers_act.C_d_h = state.workers_act.C_d_h * (1.0 + self.delta_c)
            state.workers_inact.C_d_h = state.workers_inact.C_d_h * (1.0 + self.delta_c)
            self._steps_remaining -= 1


class CompositeShock(ShockProtocol):
    """
    Apply multiple shocks in sequence.

    Parameters
    ----------
    shocks : list[ShockProtocol]
        Ordered list of shocks; each is applied in turn.
    """

    def __init__(self, shocks: list):
        self.shocks = list(shocks)

    def apply(self, state: SimulationState) -> None:
        for shock in self.shocks:
            shock.apply(state)
