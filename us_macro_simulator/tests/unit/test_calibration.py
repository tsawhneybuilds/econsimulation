"""Unit tests for CalibrationBundle."""
import pytest
from src.us.calibration import build_us_2019q4_calibration, CalibrationBundle


def test_calibration_builds():
    calib = build_us_2019q4_calibration()
    assert isinstance(calib, CalibrationBundle)


def test_reference_quarter():
    calib = build_us_2019q4_calibration()
    assert calib.reference_quarter == "2019Q4"


def test_version_hash_stable():
    c1 = build_us_2019q4_calibration()
    c2 = build_us_2019q4_calibration()
    assert c1.version_hash == c2.version_hash


def test_sector_weights_sum():
    calib = build_us_2019q4_calibration()
    total = sum(calib.structural.sector_weights)
    assert abs(total - 1.0) < 1e-6


def test_gva_shares_sum():
    calib = build_us_2019q4_calibration()
    total = sum(calib.initial_distributions.gva_shares)
    assert abs(total - 1.0) < 1e-6


def test_expenditure_shares_approx_unity():
    calib = build_us_2019q4_calibration()
    m = calib.mapping
    total = m.C_share + m.I_share + m.G_share + m.NX_share
    assert abs(total - 1.0) < 0.01


def test_tax_rates_in_bounds():
    calib = build_us_2019q4_calibration()
    s = calib.structural
    for attr in ["tau_INC", "tau_FIRM", "tau_VAT", "tau_SIW", "tau_SIF"]:
        v = getattr(s, attr)
        assert 0 <= v <= 1, f"{attr}={v} out of [0,1]"


def test_n_sectors_consistent():
    calib = build_us_2019q4_calibration()
    G = calib.structural.G
    assert len(calib.structural.sector_weights) == G
    assert len(calib.structural.alpha_bar) == G
    assert len(calib.structural.delta) == G
    assert len(calib.initial_distributions.gva_shares) == G


def test_initial_gdp_positive():
    calib = build_us_2019q4_calibration()
    assert calib.initial_distributions.Y_0 > 0


def test_provenance_present():
    calib = build_us_2019q4_calibration()
    assert len(calib.provenance) > 0
    for key, prov in calib.provenance.items():
        assert prov.source != ""
        assert prov.vintage_date is not None


def test_pi_map_weights_sum():
    calib = build_us_2019q4_calibration()
    m = calib.mapping
    w = m.w_food + m.w_energy + m.w_core
    assert abs(w - 1.0) < 1e-6, f"Price index weights sum to {w}"


def test_invalid_sector_weights_raises():
    with pytest.raises(ValueError, match="sector_weights"):
        bad_structural = __import__(
            "src.us.calibration.us_calibration",
            fromlist=["StructuralParams"]
        ).StructuralParams(sector_weights=[0.5, 0.6, 0.0, 0.0, 0.0, 0.0])  # sums to 1.1
        CalibrationBundle(structural=bad_structural)
