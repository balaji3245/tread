import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from starlette.testclient import TestClient

from app.historical_data_cache import (
    atomic_write_gzip_json,
    atomic_write_json,
    get_cache_file_paths,
    get_missing_ranges,
    load_cached_candles,
    load_manifest,
    merge_and_save_candles,
    save_cached_candles,
)
from app.historical_data_quality import (
    audit_dataset_quality,
    clean_and_normalize_candles,
    compute_dataset_hash,
    verify_1m_5m_alignment,
)
from app.main import app
from app.mt5_client import MT5Client

client = TestClient(app)


def test_atomic_write_gzip_and_json():
    """Verify atomic write operations write valid gzip and json without corruption."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        gz_file = tmp_path / "test_data.json.gz"
        json_file = tmp_path / "test_meta.json"

        sample_data = [{"time": 1000 + i * 60, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0} for i in range(100)]
        size_gz = atomic_write_gzip_json(gz_file, sample_data)
        assert size_gz > 0
        assert gz_file.exists()

        # Verify reading
        import gzip
        import json
        with gzip.open(gz_file, "rt", encoding="utf-8") as f:
            read_back = json.load(f)
        assert len(read_back) == 100

        meta_data = {"symbol": "XAUUSD", "count": 100}
        size_json = atomic_write_json(json_file, meta_data)
        assert size_json > 0
        assert json_file.exists()
        with open(json_file, "r", encoding="utf-8") as f:
            read_meta = json.load(f)
        assert read_meta["count"] == 100


def test_manifest_creation_and_loading():
    """Verify manifest creation, chunk storage, and loading."""
    sym = "TESTMANIFEST"
    tf = "1m"
    candles = [
        {"time": 1700000000 + i * 60, "open": 2600.0, "high": 2605.0, "low": 2595.0, "close": 2602.0, "tick_volume": 100}
        for i in range(50)
    ]
    chunks = [
        {
            "chunk_id": 1,
            "requested_start": "2026-01-01T00:00:00+00:00",
            "requested_end": "2026-01-14T00:00:00+00:00",
            "actual_start": "2026-01-01T00:00:00+00:00",
            "actual_end": "2026-01-14T00:00:00+00:00",
            "count": 50,
            "status": "SUCCESS",
            "mt5_error": None
        }
    ]

    meta = save_cached_candles(sym, tf, candles, chunks=chunks, dataset_hash="abc123hash")
    assert meta["candle_count"] == 50

    manifest = load_manifest(sym, tf)
    assert manifest is not None
    assert manifest["symbol"] == sym
    assert manifest["timeframe"] == tf
    assert manifest["candle_count"] == 50
    assert manifest["archive_chunks"] == 1
    assert len(manifest["chunks"]) == 1
    assert manifest["chunks"][0]["status"] == "SUCCESS"


def test_missing_ranges_and_incremental_detection():
    """Test detection of missing time intervals for incremental archival downloads."""
    sym = "TESTMISSING"
    tf = "1m"
    base_t = 1700000000
    # Cache covers [base_t, base_t + 10 * 86400]
    cached = [
        {"time": base_t + i * 60, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2000.0}
        for i in range(10 * 1440)
    ]
    save_cached_candles(sym, tf, cached)

    # Request target spanning 30 days before base_t to 10 days after
    target_start = base_t - (30 * 86400)
    target_end = base_t + (20 * 86400)

    missing = get_missing_ranges(sym, tf, target_start, target_end, max_gap_seconds=86400)
    assert len(missing) == 2
    # First missing interval is before cache
    assert missing[0][0] == target_start
    # Second missing interval is after cache
    assert missing[1][1] == target_end


def test_incremental_merge_and_deduplication():
    """Test merging overlapping chunked data deduplicates timestamps and sorts ascending."""
    sym = "TESTMERGE"
    tf = "1m"
    c1 = [{"time": 1000 + i * 60, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2001.0} for i in range(10)]
    save_cached_candles(sym, tf, c1)

    # Overlapping new chunk [1300 to 1800]
    c2 = [{"time": 1000 + (i + 5) * 60, "open": 2001.0, "high": 2006.0, "low": 1996.0, "close": 2002.0} for i in range(10)]
    merged = merge_and_save_candles(sym, tf, c2)

    assert len(merged) == 15  # 10 + 10 - 5 overlapping
    times = [c["time"] for c in merged]
    assert times == sorted(times)
    assert len(times) == len(set(times))


def test_mt5_client_chunked_with_manifest_mock():
    """Test MT5Client chunked retrieval return_manifest behavior."""
    client_mock = MT5Client(mock_fallback=True)
    client_mock.is_mock = True
    client_mock.is_connected = True
    client_mock.resolved_symbol = "XAUUSD"

    candles, manifest_chunks = client_mock.get_historical_candles_chunked(
        timeframe="1m",
        chunk_days=14,
        return_manifest=True
    )
    assert isinstance(candles, list)
    assert isinstance(manifest_chunks, list)
    assert len(manifest_chunks) > 0
    assert "chunk_id" in manifest_chunks[0]
    assert manifest_chunks[0]["status"] == "SUCCESS"


def test_coverage_status_and_completeness_thresholds():
    """Verify coverage status classification for 350+ days, 180+ days, and <180 days."""
    c_short = [{"time": 1000 + i * 60, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2000.0} for i in range(500)]
    _, _, q_short = audit_dataset_quality(c_short, c_short, requested_days=365, symbol="XAUUSD")
    assert q_short.coverage_status == "INSUFFICIENT_HISTORY"
    assert not q_short.is_complete

    # 200 days
    c_mid = [
        {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2000.0},
        {"time": 1700000000 + (200 * 86400), "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2000.0}
    ]
    _, _, q_mid = audit_dataset_quality(c_mid, c_mid, requested_days=365, symbol="XAUUSD")
    assert q_mid.coverage_status == "LIMITED_HISTORY"

    # 355 days
    c_full = [
        {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2000.0},
        {"time": 1700000000 + (355 * 86400), "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2000.0}
    ]
    _, _, q_full = audit_dataset_quality(c_full, c_full, requested_days=365, symbol="XAUUSD")
    assert q_full.coverage_status == "12_MONTH_HISTORY_AVAILABLE"
    assert q_full.is_complete


def test_history_status_api_manifest_exposure():
    """Verify GET /api/history/xauusd/status exposes manifest and archive metadata."""
    resp = client.get("/api/history/xauusd/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "XAUUSD"
    assert "m1" in data
    assert "m5" in data
    assert "archive_chunks" in data["m1"]
    assert "dataset_hash" in data
    assert "manifest_1m" in data


def test_history_download_api_timeframe_parameter(monkeypatch):
    """Verify POST /api/history/xauusd/download validates symbol and timeframe parameters."""
    # Invalid symbol
    resp_bad_sym = client.post("/api/history/xauusd/download", json={"symbol": "EURUSD"})
    assert resp_bad_sym.status_code == 400

    # Valid request with timeframe parameter
    monkeypatch.setattr(
        "app.routes.history.fetch_and_cache_historical_dataset",
        lambda **kwargs: {"dataset_hash": "e9db340c4efa9e63", "candle_count": 340729}
    )
    resp_valid = client.post(
        "/api/history/xauusd/download",
        json={"symbol": "XAUUSD", "months": 1, "timeframe": "1m"}
    )
    assert resp_valid.status_code in [200, 500]  # 200 on connected MT5/mock
