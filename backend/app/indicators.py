from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel

from app.signal_models import PriceLevel


class MACDResult(BaseModel):
    macd: Optional[float] = None
    signal: Optional[float] = None
    histogram: Optional[float] = None


class MarketStructureResult(BaseModel):
    structure: str  # "BULLISH" | "BEARISH" | "RANGE"
    higher_high: bool = False
    higher_low: bool = False
    lower_high: bool = False
    lower_low: bool = False
    last_swing_high: Optional[float] = None
    last_swing_low: Optional[float] = None


# ----------------------------------------------------------------------
# 1. EMA (Exponential Moving Average)
# ----------------------------------------------------------------------
def calculate_ema_series(prices: List[float], period: int) -> List[Optional[float]]:
    """
    Calculate full Exponential Moving Average (EMA) series.
    Returns list matching prices length, with None where data < period.
    """
    if len(prices) < period or period <= 0:
        return [None] * len(prices)

    ema_series: List[Optional[float]] = [None] * (period - 1)
    
    # Initialize first EMA with Simple Moving Average (SMA)
    sma = sum(prices[:period]) / period
    ema_series.append(round(sma, 4))
    
    multiplier = 2.0 / (period + 1.0)
    current_ema = sma

    for price in prices[period:]:
        current_ema = (price * multiplier) + (current_ema * (1.0 - multiplier))
        ema_series.append(round(current_ema, 4))

    return ema_series


def get_latest_ema(candles: List[Dict[str, Any]], period: int) -> Optional[float]:
    """Calculate the latest EMA value from a list of candles."""
    if not candles or len(candles) < period:
        return None
    prices = [float(c["close"]) for c in candles]
    series = calculate_ema_series(prices, period)
    return series[-1] if series and series[-1] is not None else None


# ----------------------------------------------------------------------
# 2. RSI (Relative Strength Index)
# ----------------------------------------------------------------------
def calculate_rsi_series(prices: List[float], period: int = 14) -> List[Optional[float]]:
    """
    Calculate RSI series using Wilder's standard smoothing method.
    """
    if len(prices) <= period or period <= 0:
        return [None] * len(prices)

    rsi_series: List[Optional[float]] = [None] * period
    gains: List[float] = []
    losses: List[float] = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(0.0, change))
        losses.append(max(0.0, -change))

    # Initial average gain & loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0.0:
        rsi_series.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_series.append(round(100.0 - (100.0 / (1.0 + rs)), 2))

    # Wilder's Smoothing for remaining
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0.0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi_series.append(round(rsi, 2))

    return rsi_series


def get_latest_rsi(candles: List[Dict[str, Any]], period: int = 14) -> Optional[float]:
    """Calculate latest RSI value."""
    if not candles or len(candles) <= period:
        return None
    prices = [float(c["close"]) for c in candles]
    series = calculate_rsi_series(prices, period)
    return series[-1] if series and series[-1] is not None else None


# ----------------------------------------------------------------------
# 3. MACD (Moving Average Convergence Divergence)
# ----------------------------------------------------------------------
def calculate_macd(
    candles: List[Dict[str, Any]],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> MACDResult:
    """
    Calculate latest MACD line, signal line, and histogram.
    """
    min_required = slow_period + signal_period
    if not candles or len(candles) < min_required:
        return MACDResult()

    prices = [float(c["close"]) for c in candles]
    fast_ema = calculate_ema_series(prices, fast_period)
    slow_ema = calculate_ema_series(prices, slow_period)

    # Calculate MACD line (Fast EMA - Slow EMA) where both exist
    macd_line: List[float] = []
    macd_indices: List[int] = []
    for i in range(len(prices)):
        if fast_ema[i] is not None and slow_ema[i] is not None:
            macd_line.append(fast_ema[i] - slow_ema[i])
            macd_indices.append(i)

    if len(macd_line) < signal_period:
        return MACDResult()

    signal_series = calculate_ema_series(macd_line, signal_period)
    latest_macd = macd_line[-1]
    latest_signal = signal_series[-1]

    if latest_signal is None:
        return MACDResult(macd=round(latest_macd, 4))

    histogram = latest_macd - latest_signal
    return MACDResult(
        macd=round(latest_macd, 4),
        signal=round(latest_signal, 4),
        histogram=round(histogram, 4)
    )


# ----------------------------------------------------------------------
# 4. ATR (Average True Range)
# ----------------------------------------------------------------------
def calculate_atr_series(candles: List[Dict[str, Any]], period: int = 14) -> List[Optional[float]]:
    """
    Calculate ATR series using Wilder's smoothing.
    """
    if not candles or len(candles) <= period or period <= 0:
        return [None] * len(candles)

    tr_list: List[float] = []
    # First candle TR is high - low
    tr_list.append(float(candles[0]["high"]) - float(candles[0]["low"]))

    for i in range(1, len(candles)):
        h = float(candles[i]["high"])
        l = float(candles[i]["low"])
        prev_c = float(candles[i - 1]["close"])
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        tr_list.append(tr)

    atr_series: List[Optional[float]] = [None] * (period - 1)
    # First ATR is simple average of first `period` TRs
    initial_atr = sum(tr_list[:period]) / period
    atr_series.append(round(initial_atr, 4))
    current_atr = initial_atr

    for tr in tr_list[period:]:
        current_atr = (current_atr * (period - 1) + tr) / period
        atr_series.append(round(current_atr, 4))

    return atr_series


def get_latest_atr(candles: List[Dict[str, Any]], period: int = 14) -> Optional[float]:
    """Calculate latest ATR value."""
    if not candles or len(candles) <= period:
        return None
    series = calculate_atr_series(candles, period)
    return series[-1] if series and series[-1] is not None else None


# ----------------------------------------------------------------------
# 5. Session-Aware VWAP
# ----------------------------------------------------------------------
def calculate_vwap(candles: List[Dict[str, Any]]) -> Optional[float]:
    """
    Calculate session-aware VWAP if real volume/tick_volume data is present.
    If volume is missing or all zero, explicitly returns None.
    """
    if not candles:
        return None

    cumulative_tp_vol = 0.0
    cumulative_vol = 0.0
    has_valid_volume = False

    for c in candles:
        # Check volume or tick_volume
        vol = float(c.get("volume", c.get("tick_volume", 0)))
        if vol > 0:
            has_valid_volume = True
            typical_price = (float(c["high"]) + float(c["low"]) + float(c["close"])) / 3.0
            cumulative_tp_vol += typical_price * vol
            cumulative_vol += vol

    if not has_valid_volume or cumulative_vol == 0:
        return None

    return round(cumulative_tp_vol / cumulative_vol, 2)


# ----------------------------------------------------------------------
# 6. Market Structure Detection (Swing Highs / Lows & Trend Structure)
# ----------------------------------------------------------------------
def detect_swings(candles: List[Dict[str, Any]], lookback: int = 2) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Deterministic swing high and swing low detection.
    A swing high has higher high than `lookback` bars before and after.
    A swing low has lower low than `lookback` bars before and after.
    """
    if len(candles) < (lookback * 2 + 1):
        return [], []

    swing_highs: List[Dict[str, Any]] = []
    swing_lows: List[Dict[str, Any]] = []

    for i in range(lookback, len(candles) - lookback):
        current_h = float(candles[i]["high"])
        current_l = float(candles[i]["low"])

        # Check Swing High
        is_sh = True
        for offset in range(1, lookback + 1):
            if float(candles[i - offset]["high"]) >= current_h or float(candles[i + offset]["high"]) > current_h:
                is_sh = False
                break
        if is_sh:
            swing_highs.append({
                "index": i,
                "time": candles[i]["time"],
                "price": current_h
            })

        # Check Swing Low
        is_sl = True
        for offset in range(1, lookback + 1):
            if float(candles[i - offset]["low"]) <= current_l or float(candles[i + offset]["low"]) < current_l:
                is_sl = False
                break
        if is_sl:
            swing_lows.append({
                "index": i,
                "time": candles[i]["time"],
                "price": current_l
            })

    return swing_highs, swing_lows


def analyze_market_structure(candles: List[Dict[str, Any]], lookback: int = 2) -> MarketStructureResult:
    """
    Determine whether recent market structure is BULLISH (HH + HL), BEARISH (LH + LL), or RANGE.
    """
    if len(candles) < 15:
        return MarketStructureResult(structure="RANGE")

    # If total price range in the lookback is too small (< 0.15%), classify as RANGE
    all_highs = [float(c["high"]) for c in candles]
    all_lows = [float(c["low"]) for c in candles]
    highest = max(all_highs)
    lowest = min(all_lows)
    mid_price = (highest + lowest) / 2.0
    if mid_price > 0 and ((highest - lowest) / mid_price) < 0.0015:
        return MarketStructureResult(structure="RANGE")

    swing_highs, swing_lows = detect_swings(candles, lookback=lookback)

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        # Fallback to linear price slope
        first_half = candles[:len(candles) // 2]
        second_half = candles[len(candles) // 2:]
        avg_1 = sum(float(c["close"]) for c in first_half) / len(first_half)
        avg_2 = sum(float(c["close"]) for c in second_half) / len(second_half)
        if avg_2 > avg_1 * 1.002:
            return MarketStructureResult(structure="BULLISH")
        elif avg_2 < avg_1 * 0.998:
            return MarketStructureResult(structure="BEARISH")
        return MarketStructureResult(structure="RANGE")

    last_sh = swing_highs[-1]["price"]
    prev_sh = swing_highs[-2]["price"]
    last_sl = swing_lows[-1]["price"]
    prev_sl = swing_lows[-2]["price"]

    higher_high = last_sh > prev_sh
    higher_low = last_sl > prev_sl
    lower_high = last_sh < prev_sh
    lower_low = last_sl < prev_sl

    if higher_high and higher_low:
        structure = "BULLISH"
    elif lower_high and lower_low:
        structure = "BEARISH"
    elif higher_high and lower_low:
        structure = "RANGE"  # Expanding/Volatile
    else:
        structure = "RANGE"  # Consolidation / Contracting

    return MarketStructureResult(
        structure=structure,
        higher_high=higher_high,
        higher_low=higher_low,
        lower_high=lower_high,
        lower_low=lower_low,
        last_swing_high=last_sh,
        last_swing_low=last_sl
    )


# ----------------------------------------------------------------------
# 7. Support & Resistance Detection
# ----------------------------------------------------------------------
def detect_support_resistance(
    candles: List[Dict[str, Any]],
    current_price: float,
    atr: Optional[float] = None,
    max_levels: int = 4
) -> Tuple[List[PriceLevel], List[PriceLevel]]:
    """
    Detect support and resistance levels from swing highs/lows with clustering and strength scoring.
    """
    if len(candles) < 10:
        return [], []

    swing_highs, swing_lows = detect_swings(candles, lookback=2)
    tolerance = (atr * 0.4) if (atr and atr > 0) else (current_price * 0.0008)

    # Collect raw levels
    all_points: List[Tuple[float, str]] = []
    for sh in swing_highs[-15:]:
        all_points.append((sh["price"], "resistance" if sh["price"] >= current_price else "support"))
    for sl in swing_lows[-15:]:
        all_points.append((sl["price"], "support" if sl["price"] <= current_price else "resistance"))

    # Cluster nearby levels to determine strength
    clusters: List[Dict[str, Any]] = []
    for price, ltype in all_points:
        matched = False
        for c in clusters:
            if abs(c["price"] - price) <= tolerance:
                # Update cluster average price and increment touch count
                c["touches"] += 1
                c["price"] = round((c["price"] * (c["touches"] - 1) + price) / c["touches"], 2)
                matched = True
                break
        if not matched:
            clusters.append({
                "price": round(price, 2),
                "type": ltype,
                "touches": 1
            })

    support_levels: List[PriceLevel] = []
    resistance_levels: List[PriceLevel] = []

    for c in clusters:
        strength = min(5, c["touches"])
        p = c["price"]
        if p < current_price:
            support_levels.append(PriceLevel(price=p, type="support", strength=strength))
        elif p > current_price:
            resistance_levels.append(PriceLevel(price=p, type="resistance", strength=strength))

    # Sort supports descending (closest to current price first)
    support_levels.sort(key=lambda x: x.price, reverse=True)
    # Sort resistances ascending (closest to current price first)
    resistance_levels.sort(key=lambda x: x.price)

    return support_levels[:max_levels], resistance_levels[:max_levels]
