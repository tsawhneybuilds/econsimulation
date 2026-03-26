"""Release-manifest support for archived raw U.S. calibration inputs."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ReleaseManifestEntry:
    """Metadata for one staged raw artifact."""

    source: str
    dataset: str
    url: str
    local_path: str
    checksum_sha256: str
    retrieved_at: str
    release_date: str | None = None
    coverage_start: str | None = None
    coverage_end: str | None = None
    applicable_origins: list[str] = field(default_factory=list)
    content_type: str | None = None
    notes: str | None = None


class ReleaseManifest:
    """Mutable manager for `release_manifest.json`."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.entries: list[ReleaseManifestEntry] = []
        if self.path.exists():
            self.load()

    def load(self) -> list[ReleaseManifestEntry]:
        payload = json.loads(self.path.read_text())
        self.entries = [ReleaseManifestEntry(**entry) for entry in payload.get("entries", [])]
        return self.entries

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0",
            "generated_at": _utcnow_iso(),
            "entries": [asdict(entry) for entry in self.entries],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return self.path

    def add_entry(self, entry: ReleaseManifestEntry) -> ReleaseManifestEntry:
        self.entries.append(entry)
        return entry

    def stage_bytes(
        self,
        raw_root: str | Path,
        source: str,
        dataset: str,
        filename: str,
        payload: bytes,
        *,
        url: str,
        release_date: str | None = None,
        coverage_start: str | None = None,
        coverage_end: str | None = None,
        applicable_origins: list[str] | None = None,
        content_type: str | None = None,
        notes: str | None = None,
    ) -> ReleaseManifestEntry:
        raw_root = Path(raw_root)
        target_dir = raw_root / source
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        target.write_bytes(payload)
        entry = ReleaseManifestEntry(
            source=source,
            dataset=dataset,
            url=url,
            local_path=str(target),
            checksum_sha256=sha256_bytes(payload),
            retrieved_at=_utcnow_iso(),
            release_date=release_date,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            applicable_origins=list(applicable_origins or []),
            content_type=content_type,
            notes=notes,
        )
        self.add_entry(entry)
        self.save()
        return entry

    def stage_text(self, *args: Any, payload: str, **kwargs: Any) -> ReleaseManifestEntry:
        return self.stage_bytes(*args, payload=payload.encode("utf-8"), **kwargs)

    def stage_json(self, *args: Any, payload: Any, **kwargs: Any) -> ReleaseManifestEntry:
        text = json.dumps(payload, indent=2, sort_keys=True)
        return self.stage_bytes(*args, payload=text.encode("utf-8"), content_type="application/json", **kwargs)

