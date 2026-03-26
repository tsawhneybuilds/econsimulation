"""Tests for raw-source release manifest staging."""
from __future__ import annotations

import json

from src.us.data_contracts.release_manifest import ReleaseManifest


def test_release_manifest_stages_json_with_checksum(tmp_path):
    manifest = ReleaseManifest(tmp_path / "release_manifest.json")
    payload = {"dataset": "NIPA", "table": "T10105", "vintage": "2019-12-31"}

    entry = manifest.stage_json(
        tmp_path,
        "bea",
        "nipa",
        "t10105_2019q4.json",
        payload=payload,
        url="https://apps.bea.gov/api/data",
        release_date="2020-01-30",
        coverage_start="2019Q4",
        coverage_end="2019Q4",
        applicable_origins=["2019Q4"],
    )
    manifest.save()

    saved = json.loads((tmp_path / "release_manifest.json").read_text())
    staged_payload = json.loads((tmp_path / "bea" / "t10105_2019q4.json").read_text())

    assert entry.source == "bea"
    assert entry.checksum_sha256
    assert staged_payload == payload
    assert saved["entries"][0]["url"] == "https://apps.bea.gov/api/data"
    assert saved["entries"][0]["applicable_origins"] == ["2019Q4"]


def test_release_manifest_load_roundtrip(tmp_path):
    manifest = ReleaseManifest(tmp_path / "release_manifest.json")
    manifest.stage_text(
        tmp_path,
        "fred",
        "series",
        "example.txt",
        payload="example",
        url="https://fred.stlouisfed.org",
        release_date="2019-12-31",
    )
    manifest.save()

    loaded = ReleaseManifest(tmp_path / "release_manifest.json")

    assert len(loaded.entries) == 1
    assert loaded.entries[0].source == "fred"
    assert loaded.entries[0].dataset == "series"
    assert loaded.entries[0].local_path.endswith("fred/example.txt")
