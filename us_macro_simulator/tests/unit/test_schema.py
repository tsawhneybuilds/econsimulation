"""Unit tests for data contract schema."""
import pytest
import pandas as pd
import numpy as np

from src.us.data_contracts.schema import SERIES_REGISTRY, get_schema, SeriesSchema


def test_registry_not_empty():
    assert len(SERIES_REGISTRY) > 0


def test_all_required_series_present():
    required = ["GDPC1", "CPIAUCSL", "CPILFESL", "UNRATE", "FEDFUNDS", "PCECC96", "PRFI"]
    for sid in required:
        assert sid in SERIES_REGISTRY, f"{sid} missing from registry"


def test_get_schema_returns_correct_type():
    schema = get_schema("GDPC1")
    assert isinstance(schema, SeriesSchema)


def test_get_schema_raises_for_unknown():
    with pytest.raises(KeyError):
        get_schema("DOESNOTEXIST_XYZ")


def test_series_metadata_units_nonempty():
    for sid, schema in SERIES_REGISTRY.items():
        assert schema.metadata.units != "", f"{sid} has empty units"


def test_release_lag_nonnegative():
    for sid, schema in SERIES_REGISTRY.items():
        assert schema.metadata.release_lag_quarters >= 0


def test_frequency_valid():
    valid_freqs = {"Q", "M", "A"}
    for sid, schema in SERIES_REGISTRY.items():
        assert schema.metadata.frequency in valid_freqs, \
            f"{sid} has invalid frequency: {schema.metadata.frequency}"


def test_unrate_bounds():
    schema = get_schema("UNRATE")
    assert schema.min_value == 0.0
    assert schema.max_value == 100.0


def test_gdpc1_no_negative():
    schema = get_schema("GDPC1")
    assert schema.allow_negative is False
    assert schema.min_value == 0.0
