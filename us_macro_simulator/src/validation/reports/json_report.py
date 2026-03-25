"""JSON writer for validation reports."""
from __future__ import annotations

import json
from pathlib import Path

from src.validation.models import ValidationReport


def write_json_report(report: ValidationReport, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2))
    return output_path
