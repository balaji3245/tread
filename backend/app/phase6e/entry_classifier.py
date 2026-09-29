"""
Phase 6E: Deterministic Entry-State Classifier
Calculates strictly causal entry features at decision timestamp T (signal candle close).
Zero look-ahead guaranteed.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.phase6e.models import (
    FeatureProvenance,
    ImpulseState,
    SessionBlock,
    TrendRangeRegime,
    VolatilityQuantile,
)


def classify_session_utc(timestamp_seconds: int) -> Tuple[SessionBlock, str, str, str]:
    """
    Classify UTC session block, 2-hour bucket, hour bucket, and day of week.
    """
    dt = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
    hour = dt.hour
    dow = dt.strftime("%A")  # Monday, Tuesday, ...

    # Major Session Block
    if 0 <= hour < 7:
        session_block = SessionBlock.ASIAN
    elif 7 <= hour < 13:
        session_block = SessionBlock.LONDON
    elif 13 <= hour < 17:
        session_block = SessionBlock.NY_OVERLAP
    elif 17 <= hour < 21:
        session_block = SessionBlock.NY_AFTERNOON
    else:
        session_block = SessionBlock.LATE_NIGHT

    hour_str = f"{hour:02d}:00-{hour+1:02d}:00 UTC"
    block_2h = f"{(hour//2)*2:02d}:00-{((hour//2)*2)+2:02d}:00 UTC"

    return session_block, block_2h, hour_str, dow


def classify_volatility_quantile(
    current_atr: float,
    rolling_atrs: List[float]
) -> VolatilityQuantile:
    """
    Classify current ATR into 5 quantile buckets relative to rolling historical ATRs.
    """
    if not rolling_atrs or len(rolling_atrs) < 5:
        if current_atr < 1.00:
            return VolatilityQuantile.Q1_LOW
        elif current_atr < 1.50:
            return VolatilityQuantile.Q2_MID_LOW
        elif current_atr < 2.00:
            return VolatilityQuantile.Q3_MEDIAN
        elif current_atr < 2.80:
            return VolatilityQuantile.Q4_MID_HIGH
        else:
            return VolatilityQuantile.Q5_HIGH

    # Percentile rank
    pct = sum(1 for a in rolling_atrs if a <= current_atr) / len(rolling_atrs)
    if pct <= 0.20:
        return VolatilityQuantile.Q1_LOW
    elif pct <= 0.40:
        return VolatilityQuantile.Q2_MID_LOW
    elif pct <= 0.60:
        return VolatilityQuantile.Q3_MEDIAN
    elif pct <= 0.80:
        return VolatilityQuantile.Q4_MID_HIGH
    else:
        return VolatilityQuantile.Q5_HIGH


def classify_impulse_pullback_state(
    candles_1m: List[Dict[str, Any]],
    sig_index: int,
    direction: str,
    atr_val: float,
    ema21_1m: float,
    ema50_1m: float,
) -> ImpulseState:
    """
    Deterministic classification of entry timing state at signal candle close (sig_index):
    - EARLY_IMPULSE: 1-2 bars into move, displacement from EMA21 is 0.2-0.6 ATR, 2-bar move < 0.8 ATR.
    - CONTROLLED_PULLBACK: displacement from EMA21 <= 0.35 ATR, price held above/below EMA50, recent 3-bar retraced.
    - LATE_IMPULSE: displacement from EMA21 > 0.9 ATR or cumulative 3-bar move > 1.8 ATR or >= 3 consecutive trend bars.
    - NEUTRAL: other configurations.
    """
    if sig_index < 5:
        return ImpulseState.NEUTRAL

    sig_candle = candles_1m[sig_index]
    c_close = float(sig_candle["close"])
    c_open = float(sig_candle["open"])

    # Displacement from EMA21 in ATR units
    disp_ema21 = ((c_close - ema21_1m) if direction == "LONG" else (ema21_1m - c_close)) / max(0.1, atr_val)
    disp_ema50 = ((c_close - ema50_1m) if direction == "LONG" else (ema50_1m - c_close)) / max(0.1, atr_val)

    # Past 3 candles
    prev1 = candles_1m[sig_index - 1]
    prev2 = candles_1m[sig_index - 2]
    prev3 = candles_1m[sig_index - 3]

    move_2bar = abs(c_close - float(prev1["open"])) / max(0.1, atr_val)
    move_3bar = abs(c_close - float(prev2["open"])) / max(0.1, atr_val)

    # Check consecutive directional closes
    is_c0_dir = (c_close > c_open) if direction == "LONG" else (c_close < c_open)
    is_c1_dir = (float(prev1["close"]) > float(prev1["open"])) if direction == "LONG" else (float(prev1["close"]) < float(prev1["open"]))
    is_c2_dir = (float(prev2["close"]) > float(prev2["open"])) if direction == "LONG" else (float(prev2["close"]) < float(prev2["open"]))

    consec_dir_bars = (1 if is_c0_dir else 0) + (1 if is_c1_dir else 0) + (1 if is_c2_dir else 0)

    # 1. Late Impulse / Overextended
    if disp_ema21 > 0.90 or move_3bar > 1.80 or (consec_dir_bars == 3 and disp_ema21 > 0.70):
        return ImpulseState.LATE_IMPULSE

    # 2. Controlled Pullback
    if disp_ema21 <= 0.35 and disp_ema50 >= 0.0:
        return ImpulseState.CONTROLLED_PULLBACK

    # 3. Early Impulse
    if 0.20 <= disp_ema21 <= 0.70 and move_2bar <= 1.00 and consec_dir_bars <= 2:
        return ImpulseState.EARLY_IMPULSE

    return ImpulseState.NEUTRAL


def classify_trend_range_regime(
    trend_5m: str,
    structure_1m: str,
    dist_5m_ema50_atr: float,
    atr_val: float,
) -> TrendRangeRegime:
    """Classify macro & micro trend/range regime state."""
    if dist_5m_ema50_atr > 2.0:
        return TrendRangeRegime.VOLATILITY_EXPANSION
    elif trend_5m in ["BULLISH", "BEARISH"] and structure_1m == trend_5m:
        return TrendRangeRegime.STRONG_TREND
    elif trend_5m in ["BULLISH", "BEARISH"] and structure_1m != trend_5m:
        return TrendRangeRegime.TREND_PULLBACK
    else:
        return TrendRangeRegime.RANGE_COMPRESSION


def get_feature_provenance_catalog() -> List[FeatureProvenance]:
    """Return explicit provenance audit records for all Phase 6E features."""
    return [
        FeatureProvenance(
            feature_name="session_block_utc",
            source_timeframe="1m",
            calculation_timestamp=0,
            required_historical_bars=1,
            future_data_dependency=False,
            formula_description="UTC hour of signal candle timestamp partitioned into 5 standard global session windows."
        ),
        FeatureProvenance(
            feature_name="volatility_quantile_q1_q5",
            source_timeframe="1m",
            calculation_timestamp=0,
            required_historical_bars=120,
            future_data_dependency=False,
            formula_description="Percentile rank of 1m ATR(14) against rolling 120-bar historical ATR distribution."
        ),
        FeatureProvenance(
            feature_name="impulse_state_classification",
            source_timeframe="1m",
            calculation_timestamp=0,
            required_historical_bars=25,
            future_data_dependency=False,
            formula_description="Displacement from 1m EMA21, cumulative 3-bar range in ATR units, and consecutive directional closes at bar T close."
        ),
        FeatureProvenance(
            feature_name="trend_range_regime_classification",
            source_timeframe="5m+1m",
            calculation_timestamp=0,
            required_historical_bars=60,
            future_data_dependency=False,
            formula_description="5m primary trend alignment + 1m structure + 5m EMA50 distance ratio at bar T close."
        ),
        FeatureProvenance(
            feature_name="opposing_sr_clearance_atr",
            source_timeframe="1m",
            calculation_timestamp=0,
            required_historical_bars=30,
            future_data_dependency=False,
            formula_description="Distance in ATR units from bar T close to closest detected opposing support/resistance level."
        ),
    ]
