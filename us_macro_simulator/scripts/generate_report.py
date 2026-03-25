"""Generate an HTML report from saved validation/report artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from _helpers import REPO_ROOT, validation_report_from_dict
from src.dashboards.builder import build_html_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-json", default=str(REPO_ROOT / "outputs" / "validation_report.json"))
    parser.add_argument("--comparison-table", default=str(REPO_ROOT / "outputs" / "comparison_table.parquet"))
    parser.add_argument("--output", default=str(REPO_ROOT / "outputs" / "validation_report.html"))
    args = parser.parse_args()

    report_dict = json.loads(Path(args.report_json).read_text())
    report = validation_report_from_dict(report_dict)
    comparison_table = pd.read_parquet(args.comparison_table)
    path = build_html_report(report, comparison_table, args.output, charts={})
    print(path)


if __name__ == "__main__":
    main()
