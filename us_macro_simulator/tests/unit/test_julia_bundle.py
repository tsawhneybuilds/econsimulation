"""Tests for the Julia artifact bundle loader and evaluator."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.julia_bundle import JuliaBundleBacktestEvaluator, load_bundle
from src.validation.harness import ValidationHarness


def _write_fixture_bundle(bundle_dir: Path) -> None:
    manifest = {
        "schema_version": "1.0",
        "run_id": "bundle-test",
        "country": "US",
        "simulator": "BeforeIT.jl",
        "data_mode": "fixture",
        "calibration_date": "2016-12-31",
        "start_origin": "2017Q1",
        "end_origin": "2017Q1",
        "origins": ["2017Q1"],
        "horizon": 2,
        "n_sims": 2,
        "seed": 42,
        "variables": [
            "gdp_growth",
            "cpi_inflation",
            "unemployment_rate",
            "fed_funds_rate",
        ],
        "runtime_seconds": 1.23,
        "observed_origin_label": "full_actuals",
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest))

    observed = pd.DataFrame(
        [
            {"origin": "2017Q1", "period": "2016Q4", "GDPC1": 100.0, "CPIAUCSL": 100.0, "UNRATE": 5.0, "FEDFUNDS": 1.0, "PCECC96": 68.0, "PRFI": 5.0, "FCI": 0.0},
            {"origin": "2017Q1", "period": "2017Q1", "GDPC1": None, "CPIAUCSL": 101.0, "UNRATE": 4.9, "FEDFUNDS": 1.1, "PCECC96": None, "PRFI": None, "FCI": 0.1},
            {"origin": "full_actuals", "period": "2016Q4", "GDPC1": 100.0, "CPIAUCSL": 100.0, "UNRATE": 5.0, "FEDFUNDS": 1.0, "PCECC96": 68.0, "PRFI": 5.0, "FCI": 0.0},
            {"origin": "full_actuals", "period": "2017Q1", "GDPC1": 101.0, "CPIAUCSL": 101.0, "UNRATE": 4.9, "FEDFUNDS": 1.1, "PCECC96": 68.5, "PRFI": 5.1, "FCI": 0.1},
            {"origin": "full_actuals", "period": "2017Q2", "GDPC1": 102.0, "CPIAUCSL": 102.0, "UNRATE": 4.8, "FEDFUNDS": 1.2, "PCECC96": 69.0, "PRFI": 5.2, "FCI": 0.1},
            {"origin": "full_actuals", "period": "2017Q3", "GDPC1": 103.0, "CPIAUCSL": 103.0, "UNRATE": 4.7, "FEDFUNDS": 1.3, "PCECC96": 69.5, "PRFI": 5.3, "FCI": 0.2},
        ]
    )
    observed.to_csv(bundle_dir / "observed_dataset.csv", index=False)

    forecasts = pd.DataFrame(
        [
            {"origin": "2017Q1", "horizon": 1, "period": "2017Q2", "variable": "gdp_growth", "mean": 2.0, "p10": 1.5, "p50": 2.0, "p90": 2.5},
            {"origin": "2017Q1", "horizon": 1, "period": "2017Q2", "variable": "cpi_inflation", "mean": 2.0, "p10": 1.7, "p50": 2.0, "p90": 2.3},
            {"origin": "2017Q1", "horizon": 1, "period": "2017Q2", "variable": "unemployment_rate", "mean": 4.8, "p10": 4.7, "p50": 4.8, "p90": 4.9},
            {"origin": "2017Q1", "horizon": 1, "period": "2017Q2", "variable": "fed_funds_rate", "mean": 1.2, "p10": 1.1, "p50": 1.2, "p90": 1.3},
            {"origin": "2017Q1", "horizon": 2, "period": "2017Q3", "variable": "gdp_growth", "mean": 2.0, "p10": 1.5, "p50": 2.0, "p90": 2.5},
            {"origin": "2017Q1", "horizon": 2, "period": "2017Q3", "variable": "cpi_inflation", "mean": 2.0, "p10": 1.7, "p50": 2.0, "p90": 2.3},
            {"origin": "2017Q1", "horizon": 2, "period": "2017Q3", "variable": "unemployment_rate", "mean": 4.7, "p10": 4.6, "p50": 4.7, "p90": 4.8},
            {"origin": "2017Q1", "horizon": 2, "period": "2017Q3", "variable": "fed_funds_rate", "mean": 1.3, "p10": 1.2, "p50": 1.3, "p90": 1.4},
        ]
    )
    forecasts.to_csv(bundle_dir / "simulator_forecasts.csv", index=False)

    (bundle_dir / "initial_measurements.json").write_text(
        json.dumps(
            {
                "gdp_real": 100.0,
                "consumption_real": 68.0,
                "investment_real": 15.0,
                "government_real": 17.0,
                "exports_real": 12.0,
                "imports_real": 12.0,
                "net_exports_real": 0.0,
                "unemployment_rate": 5.0,
                "policy_rate": 1.0,
                "price_level": 1.0,
                "no_nan_inf": True,
            }
        )
    )
    pd.DataFrame(
        [
            {
                "origin": "2017Q1",
                "income_low": 0.15,
                "income_middle": 0.55,
                "income_high": 0.30,
                "consumption_low": 0.15,
                "consumption_middle": 0.55,
                "consumption_high": 0.30,
                "gva_mfg": 0.12,
                "gva_construction": 0.05,
                "gva_services": 0.55,
            }
        ]
    ).to_csv(bundle_dir / "cross_section_summary.csv", index=False)
    (bundle_dir / "scenario_bundle.json").write_text(
        json.dumps(
            {
                "rate_shock": {
                    "baseline_last_row": {"fed_funds_rate": 1.0},
                    "shocked_last_row": {"fed_funds_rate": 1.5},
                    "deltas": {"fed_funds_rate": 0.5, "cpi_inflation": 0.1},
                },
                "import_price_shock": {
                    "baseline_last_row": {"cpi_inflation": 2.0},
                    "shocked_last_row": {"cpi_inflation": 2.4},
                    "deltas": {"cpi_inflation": 0.4},
                },
            }
        )
    )


def test_bundle_loader_and_evaluator(tmp_path):
    _write_fixture_bundle(tmp_path)
    bundle = load_bundle(tmp_path)
    assert bundle.origins == ["2017Q1"]
    result = JuliaBundleBacktestEvaluator(bundle).run()
    assert "random_walk" in result.benchmark_forecasts["2017Q1"]
    assert not result.comparison_table.empty


def test_validation_harness_runs_on_bundle(tmp_path):
    _write_fixture_bundle(tmp_path)
    bundle = load_bundle(tmp_path)
    result = JuliaBundleBacktestEvaluator(bundle).run()
    harness = ValidationHarness.from_yaml(Path(__file__).parents[2] / "configs" / "validation" / "gates.yaml")
    cross_section = pd.read_parquet(
        Path(__file__).parents[2] / "data" / "fixtures" / "tier_a_crosssection.parquet"
    )
    report = harness.run_bundle(
        bundle=bundle,
        backtest_result=result,
        observed_cross_section=cross_section,
    )
    check_names = {check.name for check in report.checks}
    assert "bundle_vintage_leakage" in check_names
    assert "accounting_identity" in check_names
