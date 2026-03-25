"""Performance and runtime checks."""
from __future__ import annotations

import sys
from typing import Dict, List

import resource

from src.validation.models import ValidationCheck


def _memory_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return usage / (1024 * 1024)
    return usage / 1024


class PerformanceChecker:
    """Validate runtime and memory diagnostics."""

    def check(self, runtime_seconds: float, gates: Dict[str, float]) -> List[ValidationCheck]:
        runtime_threshold = float(gates.get("max_runtime_seconds", 300))
        memory_threshold = float(gates.get("max_memory_mb", 2048))
        memory_mb = _memory_mb()
        return [
            ValidationCheck(
                name="runtime_budget",
                passed=runtime_seconds <= runtime_threshold,
                severity="hard",
                summary="Backtest runtime stays within the configured budget.",
                details={"runtime_seconds": runtime_seconds, "threshold": runtime_threshold},
            ),
            ValidationCheck(
                name="memory_budget",
                passed=memory_mb <= memory_threshold,
                severity="soft",
                summary="Peak memory usage stays within the configured budget.",
                details={"memory_mb": memory_mb, "threshold": memory_threshold},
            ),
        ]
