"""RunManifest: experiment ID, hashes, timestamps."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class RunManifest:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    config_hash: str = ""
    calibration_hash: str = ""
    data_vintage_hash: str = ""
    seed: int = 42
    origin_quarter: str = ""
    horizon: int = 0
    mode: str = "smoke"
    git_sha: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "RunManifest":
        with open(path) as f:
            return cls(**json.load(f))


def hash_dict(d: Dict[str, Any]) -> str:
    """Stable SHA-256 hash of a JSON-serializable dict."""
    canonical = json.dumps(d, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def hash_file(path: Path) -> str:
    """SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]
