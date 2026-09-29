import pytest
from app.historical_data_quality import (
    analyze_market_gaps,
    audit_dataset_quality,
    clean_and_normalize_candles,
    compute_dataset_hash,
    validate_ohlc_candle,
    verify_1m_5m_alignment,
)


def test_validate_ohlc_candle_valid():
    valid_candle = {
        "time": 1700000000,
        "open": 2000.0,
        "high": 2010.0,
        "low": 1995.0,
        "close": 2005.0,
        "tick_volume": 100
    }
    is_valid, err = validate_ohlc_candle(valid_candle)
    assert is_valid is True
    assert err is None


def test_validate_ohlc_candle_invalid():
    # High < Low
    c_bad_hl = {"time": 1700000000, "open": 2000.0, "high": 1990.0, "low": 2005.0, "close": 2000.0}
    is_valid, err = validate_ohlc_candle(c_bad_hl)
    assert is_valid is False
    assert "High < Low" in err

    # High < Open
    c_bad_ho = {"time": 1700000000, "open": 2020.0, "high": 2010.0, "low": 2000.0, "close": 2005.0}
    is_valid, err = validate_ohlc_candle(c_bad_ho)
    assert is_valid is False

    # Low > Close
    c_bad_lc = {"time": 1700000000, "open": 2005.0, "high": 2010.0, "low": 2000.0, "close": 1995.0}
    is_valid, err = validate_ohlc_candle(c_bad_lc)
    assert is_valid is False

    # Negative / Zero Price
    c_neg = {"time": 1700000000, "open": -10.0, "high": 2010.0, "low": 1995.0, "close": 2005.0}
    is_valid, err = validate_ohlc_candle(c_neg)
    assert is_valid is False


def test_clean_and_normalize_candles():
    raw = [
        {"time": 1700000060, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},
        {"time": 1700000000, "open": 1998.0, "high": 2001.0, "low": 1997.0, "close": 2000.0},
        {"time": 1700000060, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},  # Duplicate
        {"time": 1700000120, "open": -5.0, "high": 2005.0, "low": 1995.0, "close": 2002.0},    # Invalid
    ]
    cleaned, inv_count, dup_count, nonmono_count = clean_and_normalize_candles(raw, "1m")
    assert len(cleaned) == 2
    assert inv_count == 1
    assert dup_count == 1
    assert nonmono_count == 1
    assert cleaned[0]["time"] == 1700000000
    assert cleaned[1]["time"] == 1700000060


def test_analyze_market_gaps():
    # Friday 21:00 UTC (1700254800) to Sunday 22:00 UTC (1700431200) -> Weekend gap
    weekend_c = [
        {"time": 1700254800, "open": 2000, "high": 2005, "low": 1995, "close": 2000},
        {"time": 1700431200, "open": 2000, "high": 2005, "low": 1995, "close": 2000}
    ]
    unexp, exp = analyze_market_gaps(weekend_c)
    assert exp == 1
    assert unexp == 0

    # Tuesday 14:00 UTC to Tuesday 15:00 UTC -> Unexpected gap during active session
    intraday_c = [
        {"time": 1700575200, "open": 2000, "high": 2005, "low": 1995, "close": 2000},
        {"time": 1700578800, "open": 2000, "high": 2005, "low": 1995, "close": 2000}
    ]
    unexp, exp = analyze_market_gaps(intraday_c)
    assert unexp == 1


def test_verify_1m_5m_alignment():
    c1 = [{"time": 1700000000, "open": 2000, "high": 2005, "low": 1995, "close": 2000},
          {"time": 1700003600, "open": 2000, "high": 2005, "low": 1995, "close": 2000}]
    c5 = [{"time": 1700000000, "open": 2000, "high": 2005, "low": 1995, "close": 2000},
          {"time": 1700003600, "open": 2000, "high": 2005, "low": 1995, "close": 2000}]
    status, detail = verify_1m_5m_alignment(c1, c5)
    assert status == "PASS"


def test_compute_dataset_hash_deterministic():
    c1 = [{"time": 1700000000, "open": 2000.5, "high": 2005.0, "low": 1995.0, "close": 2002.3}]
    c5 = [{"time": 1700000000, "open": 2000.5, "high": 2008.0, "low": 1992.0, "close": 2004.1}]
    h1 = compute_dataset_hash(c1, c5)
    h2 = compute_dataset_hash(c1, c5)
    assert h1 == h2
    assert len(h1) == 16
