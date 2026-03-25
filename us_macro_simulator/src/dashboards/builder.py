"""HTML dashboard/report rendering."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.validation.models import ValidationReport


TEMPLATE_DIR = Path(__file__).parent / "templates"


def build_html_report(
    report: ValidationReport,
    comparison_table: pd.DataFrame,
    output_path: str | Path,
    charts: Dict[str, str],
) -> Path:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    html = template.render(
        report=report.to_dict(),
        hard_failures=[check.to_dict() for check in report.hard_failures()],
        warnings=[check.to_dict() for check in report.warnings()],
        comparison_rows=comparison_table.fillna("").to_dict(orient="records"),
        charts=charts,
    )
    output_file.write_text(html)
    return output_file
