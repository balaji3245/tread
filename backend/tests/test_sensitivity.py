import pytest
from app.backtest_models import BacktestConfig
from app.validation.sensitivity import (
    run_exit_sensitivity,
    run_spread_sensitivity,
    run_threshold_sensitivity,
)


def create_synthetic_candle_streams(count_1m=300):
    base_t = 1700000000
    candles_1m = []
    price = 2000.0
    for i in range(count_1m):
        t = base_t + (i * 60)
        # Moderate cyclic movement
        change = 0.5 if (i % 20 < 10) else -0.5
        price += change
        candles_1m.append({
            "time": t,
            "open": price - 0.2,
            "high": price + 1.0,
            "low": price - 1.0,
            "close": price,
            "spread": 0.30
        })

    candles_5m = []
    for j in range(0, count_1m, 5):
        chunk = candles_1m[j:j+5]
        if chunk:
            candles_5m.append({
                "time": chunk[0]["time"],
                "open": chunk[0]["open"],
                "high": max(c["high"] for c in chunk),
                "low": min(c["low"] for c in chunk),
                "close": chunk[-1]["close"],
                "spread": 0.30
            })

    return candles_1m, candles_5m


def test_spread_sensitivity_matrix():
    c_1m, c_5m = create_synthetic_candle_streams(300)
    cfg = BacktestConfig(symbol="XAUUSD", signal_threshold=7)
    spread_values = [0.0, 0.30, 0.75]

    results = run_spread_sensitivity(c_1m, c_5m, cfg, spread_values)

    assert len(results) == len(spread_values)
    for idx, r in enumerate(results):
        assert r.spread == spread_values[idx]
        assert r.trades >= 0
        assert r.win_rate >= 0.0


def test_threshold_sensitivity_and_sample_warning():
    c_1m, c_5m = create_synthetic_candle_streams(300)
    cfg = BacktestConfig(symbol="XAUUSD")
    thresholds = [7, 8, 9, 10]

    results = run_threshold_sensitivity(c_1m, c_5m, cfg, thresholds, small_sample_threshold=50)

    assert len(results) == 4
    for r in results:
        assert r.threshold in thresholds
        if r.trades < 50:
            assert r.sample_size_warning is True
            assert "Small sample" in (r.sample_size_note or "")


def test_exit_sensitivity_cases():
    c_1m, c_5m = create_synthetic_candle_streams(300)
    cfg = BacktestConfig(symbol="XAUUSD")

    results = run_exit_sensitivity(c_1m, c_5m, cfg)

    assert len(results) == 5
    case_ids = [r.case_id for r in results]
    assert case_ids == ["Case A", "Case B", "Case C", "Case D", "Case E"]
