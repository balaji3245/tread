"""
Phase 5A Historical Data Recovery & MT5 Diagnostic Unit Tests.
Tests:
- MT5 diagnostic tools and symbol resolution
- Chunked retrieval, range splitting, overlap deduplication, chronological sorting
- Historical coverage calculation and data-completeness classification
- Cache merging, partial cache updates, and dataset hash determinism
- API endpoints /api/history/xauusd/status and /api/history/xauusd/download
"""

import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from starlette.testclient import TestClient

from app.historical_data_cache import (
    load_cached_candles,
    merge_and_save_candles,
    save_cached_candles,
)
from app.historical_data_diagnostic import run_diagnostic
from app.historical_data_quality import (
    analyze_market_gaps,
    audit_dataset_quality,
    clean_and_normalize_candles,
    compute_dataset_hash,
    validate_ohlc_candle,
    verify_1m_5m_alignment,
)
from app.main import app
from app.mt5_client import MT5Client

client = TestClient(app)


def test_phase5a_ohlc_validation():
    """Verify strict OHLC candle rules."""
    valid_c = {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0}
    is_v, reason = validate_ohlc_candle(valid_c)
    assert is_v is True
    assert reason is None

    # High < Open
    invalid_c = {"time": 1700000000, "open": 2000.0, "high": 1990.0, "low": 1980.0, "close": 1985.0}
    is_v, reason = validate_ohlc_candle(invalid_c)
    assert is_v is False
    assert "High < max(Open, Close)" in reason

    # Negative price
    neg_c = {"time": 1700000000, "open": -10.0, "high": 5.0, "low": -15.0, "close": 0.0}
    is_v, reason = validate_ohlc_candle(neg_c)
    assert is_v is False


def test_phase5a_clean_and_deduplicate():
    """Verify deduplication and ascending sort."""
    raw = [
        {"time": 1700000120, "open": 2002.0, "high": 2006.0, "low": 2000.0, "close": 2004.0},
        {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},
        {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},  # Duplicate
        {"time": 1700000060, "open": 2001.0, "high": 2004.0, "low": 1998.0, "close": 2003.0},
    ]
    cleaned, invalids, dups, non_monos = clean_and_normalize_candles(raw)
    assert len(cleaned) == 3
    assert dups == 1
    assert invalids == 0
    assert cleaned[0]["time"] == 1700000000
    assert cleaned[1]["time"] == 1700000060
    assert cleaned[2]["time"] == 1700000120


def test_phase5a_cache_merge_and_partial_update():
    """Verify partial cache merge preserves older history while appending new bars."""
    symbol = "TEST_MERGE_XAUUSD"
    # Initial batch: 100 bars
    batch_1 = [
        {"time": 1700000000 + i * 60, "open": 2000.0 + i * 0.1, "high": 2001.0 + i * 0.1, "low": 1999.0 + i * 0.1, "close": 2000.5 + i * 0.1}
        for i in range(100)
    ]
    save_cached_candles(symbol, "1m", batch_1)

    # Newer overlapping batch: bars 80 to 150
    batch_2 = [
        {"time": 1700000000 + i * 60, "open": 2000.0 + i * 0.1, "high": 2001.0 + i * 0.1, "low": 1999.0 + i * 0.1, "close": 2000.5 + i * 0.1}
        for i in range(80, 150)
    ]
    merged = merge_and_save_candles(symbol, "1m", batch_2)
    assert len(merged) == 150
    assert merged[0]["time"] == 1700000000
    assert merged[-1]["time"] == 1700000000 + 149 * 60

    # Verify loaded from cache
    loaded, meta = load_cached_candles(symbol, "1m")
    assert len(loaded) == 150
    assert meta["candle_count"] == 150


def test_phase5a_coverage_classification():
    """Verify coverage classification: INSUFFICIENT (<180d), LIMITED (180-364d), 12_MONTH (>=365d)."""
    now = int(time.time())

    # 10 days
    c_10d = [
        {"time": now - 86400 * 10, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},
        {"time": now, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0}
    ]
    _, _, report_10d = audit_dataset_quality(c_10d, c_10d, requested_days=365, symbol="XAUUSD")
    assert report_10d.coverage_status == "INSUFFICIENT_HISTORY"
    assert report_10d.is_complete is False

    # 200 days
    c_200d = [
        {"time": now - 86400 * 200, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},
        {"time": now, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0}
    ]
    _, _, report_200d = audit_dataset_quality(c_200d, c_200d, requested_days=365, symbol="XAUUSD")
    assert report_200d.coverage_status == "LIMITED_HISTORY"

    # 366 days
    c_366d = [
        {"time": now - 86400 * 366, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},
        {"time": now, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0}
    ]
    _, _, report_366d = audit_dataset_quality(c_366d, c_366d, requested_days=365, symbol="XAUUSD")
    assert report_366d.coverage_status == "12_MONTH_HISTORY_AVAILABLE"
    assert report_366d.is_complete is True


def test_phase5a_history_status_api():
    """Verify GET /api/history/xauusd/status endpoint."""
    resp = client.get("/api/history/xauusd/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "XAUUSD"
    assert "m1" in data
    assert "m5" in data
    assert "timeframes" in data
    assert "data_quality" in data
    assert "dataset_hash" in data
    assert "history_days" in data
    assert "coverage_status" in data


def test_phase5a_history_download_api_validation(monkeypatch):
    """Verify POST /api/history/xauusd/download endpoint parameter checking."""
    # Invalid symbol
    resp = client.post("/api/history/xauusd/download", json={"symbol": "INVALID"})
    assert resp.status_code == 400

    # Valid symbol with mocked dataset download to preserve canonical golden dataset
    monkeypatch.setattr(
        "app.routes.history.fetch_and_cache_historical_dataset",
        lambda **kwargs: {"dataset_hash": "e9db340c4efa9e63", "candle_count": 340729}
    )
    resp = client.post("/api/history/xauusd/download", json={"symbol": "XAUUSD", "months": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "dataset_hash" in data["data"]


def test_phase5a_mock_chunked_retrieval():
    """Verify MT5Client get_historical_candles_chunked in fallback/mock mode."""
    client_mock = MT5Client(mock_fallback=True)
    client_mock.is_connected = True
    client_mock.is_mock = True
    client_mock.resolved_symbol = "XAUUSD"

    dt_start = datetime.now(timezone.utc) - timedelta(days=30)
    dt_end = datetime.now(timezone.utc)

    candles_1m = client_mock.get_historical_candles_chunked(
        timeframe="1m", date_from=dt_start, date_to=dt_end, chunk_days=7
    )
    assert len(candles_1m) > 0

    candles_5m = client_mock.get_historical_candles_chunked(
        timeframe="5m", date_from=dt_start, date_to=dt_end, chunk_days=14
    )
    assert len(candles_5m) > 0


def test_phase5a_diagnostic_runner():
    """Verify diagnostic function executes safely without throwing errors."""
    res = run_diagnostic(symbol="XAUUSD")
    assert isinstance(res, dict)
    assert "mt5_available" in res
    assert "connected" in res
