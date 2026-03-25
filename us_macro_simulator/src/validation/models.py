"""Shared validation data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class ValidationCheck:
    """Single validation outcome."""

    name: str
    passed: bool
    severity: str
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "summary": self.summary,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """Aggregate validation report across all checks."""

    run_id: str
    overall_passed: bool
    checks: List[ValidationCheck]
    summary: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def hard_failures(self) -> List[ValidationCheck]:
        return [check for check in self.checks if check.severity == "hard" and not check.passed]

    def warnings(self) -> List[ValidationCheck]:
        return [check for check in self.checks if check.severity != "hard" and not check.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "overall_passed": self.overall_passed,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "artifacts": self.artifacts,
            "notes": self.notes,
            "checks": [check.to_dict() for check in self.checks],
        }
