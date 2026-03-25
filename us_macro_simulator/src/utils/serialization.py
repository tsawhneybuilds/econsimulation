"""Artifact save/load utilities."""
from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd


def save_artifact(obj: Any, path: Path, fmt: str = "auto") -> str:
    """Save obj to path; returns SHA-256 hash of saved bytes.
    fmt: 'parquet', 'json', 'pickle', 'auto' (inferred from extension).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "auto":
        fmt = _infer_fmt(path)

    if fmt == "parquet":
        if not isinstance(obj, pd.DataFrame):
            raise TypeError(f"parquet requires DataFrame, got {type(obj)}")
        obj.to_parquet(path)
        raw = path.read_bytes()
    elif fmt == "json":
        raw = json.dumps(obj, indent=2, default=str).encode()
        path.write_bytes(raw)
    elif fmt == "pickle":
        raw = pickle.dumps(obj)
        path.write_bytes(raw)
    else:
        raise ValueError(f"Unknown format: {fmt}")

    return hashlib.sha256(raw).hexdigest()[:16]


def load_artifact(path: Path, fmt: str = "auto") -> Any:
    path = Path(path)
    if fmt == "auto":
        fmt = _infer_fmt(path)

    if fmt == "parquet":
        return pd.read_parquet(path)
    elif fmt == "json":
        with open(path) as f:
            return json.load(f)
    elif fmt == "pickle":
        with open(path, "rb") as f:
            return pickle.load(f)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def _infer_fmt(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return "parquet"
    elif suffix == ".json":
        return "json"
    elif suffix in (".pkl", ".pickle"):
        return "pickle"
    return "json"
