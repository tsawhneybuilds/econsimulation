"""Forecast benchmark implementations."""

from .ar_benchmark import ARBenchmark
from .factor_model import FactorModelBenchmark
from .local_mean import LocalMeanBenchmark
from .random_walk import RandomWalkBenchmark
from .registry import BENCHMARK_REGISTRY, get_benchmark, list_benchmarks
from .semi_structural import SemiStructuralBenchmark

__all__ = [
    "ARBenchmark",
    "FactorModelBenchmark",
    "LocalMeanBenchmark",
    "RandomWalkBenchmark",
    "SemiStructuralBenchmark",
    "BENCHMARK_REGISTRY",
    "get_benchmark",
    "list_benchmarks",
]
