"""HTML writer for validation reports."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.dashboards.builder import build_html_report
from src.dashboards.charts import build_default_charts
from src.forecasting.runners.backtest_runner import BacktestResult
from src.validation.models import ValidationReport


def write_html_report(
    report: ValidationReport,
    backtest_result: BacktestResult,
    actuals: pd.DataFrame,
    output_dir: str | Path,
) -> Path:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    charts = build_default_charts(
        backtest_result=backtest_result,
        actuals=actuals,
        output_dir=output_root / "charts",
    )
    return build_html_report(
        report=report,
        comparison_table=backtest_result.comparison_table,
        output_path=output_root / "validation_report.html",
        charts=charts,
    )
