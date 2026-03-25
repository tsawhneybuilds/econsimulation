"""ParameterProvenance: source, date, assumption flag."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class ParameterProvenance:
    source: str                         # e.g. "BEA_NIPA_2020", "FRB_H15", "ASSUMPTION"
    vintage_date: date                  # date data was pulled
    is_assumption: bool = False         # True if value is an assumption/calibrated
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "vintage_date": str(self.vintage_date),
            "is_assumption": self.is_assumption,
            "notes": self.notes,
        }
