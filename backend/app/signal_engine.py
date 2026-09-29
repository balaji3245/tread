import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.indicators import (
    analyze_market_structure,
    calculate_macd,
    calculate_vwap,
    detect_support_resistance,
    get_latest_atr,
    get_latest_ema,
    get_latest_rsi,
)
from app.signal_models import MarketSignal, PriceLevel, SignalIndicators

logger = logging.getLogger(__name__)


class SignalEngine:
    """
    Deterministic Multi-Timeframe (5m + 1m) Market Analysis & Signal Engine for XAUUSD.
    Strictly read-only and analytical.
    """

    def __init__(self, setup_threshold: int = 7, max_strength: int = 10):
        self.setup_threshold = setup_threshold
        self.max_strength = max_strength
        self.last_signal: Optional[MarketSignal] = None

    def analyze(
        self,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]],
        current_tick: Optional[Dict[str, Any]] = None,
    ) -> MarketSignal:
        """
        Analyze multi-timeframe candles and generate objective MarketSignal.
        """
        if current_tick and "timestamp" in current_tick:
            t_raw = current_tick["timestamp"]
            now_ms = int(t_raw) if t_raw > 10_000_000_000 else int(t_raw * 1000)
        elif candles_1m:
            now_ms = int(candles_1m[-1]["time"] * 1000)
        else:
            now_ms = int(time.time() * 1000)
        current_price = (
            float(current_tick["bid"])
            if current_tick and "bid" in current_tick
            else (float(candles_1m[-1]["close"]) if candles_1m else 0.0)
        )

        # Insufficient data check
        if len(candles_1m) < 30 or len(candles_5m) < 15 or current_price <= 0:
            return MarketSignal(
                symbol="XAUUSD",
                type="WAIT",
                timeframe="1m+5m",
                generatedAt=now_ms,
                strength=0,
                maxStrength=self.max_strength,
                price=current_price,
                trend_5m="RANGE",
                structure_1m="RANGE",
                reasons=["Insufficient historical candle data for multi-timeframe confirmation."],
                warnings=["Accumulating candle history from MT5..."],
                indicators=SignalIndicators(),
                supportLevels=[],
                resistanceLevels=[],
            )

        # --- 1. Compute Indicators ---
        # 1m Indicators
        ema9_1m = get_latest_ema(candles_1m, 9)
        ema21_1m = get_latest_ema(candles_1m, 21)
        ema50_1m = get_latest_ema(candles_1m, 50)
        rsi_1m = get_latest_rsi(candles_1m, 14)
        macd_res_1m = calculate_macd(candles_1m, 12, 26, 9)
        atr_1m = get_latest_atr(candles_1m, 14)
        vwap_1m = calculate_vwap(candles_1m)

        # 5m Indicators
        ema9_5m = get_latest_ema(candles_5m, 9)
        ema21_5m = get_latest_ema(candles_5m, 21)
        ema50_5m = get_latest_ema(candles_5m, 50)
        rsi_5m = get_latest_rsi(candles_5m, 14)
        atr_5m = get_latest_atr(candles_5m, 14)

        # --- 2. Market Structure & Levels ---
        struct_5m_res = analyze_market_structure(candles_5m, lookback=2)
        struct_1m_res = analyze_market_structure(candles_1m, lookback=2)

        support_levels, resistance_levels = detect_support_resistance(
            candles_1m, current_price, atr=atr_1m, max_levels=4
        )

        indicators_obj = SignalIndicators(
            ema9_1m=ema9_1m,
            ema21_1m=ema21_1m,
            ema50_1m=ema50_1m,
            ema9_5m=ema9_5m,
            ema21_5m=ema21_5m,
            ema50_5m=ema50_5m,
            rsi_1m=rsi_1m,
            rsi_5m=rsi_5m,
            macd_1m=macd_res_1m.macd,
            macdSignal_1m=macd_res_1m.signal,
            macdHist_1m=macd_res_1m.histogram,
            atr_1m=atr_1m,
            atr_5m=atr_5m,
            vwap_1m=vwap_1m,
        )

        # --- 3. Determine 5M Primary Trend Context ---
        trend_5m: str = "RANGE"
        ema_5m_bullish = bool(ema9_5m and ema21_5m and ema9_5m > ema21_5m * 1.0001)
        ema_5m_bearish = bool(ema9_5m and ema21_5m and ema9_5m < ema21_5m * 0.9999)
        if ema50_5m:
            ema_5m_bullish = ema_5m_bullish and bool(ema21_5m and ema21_5m > ema50_5m)
            ema_5m_bearish = ema_5m_bearish and bool(ema21_5m and ema21_5m < ema50_5m)

        if ema_5m_bullish and struct_5m_res.structure == "BULLISH":
            trend_5m = "BULLISH"
        elif ema_5m_bearish and struct_5m_res.structure == "BEARISH":
            trend_5m = "BEARISH"
        else:
            trend_5m = "RANGE"

        structure_1m = struct_1m_res.structure

        # --- 4. Evaluate Scoring Rules ---
        long_score = 0
        long_reasons: List[str] = []
        long_warnings: List[str] = []

        short_score = 0
        short_reasons: List[str] = []
        short_warnings: List[str] = []

        # Common checks
        is_atr_healthy = bool(atr_1m and atr_1m >= 0.25)
        closest_sup = support_levels[0] if support_levels else None
        closest_res = resistance_levels[0] if resistance_levels else None

        # ==========================================================
        # LONG EVALUATION
        # ==========================================================
        if trend_5m == "BULLISH":
            long_score += 2
            long_reasons.append("5m primary trend is bullish (EMA & structural support)")
        elif trend_5m == "RANGE":
            long_warnings.append("5m primary trend is in consolidation/range")

        if ema9_1m and ema21_1m and ema9_1m > ema21_1m:
            long_score += 1
            long_reasons.append("1m EMA 9 is above EMA 21 (short-term momentum)")
        else:
            long_warnings.append("1m EMA 9/21 alignment not bullish")

        if structure_1m == "BULLISH":
            long_score += 2
            long_reasons.append("1m market structure is bullish (Higher Highs / Higher Lows)")
        elif structure_1m == "BEARISH":
            long_score -= 2
            long_warnings.append("1m market structure is bearish (contradicts long)")

        if macd_res_1m.histogram is not None and macd_res_1m.histogram > 0:
            long_score += 1
            long_reasons.append("1m MACD histogram is positive")
        elif macd_res_1m.histogram is not None and macd_res_1m.histogram < 0:
            long_warnings.append("1m MACD histogram is negative")

        if rsi_1m is not None:
            if 40.0 <= rsi_1m <= 68.0:
                long_score += 1
                long_reasons.append(f"1m RSI ({rsi_1m:.1f}) in healthy bullish expansion zone")
            elif rsi_1m > 70.0:
                long_score -= 1
                long_warnings.append(f"1m RSI ({rsi_1m:.1f}) is overbought (>70)")
            elif rsi_1m < 35.0:
                long_warnings.append(f"1m RSI ({rsi_1m:.1f}) indicates weak momentum")

        if closest_sup and (current_price - closest_sup.price) <= ((atr_1m or 1.0) * 1.5):
            long_score += 1
            long_reasons.append(f"Price holding above nearby support (${closest_sup.price:.2f})")

        if is_atr_healthy:
            long_score += 1
            long_reasons.append(f"Volatility is normal (1m ATR: ${atr_1m:.2f})")
        else:
            long_warnings.append("1m ATR is unusually low (flat market)")

        if ema21_1m and current_price >= ema21_1m:
            long_score += 1
            long_reasons.append("Price is trading above 1m EMA 21")

        if closest_res and (closest_res.price - current_price) < ((atr_1m or 1.0) * 0.4):
            long_score -= 1
            long_warnings.append(f"Immediate resistance overhead at ${closest_res.price:.2f}")

        # ==========================================================
        # SHORT EVALUATION
        # ==========================================================
        if trend_5m == "BEARISH":
            short_score += 2
            short_reasons.append("5m primary trend is bearish (EMA & structural breakdown)")
        elif trend_5m == "RANGE":
            short_warnings.append("5m primary trend is in consolidation/range")

        if ema9_1m and ema21_1m and ema9_1m < ema21_1m:
            short_score += 1
            short_reasons.append("1m EMA 9 is below EMA 21 (short-term downward pressure)")
        else:
            short_warnings.append("1m EMA 9/21 alignment not bearish")

        if structure_1m == "BEARISH":
            short_score += 2
            short_reasons.append("1m market structure is bearish (Lower Highs / Lower Lows)")
        elif structure_1m == "BULLISH":
            short_score -= 2
            short_warnings.append("1m market structure is bullish (contradicts short)")

        if macd_res_1m.histogram is not None and macd_res_1m.histogram < 0:
            short_score += 1
            short_reasons.append("1m MACD histogram is negative")
        elif macd_res_1m.histogram is not None and macd_res_1m.histogram > 0:
            short_warnings.append("1m MACD histogram is positive")

        if rsi_1m is not None:
            if 32.0 <= rsi_1m <= 60.0:
                short_score += 1
                short_reasons.append(f"1m RSI ({rsi_1m:.1f}) in healthy bearish expansion zone")
            elif rsi_1m < 30.0:
                short_score -= 1
                short_warnings.append(f"1m RSI ({rsi_1m:.1f}) is oversold (<30)")
            elif rsi_1m > 65.0:
                short_warnings.append(f"1m RSI ({rsi_1m:.1f}) indicates strong buying pressure")

        if closest_res and (closest_res.price - current_price) <= ((atr_1m or 1.0) * 1.5):
            short_score += 1
            short_reasons.append(f"Price reacting near resistance (${closest_res.price:.2f})")

        if is_atr_healthy:
            short_score += 1
            short_reasons.append(f"Volatility is normal (1m ATR: ${atr_1m:.2f})")
        else:
            short_warnings.append("1m ATR is unusually low (flat market)")

        if ema21_1m and current_price <= ema21_1m:
            short_score += 1
            short_reasons.append("Price is trading below 1m EMA 21")

        if closest_sup and (current_price - closest_sup.price) < ((atr_1m or 1.0) * 0.4):
            short_score -= 1
            short_warnings.append(f"Immediate support below at ${closest_sup.price:.2f}")

        # Clamp scores
        long_score = max(0, min(self.max_strength, long_score))
        short_score = max(0, min(self.max_strength, short_score))

        # --- 5. Classify Final Setup ---
        signal_type = "WAIT"
        final_strength = 0
        final_reasons: List[str] = []
        final_warnings: List[str] = []

        if long_score >= self.setup_threshold and trend_5m == "BULLISH" and long_score > short_score:
            signal_type = "LONG_SETUP"
            final_strength = long_score
            final_reasons = long_reasons
            final_warnings = long_warnings
        elif short_score >= self.setup_threshold and trend_5m == "BEARISH" and short_score > long_score:
            signal_type = "SHORT_SETUP"
            final_strength = short_score
            final_reasons = short_reasons
            final_warnings = short_warnings
        else:
            signal_type = "WAIT"
            final_strength = max(long_score, short_score)
            if trend_5m == "RANGE":
                final_reasons.append("Market is in a range on 5m timeframe. Awaiting breakout/directional bias.")
            elif trend_5m == "BULLISH":
                final_reasons.append(
                    f"5m trend is Bullish, but 1m confirmation score ({long_score}/{self.max_strength}) is below threshold ({self.setup_threshold}/{self.max_strength})."
                )
                final_warnings.extend(long_warnings)
            elif trend_5m == "BEARISH":
                final_reasons.append(
                    f"5m trend is Bearish, but 1m confirmation score ({short_score}/{self.max_strength}) is below threshold ({self.setup_threshold}/{self.max_strength})."
                )
                final_warnings.extend(short_warnings)
            else:
                final_reasons.append("No high-probability setup currently detected. Patience required.")

        generated_signal = MarketSignal(
            symbol="XAUUSD",
            type=signal_type,
            timeframe="1m+5m",
            generatedAt=now_ms,
            strength=final_strength,
            maxStrength=self.max_strength,
            price=current_price,
            trend_5m=trend_5m,
            structure_1m=structure_1m,
            reasons=final_reasons,
            warnings=final_warnings,
            indicators=indicators_obj,
            supportLevels=support_levels,
            resistanceLevels=resistance_levels,
        )

        self.last_signal = generated_signal
        return generated_signal
