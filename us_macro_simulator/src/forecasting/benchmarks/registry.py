"""Benchmark registry: name -> benchmark instance."""
from __future__ import annotations

from typing import Any, Dict

from .random_walk import RandomWalkBenchmark
from .ar_benchmark import ARBenchmark
from .local_mean import LocalMeanBenchmark
from .factor_model import FactorModelBenchmark
from .semi_structural import SemiStructuralBenchmark

BENCHMARK_REGISTRY: Dict[str, Any] = {
    "random_walk": RandomWalkBenchmark(),
    "ar4": ARBenchmark(order=4),
    "local_mean": LocalMeanBenchmark(window=8),
    "factor_model": FactorModelBenchmark(n_factors=2, ar_order=2),
    "semi_structural": SemiStructuralBenchmark(),
}


def get_benchmark(name: str) -> Any:
    """Return the benchmark instance registered under *name*.

    Raises ``KeyError`` with a helpful message when the name is unknown.
    """
    if name not in BENCHMARK_REGISTRY:
        raise KeyError(
            f"Unknown benchmark: {name}. "
            f"Available: {list(BENCHMARK_REGISTRY)}"
        )
    return BENCHMARK_REGISTRY[name]


def list_benchmarks() -> list[str]:
    """Return the names of all registered benchmarks."""
    return list(BENCHMARK_REGISTRY.keys())
