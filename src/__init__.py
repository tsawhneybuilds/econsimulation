"""Canonical package shim for the simulator source tree.

This repo historically had a duplicate ``src/us/data_contracts`` tree at the
workspace root.  Make ``import src...`` resolve to ``us_macro_simulator/src``
so there is a single authoritative package location.
"""
from __future__ import annotations

from pathlib import Path


_CANONICAL_SRC = Path(__file__).resolve().parents[1] / "us_macro_simulator" / "src"
__path__ = [str(_CANONICAL_SRC)]

