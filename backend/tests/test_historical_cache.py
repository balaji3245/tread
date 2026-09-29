import os
import pytest
from app.historical_data_cache import (
    load_cached_candles,
    merge_and_save_candles,
    save_cached_candles,
)


def test_historical_cache_save_and_load(tmp_path, monkeypatch):
    # Patch DATA_DIR to temp directory
    import app.historical_data_cache as hdc
    monkeypatch.setattr(hdc, "DATA_DIR", tmp_path)

    candles_1m = [
        {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},
        {"time": 1700000060, "open": 2002.0, "high": 2008.0, "low": 2001.0, "close": 2007.0}
    ]

    meta = save_cached_candles("TEST_SYM", "1m", candles_1m)
    assert meta["candle_count"] == 2
    assert meta["symbol"] == "TEST_SYM"

    loaded_candles, loaded_meta = load_cached_candles("TEST_SYM", "1m")
    assert len(loaded_candles) == 2
    assert loaded_meta is not None
    assert loaded_meta["candle_count"] == 2
    assert loaded_candles[0]["time"] == 1700000000


def test_merge_and_save_candles(tmp_path, monkeypatch):
    import app.historical_data_cache as hdc
    monkeypatch.setattr(hdc, "DATA_DIR", tmp_path)

    initial_candles = [
        {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0}
    ]
    save_cached_candles("TEST_MERGE", "1m", initial_candles)

    new_candles = [
        {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},  # Duplicate
        {"time": 1700000060, "open": 2002.0, "high": 2008.0, "low": 2001.0, "close": 2007.0}
    ]

    merged = merge_and_save_candles("TEST_MERGE", "1m", new_candles)
    assert len(merged) == 2
    assert merged[0]["time"] == 1700000000
    assert merged[1]["time"] == 1700000060
