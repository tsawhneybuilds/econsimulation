"""
Unit tests for FREDLiveLoader.

File: tests/us/data_contracts/test_fred_loader.py

Run:
    pytest tests/us/data_contracts/test_fred_loader.py -v

The tests are grouped into two classes:
  TestFREDLiveLoaderUnit  – pure unit tests, no network, mock requests
  TestFREDLiveLoaderSmoke – live integration test, skipped unless FRED_API_KEY set
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.us.data_contracts.fred_loader import FREDLiveLoader, _MAP


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_response(observations: list[dict]) -> MagicMock:
    """Return a mock requests.Response whose .json() yields FRED-shaped data."""
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {"observations": observations}
    return mock


def _quarterly_obs(start: str = "2015-01-01", n: int = 20, value: float = 1.0) -> list[dict]:
    """Generate n quarterly FRED observation dicts starting at *start*."""
    dates = pd.date_range(start, periods=n, freq="QS")
    return [{"date": d.strftime("%Y-%m-%d"), "value": str(value + i * 0.1)} for i, d in enumerate(dates)]


def _monthly_obs(start: str = "2015-01-01", n: int = 60, value: float = 100.0) -> list[dict]:
    dates = pd.date_range(start, periods=n, freq="MS")
    return [{"date": d.strftime("%Y-%m-%d"), "value": str(value + i * 0.05)} for i, d in enumerate(dates)]


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestFREDLiveLoaderUnit:

    def _loader(self, vintage: str = "2019-12-31") -> FREDLiveLoader:
        return FREDLiveLoader(api_key="test_key_abc", vintage_date=vintage)

    # --- construction ---

    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("FRED_API_KEY", raising=False)
        with pytest.raises(ValueError, match="API key"):
            FREDLiveLoader(api_key=None, vintage_date="2019-12-31")

    def test_accepts_env_var_key(self, monkeypatch):
        monkeypatch.setenv("FRED_API_KEY", "env_key_xyz")
        loader = FREDLiveLoader(vintage_date="2019-12-31")
        assert loader.api_key == "env_key_xyz"

    def test_vintage_date_string_parsed(self):
        loader = self._loader("2019-06-30")
        assert loader.vintage_date == date(2019, 6, 30)

    # --- _fetch_series ---

    def test_fetch_series_parses_observations(self):
        loader = self._loader()
        obs = _quarterly_obs(n=8)
        with patch("requests.get", return_value=_make_fake_response(obs)):
            s = loader._fetch_series("GDPC1")
        assert isinstance(s, pd.Series)
        assert len(s) == 8

    def test_fetch_series_skips_missing_values(self):
        loader = self._loader()
        obs = _quarterly_obs(n=4)
        obs[1]["value"] = "."   # FRED missing-value sentinel
        obs[2]["value"] = ""
        with patch("requests.get", return_value=_make_fake_response(obs)):
            s = loader._fetch_series("GDPC1")
        assert len(s) == 2

    def test_fetch_series_raises_on_empty(self):
        loader = self._loader()
        with patch("requests.get", return_value=_make_fake_response([])):
            with pytest.raises(RuntimeError, match="Zero observations"):
                loader._fetch_series("GDPC1")

    def test_fetch_series_raises_on_bad_payload(self):
        mock = MagicMock()
        mock.raise_for_status.return_value = None
        mock.json.return_value = {"error_message": "bad series"}
        loader = self._loader()
        with patch("requests.get", return_value=mock):
            with pytest.raises(RuntimeError, match="Unexpected FRED response"):
                loader._fetch_series("GDPC1")

    def test_realtime_end_pinned_to_vintage(self):
        """Ensure realtime_end is sent so FRED returns vintage-consistent data."""
        loader = self._loader("2019-12-31")
        obs = _quarterly_obs(n=4)
        captured_params: dict = {}

        def fake_get(url, params, timeout):
            captured_params.update(params)
            return _make_fake_response(obs)

        with patch("requests.get", side_effect=fake_get):
            loader._fetch_series("GDPC1")

        assert captured_params["realtime_end"] == "2019-12-31"
        assert captured_params["observation_end"] == "2019-12-31"

    # --- _to_quarterly ---

    def test_to_quarterly_level_returns_period_index(self):
        raw = pd.Series(
            [1.0, 2.0, 3.0],
            index=pd.to_datetime(["2019-01-01", "2019-04-01", "2019-07-01"]),
        )
        result = FREDLiveLoader._to_quarterly(raw, "Q", "level")
        assert isinstance(result.index, pd.PeriodIndex)
        assert result.index.freqstr == "Q-DEC"

    def test_to_quarterly_monthly_mean(self):
        # 3 months → 1 quarter
        raw = pd.Series(
            [1.0, 2.0, 3.0],
            index=pd.to_datetime(["2019-01-01", "2019-02-01", "2019-03-01"]),
        )
        result = FREDLiveLoader._to_quarterly(raw, "M", "quarterly_mean")
        assert len(result) == 1
        assert abs(float(result.iloc[0]) - 2.0) < 1e-9

    def test_to_quarterly_qoq_ann(self):
        # 100 * (2/1 - 1) * 4 = 400
        raw = pd.Series(
            [1.0, 2.0],
            index=pd.to_datetime(["2018-12-31", "2019-03-31"]),
        )
        result = FREDLiveLoader._to_quarterly(raw, "Q", "qoq_ann")
        assert abs(float(result.iloc[-1]) - 400.0) < 1e-6

    def test_to_quarterly_bad_transform_raises(self):
        raw = pd.Series([1.0], index=pd.to_datetime(["2019-01-01"]))
        with pytest.raises(ValueError, match="Unknown transform"):
            FREDLiveLoader._to_quarterly(raw, "Q", "bogus_transform")

    # --- load() ---

    def _mock_all_series(self, series_ids: list[str]) -> dict:
        """Return a side_effect dict that feeds fake data for each fred_id."""
        from src.us.data_contracts.fred_loader import _MAP
        responses = {}
        for sid in series_ids:
            if sid not in _MAP:
                continue
            fred_id, src_freq, _ = _MAP[sid]
            if src_freq == "Q":
                obs = _quarterly_obs(n=20)
            elif src_freq == "M":
                obs = _monthly_obs(n=60)
            else:
                obs = _monthly_obs(n=200)  # weekly proxy
            responses[fred_id] = _make_fake_response(obs)
        return responses

    def test_load_returns_period_index_dataframe(self):
        loader = self._loader()
        series_ids = ["GDPC1", "UNRATE", "FEDFUNDS"]
        responses = self._mock_all_series(series_ids)

        def fake_get(url, params, timeout):
            return responses[params["series_id"]]

        with patch("requests.get", side_effect=fake_get):
            df = loader.load(series_ids)

        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.PeriodIndex)
        assert set(series_ids).issubset(set(df.columns))

    def test_load_vintage_mask_applied(self):
        loader = self._loader("2019-12-31")
        series_ids = ["GDPC1"]
        responses = self._mock_all_series(series_ids)

        def fake_get(url, params, timeout):
            return responses[params["series_id"]]

        with patch("requests.get", side_effect=fake_get):
            df = loader.load(series_ids)

        cutoff = pd.Period("2019Q4", freq="Q")
        assert df.index[-1] <= cutoff, "Data after vintage_date leaked into dataset"

    def test_load_skips_unmapped_series_with_warning(self, caplog):
        import logging
        loader = self._loader()
        series_ids = ["GDPC1", "NONEXISTENT_SERIES_XYZ"]
        responses = self._mock_all_series(["GDPC1"])

        def fake_get(url, params, timeout):
            return responses.get(params["series_id"], _make_fake_response(_quarterly_obs()))

        with patch("requests.get", side_effect=fake_get):
            with caplog.at_level(logging.WARNING):
                df = loader.load(series_ids)

        assert "NONEXISTENT_SERIES_XYZ" in caplog.text
        assert "GDPC1" in df.columns
        assert "NONEXISTENT_SERIES_XYZ" not in df.columns

    def test_load_raises_when_all_series_fail(self):
        loader = self._loader()

        def fake_get(url, params, timeout):
            raise ConnectionError("network down")

        with patch("requests.get", side_effect=fake_get):
            with pytest.raises(RuntimeError, match="No series could be loaded"):
                loader.load(["GDPC1", "UNRATE"])

    def test_load_raises_without_requests_installed(self, monkeypatch):
        loader = self._loader()
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("No module named 'requests'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="pip install requests"):
                loader.load(["GDPC1"])


# ---------------------------------------------------------------------------
# Integration / smoke test (network, skipped without key)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("FRED_API_KEY"),
    reason="FRED_API_KEY not set — skipping live integration test",
)
class TestFREDLiveLoaderSmoke:
    """Hits the real FRED API.  Requires FRED_API_KEY env var."""

    def test_live_fetch_gdpc1(self):
        loader = FREDLiveLoader(vintage_date="2019-12-31", start_date="2010-01-01")
        df = loader.load(["GDPC1", "GDPC1_GROWTH", "UNRATE", "FEDFUNDS", "CPIAUCSL"])

        assert len(df) >= 20, "Expected at least 20 quarters of data"
        assert df.index[-1] <= pd.Period("2019Q4", freq="Q")
        assert df["GDPC1"].dropna().iloc[-1] > 10_000, "Real GDP should be >10k bn"
        assert 0 < df["UNRATE"].dropna().iloc[-1] < 20, "Unemployment rate sanity check"

    def test_live_vintage_pin(self):
        """Data available as of 2019Q4 should not appear in 2018Q4 vintage."""
        loader_2018 = FREDLiveLoader(vintage_date="2018-12-31", start_date="2010-01-01")
        df_2018 = loader_2018.load(["GDPC1"])
        assert df_2018.index[-1] <= pd.Period("2018Q4", freq="Q")
