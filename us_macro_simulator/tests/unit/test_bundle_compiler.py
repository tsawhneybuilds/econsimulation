"""Tests for the U.S. calibration bundle compiler."""
from __future__ import annotations

import json

import pandas as pd

from src.us.calibration import (
    REQUIRED_CALIBRATION_KEYS,
    REQUIRED_FIGARO_KEYS,
    REQUIRED_TIMESERIES_KEYS,
    build_bootstrap_bundle_from_observed,
    validate_bundle_dicts,
)


def _observed_panel() -> pd.DataFrame:
    periods = pd.period_range("2017Q1", "2019Q4", freq="Q").astype(str)
    base = pd.Series(range(len(periods)), dtype=float)
    return pd.DataFrame(
        {
            "period": periods,
            "GDPC1": 19_000.0 + base * 40.0,
            "PCECC96": 12_900.0 + base * 26.0,
            "PRFI": 950.0 + base * 8.0,
            "PNFIC1": 2_850.0 + base * 10.0,
            "GCEC1": 3_200.0 + base * 6.0,
            "EXPGSC1": 2_200.0 + base * 5.0,
            "IMPGSC1": 2_700.0 + base * 5.0,
            "CPIAUCSL": 245.0 + base * 0.8,
            "CPILFESL": 250.0 + base * 0.7,
            "GDPDEF": 110.0 + base * 0.4,
            "UNRATE": 5.0 - base * 0.03,
            "FEDFUNDS": 1.25 + base * 0.02,
            "FCI": base * 0.01,
        }
    )


def test_build_bootstrap_bundle_writes_complete_artifacts(tmp_path):
    bundle_dir = build_bootstrap_bundle_from_observed(_observed_panel(), tmp_path)

    manifest = json.loads((bundle_dir / "manifest.json").read_text())
    calibration = json.loads((bundle_dir / manifest["calibration_file"]).read_text())
    figaro = json.loads((bundle_dir / manifest["figaro_file"]).read_text())
    data = json.loads((bundle_dir / manifest["data_file"]).read_text())
    ea = json.loads((bundle_dir / manifest["ea_file"]).read_text())
    provenance = json.loads((bundle_dir / manifest["provenance_file"]).read_text())
    observed = pd.read_csv(bundle_dir / manifest["observed_macro_file"])

    validate_bundle_dicts(calibration, figaro, data, ea)

    assert set(REQUIRED_CALIBRATION_KEYS).issubset(calibration)
    assert set(REQUIRED_FIGARO_KEYS).issubset(figaro)
    assert set(REQUIRED_TIMESERIES_KEYS).issubset(data)
    assert observed.columns[0] == "period"
    assert manifest["reference_quarter"] == "2019Q4"
    assert manifest["sector_count"] == 62
    assert len(calibration["firms"]) == 62
    assert len(calibration["firms"][0]) == 3
    assert len(figaro["intermediate_consumption"]) == 62
    assert len(figaro["intermediate_consumption"][0]) == 62
    assert len(figaro["intermediate_consumption"][0][0]) == 3
    assert len(provenance["ea"]) == len(ea)


def test_bundle_provenance_tags_only_ea_as_fallback(tmp_path):
    bundle_dir = build_bootstrap_bundle_from_observed(_observed_panel(), tmp_path)
    provenance = json.loads((bundle_dir / "provenance.json").read_text())

    assert all(meta["kind"] != "fallback" for meta in provenance["calibration"].values())
    assert all(meta["kind"] != "fallback" for meta in provenance["figaro"].values())
    assert all(meta["kind"] != "fallback" for meta in provenance["data"].values())
    assert all(meta["kind"] == "fallback" for meta in provenance["ea"].values())

