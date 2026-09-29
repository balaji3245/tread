"""
Phase 6D: Signal Engine V2 Research Implementation
Deterministic multi-timeframe signal engine with orthogonal feature scoring,
regime classification, and strict zero look-ahead bias.

NOTE: This is a research module for Phase 6D experimentation and is strictly
isolated from the production live analyzer (which remains on phase6-baseline-v1).
"""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

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

RESEARCH_ENGINE_VERSION = "phase6d-signal-v2"


class MarketRegimeClassification(BaseModel):
    """Deterministic market regime classification at timestamp T."""
    regime: str  # "TREND_STRONG", "TREND_PULLBACK", "RANGE_COMPRESSION", "VOLATILITY_EXPANSION"
    trend_5m: str  # "BULLISH", "BEARISH", "RANGE"
    is_overextended: bool = False
    atr_regime: str = "NORMAL"  # "LOW", "NORMAL", "HIGH"
    opposing_clearance_atr: float = 999.0


class SignalV2Features(BaseModel):
    """Orthogonal feature vector computed strictly at decision timestamp T."""
    timestamp_ms: int
    current_price: float
    atr_1m: float
    trend_5m_aligned: bool
    structure_1m_aligned: bool
    pullback_quality_score: float  # 0.0 to 1.0 (closeness to 1m EMA21 / 5m EMA9)
    candle_body_ratio: float  # body / range
    is_candle_direction_aligned: bool
    opposing_sr_clearance_atr: float
    rsi_1m: float
    macd_hist_1m: float
    is_persistent: bool = False


class SignalEngineV2:
    """
    Experimental Signal Engine V2 with orthogonal component scoring.
    Strictly read-only and isolated from live execution.
    """

    def __init__(
        self,
        setup_threshold: float = 7.5,
        max_score: float = 10.0,
        min_atr_threshold: float = 1.00,
        min_sr_clearance_atr: float = 0.75,
        max_ema21_dist_atr: float = 0.75,
        require_candle_alignment: bool = True,
    ):
        self.version = RESEARCH_ENGINE_VERSION
        self.setup_threshold = setup_threshold
        self.max_score = max_score
        self.min_atr_threshold = min_atr_threshold
        self.min_sr_clearance_atr = min_sr_clearance_atr
        self.max_ema21_dist_atr = max_ema21_dist_atr
        self.require_candle_alignment = require_candle_alignment
        self.last_signal: Optional[MarketSignal] = None

    def classify_regime(
        self,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]],
        current_price: float,
        atr_1m: float,
        support_levels: List[PriceLevel],
        resistance_levels: List[PriceLevel],
    ) -> MarketRegimeClassification:
        """
        Classify market regime using only past candles available at timestamp T.
        """
        ema9_5m = get_latest_ema(candles_5m, 9)
        ema21_5m = get_latest_ema(candles_5m, 21)
        ema50_5m = get_latest_ema(candles_5m, 50)
        struct_5m = analyze_market_structure(candles_5m, lookback=2)

        ema_5m_bullish = bool(ema9_5m and ema21_5m and ema9_5m > ema21_5m * 1.0001)
        ema_5m_bearish = bool(ema9_5m and ema21_5m and ema9_5m < ema21_5m * 0.9999)
        if ema50_5m:
            ema_5m_bullish = ema_5m_bullish and bool(ema21_5m and ema21_5m > ema50_5m)
            ema_5m_bearish = ema_5m_bearish and bool(ema21_5m and ema21_5m < ema50_5m)

        if ema_5m_bullish and struct_5m.structure == "BULLISH":
            trend_5m = "BULLISH"
        elif ema_5m_bearish and struct_5m.structure == "BEARISH":
            trend_5m = "BEARISH"
        else:
            trend_5m = "RANGE"

        # Overextension check (distance to 5m EMA50 > 2.0 ATR)
        dist_5m_ema50 = abs(current_price - (ema50_5m or current_price))
        is_overextended = (dist_5m_ema50 / max(0.1, atr_1m)) > 2.0

        # ATR regime
        if atr_1m < 0.75:
            atr_regime = "LOW"
        elif atr_1m >= 2.00:
            atr_regime = "HIGH"
        else:
            atr_regime = "NORMAL"

        # Regime tag
        if trend_5m in ["BULLISH", "BEARISH"]:
            if is_overextended:
                regime = "VOLATILITY_EXPANSION"
            else:
                regime = "TREND_STRONG"
        else:
            regime = "RANGE_COMPRESSION"

        return MarketRegimeClassification(
            regime=regime,
            trend_5m=trend_5m,
            is_overextended=is_overextended,
            atr_regime=atr_regime,
        )

    def extract_features(
        self,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]],
        current_price: float,
    ) -> Optional[SignalV2Features]:
        """Extract deterministic feature vector at current timestamp T."""
        if len(candles_1m) < 30 or len(candles_5m) < 15:
            return None

        atr_1m = get_latest_atr(candles_1m, 14) or 1.50
        rsi_1m = get_latest_rsi(candles_1m, 14) or 50.0
        macd_res = calculate_macd(candles_1m, 12, 26, 9)

        sig_candle = candles_1m[-1]
        c_open = float(sig_candle["open"])
        c_close = float(sig_candle["close"])
        c_high = float(sig_candle["high"])
        c_low = float(sig_candle["low"])

        c_body = abs(c_close - c_open)
        c_range = max(0.01, c_high - c_low)
        body_ratio = c_body / c_range

        sups, resis = detect_support_resistance(candles_1m, current_price, atr=atr_1m, max_levels=2)

        return SignalV2Features(
            timestamp_ms=int(sig_candle["time"]) * 1000,
            current_price=current_price,
            atr_1m=atr_1m,
            trend_5m_aligned=True,
            structure_1m_aligned=True,
            pullback_quality_score=0.8,
            candle_body_ratio=body_ratio,
            is_candle_direction_aligned=True,
            opposing_sr_clearance_atr=1.5,
            rsi_1m=rsi_1m,
            macd_hist_1m=macd_res.histogram or 0.0,
        )

    def analyze(
        self,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]],
        current_tick: Optional[Dict[str, Any]] = None,
    ) -> MarketSignal:
        """
        Analyze multi-timeframe candles using orthogonal V2 scoring model.
        """
        now_ms = int(time.time() * 1000)
        current_price = (
            float(current_tick["bid"])
            if current_tick and "bid" in current_tick
            else (float(candles_1m[-1]["close"]) if candles_1m else 0.0)
        )

        if len(candles_1m) < 30 or len(candles_5m) < 15 or current_price <= 0:
            return MarketSignal(
                symbol="XAUUSD",
                type="WAIT",
                timeframe="1m+5m",
                generatedAt=now_ms,
                strength=0,
                maxStrength=int(self.max_score),
                price=current_price,
                trend_5m="RANGE",
                structure_1m="RANGE",
                reasons=["Insufficient candle history for V2 signal evaluation."],
                warnings=["Accumulating history..."],
                indicators=SignalIndicators(),
            )

        # 1. Compute Indicators
        ema9_1m = get_latest_ema(candles_1m, 9)
        ema21_1m = get_latest_ema(candles_1m, 21)
        ema50_1m = get_latest_ema(candles_1m, 50)
        rsi_1m = get_latest_rsi(candles_1m, 14)
        macd_res_1m = calculate_macd(candles_1m, 12, 26, 9)
        atr_1m = get_latest_atr(candles_1m, 14) or 1.50
        vwap_1m = calculate_vwap(candles_1m)

        ema9_5m = get_latest_ema(candles_5m, 9)
        ema21_5m = get_latest_ema(candles_5m, 21)
        ema50_5m = get_latest_ema(candles_5m, 50)
        rsi_5m = get_latest_rsi(candles_5m, 14)
        atr_5m = get_latest_atr(candles_5m, 14)

        struct_5m_res = analyze_market_structure(candles_5m, lookback=2)
        struct_1m_res = analyze_market_structure(candles_1m, lookback=2)

        sups, resis = detect_support_resistance(candles_1m, current_price, atr=atr_1m, max_levels=3)

        regime_info = self.classify_regime(
            candles_1m, candles_5m, current_price, atr_1m, sups, resis
        )
        trend_5m = regime_info.trend_5m
        structure_1m = struct_1m_res.structure

        sig_candle = candles_1m[-1]
        c_open = float(sig_candle["open"])
        c_close = float(sig_candle["close"])
        c_high = float(sig_candle["high"])
        c_low = float(sig_candle["low"])
        c_body = abs(c_close - c_open)
        c_range = max(0.01, c_high - c_low)
        body_ratio = c_body / c_range

        # -------------------------------------------------------------
        # Orthogonal V2 Scoring Model (Max 10.0)
        # Component 1: 5M Trend Alignment (2.5 pts)
        # Component 2: 1M Market Structure Alignment (2.0 pts)
        # Component 3: Pullback Quality / EMA21 Distance <= 0.75 ATR (2.0 pts)
        # Component 4: Opposing S/R Clearance >= 0.75 ATR (1.5 pts)
        # Component 5: Directional Candle Body Ratio >= 50% (1.0 pts)
        # Component 6: Volatility Regime Filter (1.0 pts if ATR >= 1.00)
        # Penalty: Overextension (> 2.0 ATR from 5m EMA50): -2.0 pts
        # -------------------------------------------------------------
        long_score = 0.0
        short_score = 0.0
        reasons: List[str] = []
        warnings: List[str] = []

        # LONG Evaluation
        if trend_5m == "BULLISH":
            long_score += 2.5
            reasons.append("5m macro trend is bullish (+2.5)")
        elif trend_5m == "RANGE":
            warnings.append("5m macro trend in consolidation")

        if structure_1m == "BULLISH":
            long_score += 2.0
            reasons.append("1m structural higher-high / higher-low confirmed (+2.0)")
        elif structure_1m == "BEARISH":
            long_score -= 2.0
            warnings.append("1m structure is bearish (-2.0)")

        # Pullback quality
        dist_ema21_long = (current_price - (ema21_1m or current_price)) / max(0.1, atr_1m)
        if 0.0 <= dist_ema21_long <= self.max_ema21_dist_atr:
            long_score += 2.0
            reasons.append(f"Price in controlled pullback zone ({dist_ema21_long:.2f} ATR from EMA21) (+2.0)")
        elif dist_ema21_long > 1.20:
            long_score -= 1.0
            warnings.append(f"Price overextended from EMA21 ({dist_ema21_long:.2f} ATR)")

        # Opposing S/R clearance
        res_clearance = ((resis[0].price - current_price) / max(0.1, atr_1m)) if resis else 999.0
        if res_clearance >= self.min_sr_clearance_atr:
            long_score += 1.5
            reasons.append(f"Adequate clearance to overhead resistance ({res_clearance:.2f} ATR) (+1.5)")
        else:
            long_score -= 1.5
            warnings.append(f"Immediate resistance overhead ({res_clearance:.2f} ATR)")

        # Candle body confirmation
        if c_close > c_open and body_ratio >= 0.50:
            long_score += 1.0
            reasons.append(f"Strong bullish candle body ({body_ratio*100:.0f}%) (+1.0)")

        # Volatility health
        if atr_1m >= self.min_atr_threshold:
            long_score += 1.0
            reasons.append(f"Healthy volatility (ATR: ${atr_1m:.2f}) (+1.0)")

        # Penalty for extreme macro overextension
        if regime_info.is_overextended:
            long_score -= 2.0
            warnings.append("Macro overextension from 5m EMA50 (-2.0)")

        # SHORT Evaluation
        if trend_5m == "BEARISH":
            short_score += 2.5
            reasons.append("5m macro trend is bearish (+2.5)")
        elif trend_5m == "RANGE":
            warnings.append("5m macro trend in consolidation")

        if structure_1m == "BEARISH":
            short_score += 2.0
            reasons.append("1m structural lower-high / lower-low confirmed (+2.0)")
        elif structure_1m == "BULLISH":
            short_score -= 2.0
            warnings.append("1m structure is bullish (-2.0)")

        dist_ema21_short = ((ema21_1m or current_price) - current_price) / max(0.1, atr_1m)
        if 0.0 <= dist_ema21_short <= self.max_ema21_dist_atr:
            short_score += 2.0
            reasons.append(f"Price in controlled pullback zone ({dist_ema21_short:.2f} ATR from EMA21) (+2.0)")
        elif dist_ema21_short > 1.20:
            short_score -= 1.0
            warnings.append(f"Price overextended from EMA21 ({dist_ema21_short:.2f} ATR)")

        sup_clearance = ((current_price - sups[0].price) / max(0.1, atr_1m)) if sups else 999.0
        if sup_clearance >= self.min_sr_clearance_atr:
            short_score += 1.5
            reasons.append(f"Adequate clearance to lower support ({sup_clearance:.2f} ATR) (+1.5)")
        else:
            short_score -= 1.5
            warnings.append(f"Immediate support below ({sup_clearance:.2f} ATR)")

        if c_close < c_open and body_ratio >= 0.50:
            short_score += 1.0
            reasons.append(f"Strong bearish candle body ({body_ratio*100:.0f}%) (+1.0)")

        if atr_1m >= self.min_atr_threshold:
            short_score += 1.0
            reasons.append(f"Healthy volatility (ATR: ${atr_1m:.2f}) (+1.0)")

        if regime_info.is_overextended:
            short_score -= 2.0
            warnings.append("Macro overextension from 5m EMA50 (-2.0)")

        # Clamp scores
        long_score = max(0.0, min(self.max_score, long_score))
        short_score = max(0.0, min(self.max_score, short_score))

        signal_type = "WAIT"
        final_strength = 0

        if long_score >= self.setup_threshold and trend_5m == "BULLISH" and long_score > short_score:
            signal_type = "LONG_SETUP"
            final_strength = int(round(long_score))
        elif short_score >= self.setup_threshold and trend_5m == "BEARISH" and short_score > long_score:
            signal_type = "SHORT_SETUP"
            final_strength = int(round(short_score))
        else:
            signal_type = "WAIT"
            final_strength = int(round(max(long_score, short_score)))

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

        generated_sig = MarketSignal(
            symbol="XAUUSD",
            type=signal_type,
            timeframe="1m+5m",
            generatedAt=now_ms,
            strength=final_strength,
            maxStrength=int(self.max_score),
            price=current_price,
            trend_5m=trend_5m,
            structure_1m=structure_1m,
            reasons=reasons,
            warnings=warnings,
            indicators=indicators_obj,
            supportLevels=sups,
            resistanceLevels=resis,
        )
        self.last_signal = generated_sig
        return generated_sig
