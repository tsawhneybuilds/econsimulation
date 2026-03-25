"""Data contracts for U.S. macro simulator."""
from .build_dataset import DatasetBuilder, ObservedDataset, _generate_synthetic_fixture
from .schema import SERIES_REGISTRY, SeriesSchema, SeriesMetadata, get_schema
from .vintages import VintageDataset, VintageLeakageError
from .loaders import load_fred_csv, load_fixture

__all__ = [
    "DatasetBuilder",
    "ObservedDataset",
    "_generate_synthetic_fixture",
    "SERIES_REGISTRY",
    "SeriesSchema",
    "SeriesMetadata",
    "get_schema",
    "VintageDataset",
    "VintageLeakageError",
    "load_fred_csv",
    "load_fixture",
]
