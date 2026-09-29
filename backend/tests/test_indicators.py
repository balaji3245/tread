import pytest
from app.indicators import (
    calculate_ema_series,
    get_latest_ema,
    calculate_rsi_series,
    get_latest_rsi,
    calculate_macd,
    calculate_atr_series,
    get_latest_atr,
    calculate_vwap,
    detect_swings,
    analyze_market_structure,
    detect_support_resistance,
)


def test_ema_calculation():
    prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0]
    period = 5
    ema_series = calculate_ema_series(prices, period)

    assert len(ema_series) == len(prices)
    assert ema_series[0] is None
    assert ema_series[3] is None
    # First EMA is SMA of first 5: (10+11+12+13+14)/5 = 12.0
    assert ema_series[4] == 12.0
    # Multiplier = 2 / (5 + 1) = 1/3
    # Next EMA = 15.0 * (1/3) + 12.0 * (2/3) = 5.0 + 8.0 = 13.0
    assert ema_series[5] == 13.0

    # Insufficient data
    assert calculate_ema_series([10.0, 11.0], 5) == [None, None]


def test_rsi_calculation():
    # 15 periods of strictly rising prices -> RSI should approach 100
    rising_prices = [100.0 + i * 2.0 for i in range(20)]
    rsi_series = calculate_rsi_series(rising_prices, period=14)
    assert rsi_series[-1] == 100.0

    # 15 periods of strictly falling prices -> RSI should approach 0
    falling_prices = [200.0 - i * 2.0 for i in range(20)]
    rsi_falling = calculate_rsi_series(falling_prices, period=14)
    assert rsi_falling[-1] == 0.0

    # Alternating prices
    alt_prices = [100.0 if i % 2 == 0 else 102.0 for i in range(30)]
    rsi_alt = calculate_rsi_series(alt_prices, period=14)
    assert rsi_alt[-1] is not None
    assert 40.0 <= rsi_alt[-1] <= 60.0


def test_macd_calculation():
    candles = []
    base = 2000.0
    for i in range(50):
        # Gradual uptrend
        price = base + i * 1.5
        candles.append({
            "time": 1700000000 + i * 60,
            "open": price - 0.5,
            "high": price + 1.0,
            "low": price - 1.0,
            "close": price
        })

    macd_res = calculate_macd(candles, 12, 26, 9)
    assert macd_res.macd is not None
    assert macd_res.signal is not None
    assert macd_res.histogram is not None
    # In uptrend, Fast EMA > Slow EMA -> MACD > 0
    assert macd_res.macd > 0
    assert round(macd_res.macd - macd_res.signal, 4) == macd_res.histogram

    # Insufficient candles
    empty_res = calculate_macd(candles[:20], 12, 26, 9)
    assert empty_res.macd is None


def test_atr_calculation():
    candles = []
    for i in range(30):
        candles.append({
            "time": 1700000000 + i * 60,
            "open": 2000.0,
            "high": 2005.0,
            "low": 1995.0,  # Range is 10.0
            "close": 2000.0
        })

    atr = get_latest_atr(candles, period=14)
    assert atr is not None
    assert round(atr, 1) == 10.0


def test_vwap_calculation():
    # When volume is present
    candles_with_vol = [
        {"high": 102.0, "low": 98.0, "close": 100.0, "volume": 100},  # TP: 100 * 100 = 10000
        {"high": 104.0, "low": 100.0, "close": 102.0, "volume": 200}, # TP: 102 * 200 = 20400
    ]
    # Total TP*Vol = 30400, Total Vol = 300 -> VWAP = 30400 / 300 = 101.33
    vwap = calculate_vwap(candles_with_vol)
    assert vwap == 101.33

    # When volume is missing or 0 -> must explicitly return None
    candles_no_vol = [
        {"high": 102.0, "low": 98.0, "close": 100.0, "volume": 0},
        {"high": 104.0, "low": 100.0, "close": 102.0},
    ]
    assert calculate_vwap(candles_no_vol) is None


def test_market_structure_bullish_and_bearish():
    # Synthetic Bullish Structure: Higher Highs and Higher Lows
    bullish_candles = []
    prices = [
        100, 102, 105, 103, 101,  # Swing 1: High 105, Low 101
        104, 108, 110, 107, 105,  # Swing 2: High 110 (HH), Low 105 (HL)
        108, 112, 115, 113, 110,  # Swing 3: High 115 (HH), Low 110 (HL)
    ]
    for i, p in enumerate(prices):
        bullish_candles.append({
            "time": 1700000000 + i * 60,
            "open": p - 0.5,
            "high": p + 1.0,
            "low": p - 1.0,
            "close": p
        })

    struct_bull = analyze_market_structure(bullish_candles, lookback=1)
    assert struct_bull.structure == "BULLISH"
    assert struct_bull.higher_high is True
    assert struct_bull.higher_low is True

    # Synthetic Bearish Structure: Lower Highs and Lower Lows
    bearish_candles = []
    bear_prices = [
        150, 148, 145, 147, 149,
        146, 142, 140, 143, 144,
        141, 138, 135, 137, 139,
    ]
    for i, p in enumerate(bear_prices):
        bearish_candles.append({
            "time": 1700000000 + i * 60,
            "open": p + 0.5,
            "high": p + 1.0,
            "low": p - 1.0,
            "close": p
        })

    struct_bear = analyze_market_structure(bearish_candles, lookback=1)
    assert struct_bear.structure == "BEARISH"


def test_support_resistance_detection():
    candles = []
    # Create bouncing price pattern around 2000 support and 2050 resistance
    pattern = [2000, 2020, 2050, 2030, 2000, 2025, 2050, 2020, 2000, 2030, 2050, 2025]
    for i, p in enumerate(pattern):
        candles.append({
            "time": 1700000000 + i * 60,
            "open": p,
            "high": p + 2.0,
            "low": p - 2.0,
            "close": p
        })

    supports, resistances = detect_support_resistance(candles, current_price=2025.0, atr=5.0)
    assert len(supports) > 0 or len(resistances) > 0
