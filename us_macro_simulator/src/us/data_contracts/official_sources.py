"""Official-source clients used by the U.S. calibration build."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Mapping

import requests

from .release_manifest import ReleaseManifest, ReleaseManifestEntry


@dataclass
class _BaseSourceClient:
    raw_root: Path
    manifest: ReleaseManifest
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        self.raw_root = Path(self.raw_root)
        self.session = requests.Session()

    def _get(self, url: str, *, params: Mapping[str, Any] | None = None) -> requests.Response:
        response = self.session.get(url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response

    def _stage_response(
        self,
        *,
        source: str,
        dataset: str,
        filename: str,
        url: str,
        response: requests.Response,
        release_date: str | None = None,
        coverage_start: str | None = None,
        coverage_end: str | None = None,
        applicable_origins: list[str] | None = None,
        notes: str | None = None,
    ) -> ReleaseManifestEntry:
        return self.manifest.stage_bytes(
            self.raw_root,
            source,
            dataset,
            filename,
            response.content,
            url=url,
            release_date=release_date,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            applicable_origins=applicable_origins,
            content_type=response.headers.get("content-type"),
            notes=notes,
        )


class BEASourceClient(_BaseSourceClient):
    """Minimal BEA API client with raw staging."""

    base_url = "https://apps.bea.gov/api/data"

    def __init__(
        self,
        raw_root: str | Path,
        manifest: ReleaseManifest,
        *,
        api_key: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        super().__init__(Path(raw_root), manifest, timeout_seconds=timeout_seconds)
        self.api_key = api_key or os.environ.get("BEA_API_KEY")

    def fetch_dataset(
        self,
        dataset_name: str,
        params: Mapping[str, Any],
        *,
        filename: str,
        release_date: str | None = None,
        coverage_start: str | None = None,
        coverage_end: str | None = None,
        applicable_origins: list[str] | None = None,
    ) -> ReleaseManifestEntry:
        request_params = {
            "UserID": self.api_key,
            "method": "GetData",
            "datasetname": dataset_name,
            "ResultFormat": "json",
        }
        request_params.update(params)
        response = self._get(self.base_url, params=request_params)
        return self._stage_response(
            source="bea",
            dataset=dataset_name,
            filename=filename,
            url=response.url,
            response=response,
            release_date=release_date,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            applicable_origins=applicable_origins,
        )


class CensusAPIClient(_BaseSourceClient):
    """Census API downloader with raw staging."""

    base_url = "https://api.census.gov/data"

    def fetch_dataset(
        self,
        dataset_path: str,
        params: Mapping[str, Any],
        *,
        filename: str,
        release_date: str | None = None,
        coverage_start: str | None = None,
        coverage_end: str | None = None,
        applicable_origins: list[str] | None = None,
    ) -> ReleaseManifestEntry:
        url = f"{self.base_url.rstrip('/')}/{dataset_path.lstrip('/')}"
        response = self._get(url, params=params)
        return self._stage_response(
            source="census",
            dataset=dataset_path,
            filename=filename,
            url=response.url,
            response=response,
            release_date=release_date,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            applicable_origins=applicable_origins,
        )


class FederalReserveSourceClient(_BaseSourceClient):
    """Downloader for Z.1 and other Fed data files."""

    def fetch_file(
        self,
        url: str,
        *,
        dataset: str,
        filename: str,
        release_date: str | None = None,
        coverage_start: str | None = None,
        coverage_end: str | None = None,
        applicable_origins: list[str] | None = None,
    ) -> ReleaseManifestEntry:
        response = self._get(url)
        return self._stage_response(
            source="fed",
            dataset=dataset,
            filename=filename,
            url=response.url,
            response=response,
            release_date=release_date,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            applicable_origins=applicable_origins,
        )


class FREDRealtimeSourceClient(_BaseSourceClient):
    """FRED/ALFRED series-observations client with realtime support."""

    base_url = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(
        self,
        raw_root: str | Path,
        manifest: ReleaseManifest,
        *,
        api_key: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        super().__init__(Path(raw_root), manifest, timeout_seconds=timeout_seconds)
        self.api_key = api_key or os.environ.get("FRED_API_KEY")

    def fetch_series(
        self,
        series_id: str,
        *,
        filename: str,
        start_date: str,
        end_date: str,
        realtime_end: str,
        realtime_start: str | None = None,
        applicable_origins: list[str] | None = None,
    ) -> ReleaseManifestEntry:
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": start_date,
            "observation_end": end_date,
            "realtime_end": realtime_end,
        }
        if realtime_start is not None:
            params["realtime_start"] = realtime_start
        response = self._get(self.base_url, params=params)
        return self._stage_response(
            source="fred",
            dataset=series_id,
            filename=filename,
            url=response.url,
            response=response,
            release_date=realtime_end,
            coverage_start=start_date,
            coverage_end=end_date,
            applicable_origins=applicable_origins,
        )


class OECDSourceClient(_BaseSourceClient):
    """OECD SDMX/data download helper."""

    def fetch_file(
        self,
        url: str,
        *,
        dataset: str,
        filename: str,
        release_date: str | None = None,
        coverage_start: str | None = None,
        coverage_end: str | None = None,
        applicable_origins: list[str] | None = None,
    ) -> ReleaseManifestEntry:
        response = self._get(url)
        return self._stage_response(
            source="oecd",
            dataset=dataset,
            filename=filename,
            url=response.url,
            response=response,
            release_date=release_date,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            applicable_origins=applicable_origins,
        )
