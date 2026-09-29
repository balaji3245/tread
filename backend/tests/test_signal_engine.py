import pytest
from app.signal_engine import SignalEngine


def generate_synthetic_candles(base_price: float, trend_direction: str, count: int = 70):
    candles = []
    current = base_price
    for i in range(count):
        if trend_direction == "up":
            # Wave structure: 4 steps up (+0.8), 1 step pullback (-0.3)
            drift = 0.8 if (i % 5 != 4) else -0.3
        elif trend_direction == "down":
            # Wave structure: 4 steps down (-0.8), 1 step pullback (+0.3)
            drift = -0.8 if (i % 5 != 4) else 0.3
        else:
            # Range oscillation: +/- 0.02
            drift = 0.02 if i % 2 == 0 else -0.02

        c_open = current
        c_close = current + drift
        c_high = max(c_open, c_close) + 0.35
        c_low = min(c_open, c_close) - 0.35

        candles.append({
            "time": 1700000000 + i * 60,
            "open": round(c_open, 2),
            "high": round(c_high, 2),
            "low": round(c_low, 2),
            "close": round(c_close, 2)
        })
        current = c_close

    return candles


def test_signal_engine_insufficient_data():
    engine = SignalEngine()
    signal = engine.analyze(candles_1m=[], candles_5m=[])
    assert signal.type == "WAIT"
    assert signal.strength == 0
    assert "Insufficient" in signal.reasons[0]


def test_signal_engine_bullish_setup():
    engine = SignalEngine(setup_threshold=7)
    # Generate 1m and 5m strong uptrend in wave expansion phase
    candles_1m = generate_synthetic_candles(2000.0, "up", count=73)
    candles_5m = generate_synthetic_candles(1950.0, "up", count=45)
    current_tick = {"bid": candles_1m[-1]["close"], "ask": candles_1m[-1]["close"] + 0.30}

    signal = engine.analyze(candles_1m, candles_5m, current_tick)
    assert signal.trend_5m == "BULLISH"
    assert signal.strength >= 7
    assert signal.type == "LONG_SETUP"
    assert len(signal.reasons) > 0


def test_signal_engine_bearish_setup():
    engine = SignalEngine(setup_threshold=7)
    # Generate 1m and 5m strong downtrend in wave expansion phase
    candles_1m = generate_synthetic_candles(2050.0, "down", count=73)
    candles_5m = generate_synthetic_candles(2100.0, "down", count=45)
    current_tick = {"bid": candles_1m[-1]["close"], "ask": candles_1m[-1]["close"] + 0.30}

    signal = engine.analyze(candles_1m, candles_5m, current_tick)
    assert signal.trend_5m == "BEARISH"
    assert signal.strength >= 7
    assert signal.type == "SHORT_SETUP"
    assert len(signal.reasons) > 0


def test_signal_engine_wait_condition_on_range():
    engine = SignalEngine(setup_threshold=7)
    # Flat / Sideways market
    candles_1m = generate_synthetic_candles(2000.0, "flat", count=70)
    candles_5m = generate_synthetic_candles(2000.0, "flat", count=40)
    current_tick = {"bid": 2000.0, "ask": 2000.30}

    signal = engine.analyze(candles_1m, candles_5m, current_tick)
    assert signal.type == "WAIT"
    assert signal.strength < 7


def test_signal_engine_conflicting_timeframes():
    engine = SignalEngine(setup_threshold=7)
    # 5m is strongly BULLISH, but 1m is crashing (BEARISH)
    candles_5m = generate_synthetic_candles(1900.0, "up", count=50)
    candles_1m = generate_synthetic_candles(2050.0, "down", count=70)
    current_tick = {"bid": candles_1m[-1]["close"], "ask": candles_1m[-1]["close"] + 0.30}

    signal = engine.analyze(candles_1m, candles_5m, current_tick)
    # Because 1m contradicts 5m, it MUST return WAIT
    assert signal.type == "WAIT"
    assert len(signal.warnings) > 0
