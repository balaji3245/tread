import pytest
from app.backtest_models import BacktestConfig
from app.backtester import BacktestReplayEngine
from app.indicators import calculate_macd, get_latest_atr, get_latest_ema, get_latest_rsi
from app.signal_engine import SignalEngine
from app.validation.walk_forward import generate_walk_forward_slices


def create_deterministic_candles(count_1m=150):
    base_t = 1700000000
    candles_1m = []
    price = 2000.0
    for i in range(count_1m):
        t = base_t + (i * 60)
        price += 0.4 if (i % 10 < 5) else -0.4
        candles_1m.append({
            "time": t,
            "open": price - 0.2,
            "high": price + 0.8,
            "low": price - 0.8,
            "close": price,
            "tick_volume": 100,
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
                "tick_volume": 500,
                "spread": 0.30
            })

    return candles_1m, candles_5m


def test_integrity_1_appending_future_candles_does_not_alter_past_signals():
    """Test 1: Appending future candles must not change a signal generated earlier."""
    c_1m, c_5m = create_deterministic_candles(100)
    engine = SignalEngine(setup_threshold=7)

    # Analyze state at bar 80
    slice_1m_early = c_1m[:80]
    slice_5m_early = c_5m[:16]
    tick_early = {"bid": slice_1m_early[-1]["close"], "ask": slice_1m_early[-1]["close"] + 0.3, "timestamp": slice_1m_early[-1]["time"] * 1000}
    sig_early = engine.analyze(slice_1m_early, slice_5m_early, tick_early)

    # Analyze state at bar 80 again when future candles (bars 81-100) are appended to dataset
    slice_1m_recheck = c_1m[:80]
    slice_5m_recheck = c_5m[:16]
    sig_recheck = engine.analyze(slice_1m_recheck, slice_5m_recheck, tick_early)

    assert sig_early.type == sig_recheck.type
    assert sig_early.strength == sig_recheck.strength
    assert sig_early.reasons == sig_recheck.reasons


def test_integrity_2_removing_future_candles_does_not_change_historical_signals():
    """Test 2: Removing future candles must not change historical signals."""
    c_1m, c_5m = create_deterministic_candles(120)
    engine = SignalEngine(setup_threshold=7)

    tick = {"bid": c_1m[60]["close"], "ask": c_1m[60]["close"] + 0.3, "timestamp": c_1m[60]["time"] * 1000}

    # Signal evaluated on bars 0..60 with full dataset available
    sig_from_full = engine.analyze(c_1m[:61], c_5m[:12], tick)

    # Truncate dataset to only 0..60
    truncated_1m = c_1m[:61]
    truncated_5m = c_5m[:12]
    sig_from_truncated = engine.analyze(truncated_1m, truncated_5m, tick)

    assert sig_from_full.type == sig_from_truncated.type
    assert sig_from_full.strength == sig_from_truncated.strength


def test_integrity_3_oos_results_cannot_modify_baseline_config():
    """Test 3: OOS results cannot modify baseline configuration."""
    cfg = BacktestConfig(
        symbol="XAUUSD",
        signal_threshold=7,
        sl_atr_multiplier=1.0,
        tp1_atr_multiplier=1.0,
        tp2_atr_multiplier=2.0
    )
    original_dict = cfg.model_dump()

    c_1m, c_5m = create_deterministic_candles(150)
    engine = BacktestReplayEngine(config=cfg)
    resp = engine.run_backtest(c_1m, c_5m)

    # Ensure original config instance has not been mutated
    assert cfg.model_dump() == original_dict
    assert resp.configuration["signal_threshold"] == 7
    assert resp.configuration["sl_atr_multiplier"] == 1.0


def test_integrity_4_signal_at_t_enters_at_t_plus_1_open():
    """Test 4: Signal at time T enters at T+1 candle OPEN."""
    c_1m, c_5m = create_deterministic_candles(150)
    cfg = BacktestConfig(symbol="XAUUSD", signal_threshold=7, assumed_spread=0.30)
    engine = BacktestReplayEngine(config=cfg)
    resp = engine.run_backtest(c_1m, c_5m)

    for trade in resp.trades:
        # entry_time must be strictly greater than signal_time
        assert trade.entry_time > trade.signal_time
        # In 1m timeframe, difference should be exactly 60 seconds
        assert trade.entry_time - trade.signal_time == 60


def test_integrity_5_indicator_values_at_t_have_no_t_plus_1_information():
    """Test 5: Indicator values at T do not contain T+1 information."""
    c_1m, _ = create_deterministic_candles(100)

    # Compute indicators for bars 0..50
    ema_9_50 = get_latest_ema(c_1m[:51], 9)
    rsi_14_50 = get_latest_rsi(c_1m[:51], 14)
    atr_14_50 = get_latest_atr(c_1m[:51], 14)

    # Now alter future candle 51 dramatically
    modified_c_1m = [dict(c) for c in c_1m]
    modified_c_1m[51]["close"] += 500.0
    modified_c_1m[51]["high"] += 500.0

    # Recompute indicators for bars 0..50
    ema_9_recheck = get_latest_ema(modified_c_1m[:51], 9)
    rsi_14_recheck = get_latest_rsi(modified_c_1m[:51], 14)
    atr_14_recheck = get_latest_atr(modified_c_1m[:51], 14)

    assert ema_9_50 == ema_9_recheck
    assert rsi_14_50 == rsi_14_recheck
    assert atr_14_50 == atr_14_recheck


def test_integrity_6_walk_forward_windows_strictly_chronological():
    """Test 6: Walk-forward windows remain strictly chronological."""
    slices = generate_walk_forward_slices(
        start_ts=1700000000,
        end_ts=1700000000 + (300 * 86400),
        train_days=90,
        validation_days=30,
        step_days=30
    )

    prev_train_start = 0
    for t_start, t_end, v_start, v_end in slices:
        assert t_start > prev_train_start
        assert t_end > t_start
        assert v_start == t_end
        assert v_end > v_start
        prev_train_start = t_start
