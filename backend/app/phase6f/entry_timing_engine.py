"""
Phase 6F: Entry Timing & Price-Path Simulation Engine
Chronological, causal simulation of delayed entry policies, state-machine transitions,
missed-signal accounting, price improvement metrics, and Final OOS protection.
"""
import bisect
import copy
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

from app.backtest_models import BacktestConfig, BacktestResponse, BacktestTrade
from app.backtest_statistics import compute_statistics, determine_session
from app.experiments.baseline_config import BASELINE_VERSION, get_frozen_baseline_config
from app.indicators import get_latest_atr
from app.phase6e.entry_classifier import (
    classify_impulse_pullback_state,
    classify_session_utc,
    classify_trend_range_regime,
    classify_volatility_quantile,
)
from app.phase6f.models import (
    CandidateTimingResult,
    EarlyPathExcursion,
    EntryPriceQualityMetrics,
    FINAL_OOS_END_TS,
    FINAL_OOS_START_TS,
    PathForensicLabel,
    ProtectedFinalOOSAccessError,
    SignalConversionMetrics,
    SignalEntryStatus,
    SignalTimingRecord,
    TimingFeatureProvenance,
    WindowTimingMetrics,
)
from app.signal_engine import SignalEngine
from app.signal_models import MarketSignal
from app.validation.validation_statistics import summarize_trades_slice
from app.validation.walk_forward import generate_walk_forward_slices

logger = logging.getLogger(__name__)


def assert_final_oos_locked(start_ts: int, end_ts: int):
    """Hard protection mechanism ensuring candidate selection never consumes Final OOS."""
    if start_ts >= FINAL_OOS_START_TS or end_ts > FINAL_OOS_START_TS:
        raise ProtectedFinalOOSAccessError(
            f"FATAL: Attempted access to protected Final OOS window ({start_ts} >= {FINAL_OOS_START_TS} or {end_ts} > {FINAL_OOS_START_TS}). Candidate selection is strictly blocked."
        )


class BaseEntryPolicy:
    """Base class for deterministic entry policies."""
    policy_name: str = "ImmediateEntry"
    max_wait_minutes: int = 1
    same_candle_policy: str = "stop_first"

    def evaluate_entry(
        self,
        signal_candle: Dict[str, Any],
        subsequent_candles: List[Dict[str, Any]],
        direction: str,
        atr_val: float,
        spread_val: float,
        sig_obj: MarketSignal,
    ) -> Tuple[SignalEntryStatus, Optional[int], Optional[float], Optional[str]]:
        """
        Evaluate entry condition chronologically over subsequent 1m candles.
        Returns: (Status, entry_timestamp, entry_price, transition_reason)
        """
        raise NotImplementedError


class ImmediateEntryPolicy(BaseEntryPolicy):
    """Baseline: Immediate execution at next M1 bar open (T+1 Open)."""
    policy_name = "ImmediateEntry"
    max_wait_minutes = 1

    def evaluate_entry(
        self,
        signal_candle: Dict[str, Any],
        subsequent_candles: List[Dict[str, Any]],
        direction: str,
        atr_val: float,
        spread_val: float,
        sig_obj: MarketSignal,
    ) -> Tuple[SignalEntryStatus, Optional[int], Optional[float], Optional[str]]:
        if not subsequent_candles:
            return SignalEntryStatus.WAITING_FOR_SIGNAL, None, None, "Waiting for T+1"
        
        c1 = subsequent_candles[0]
        raw_open = float(c1["open"])
        entry_time = int(c1["time"])
        
        if direction == "LONG":
            entry_price = round(raw_open + spread_val, 2)
        else:
            entry_price = round(raw_open - spread_val, 2)
            
        return SignalEntryStatus.ENTERED_IMMEDIATELY, entry_time, entry_price, "Next bar open execution"


class ControlledRetracementPolicy(BaseEntryPolicy):
    """
    Hypothesis 2: Wait for price to pull back toward reference level before entering.
    """
    def __init__(self, retrace_atr: float = 0.25, max_wait_bars: int = 3):
        self.retrace_atr = retrace_atr
        self.max_wait_bars = max_wait_bars
        self.policy_name = f"Retrace_{retrace_atr}ATR_{max_wait_bars}m"
        self.max_wait_minutes = max_wait_bars

    def evaluate_entry(
        self,
        signal_candle: Dict[str, Any],
        subsequent_candles: List[Dict[str, Any]],
        direction: str,
        atr_val: float,
        spread_val: float,
        sig_obj: MarketSignal,
    ) -> Tuple[SignalEntryStatus, Optional[int], Optional[float], Optional[str]]:
        if not subsequent_candles:
            return SignalEntryStatus.WAITING_FOR_RETRACE, None, None, "Waiting for bars"

        ref_price = float(signal_candle["close"])
        retrace_dist = round(self.retrace_atr * atr_val, 2)
        max_inval_dist = round(1.0 * atr_val, 2)
        
        # Check latest candle (or iterate chronologically)
        for k, c in enumerate(subsequent_candles):
            if k >= self.max_wait_bars:
                break
            c_time = int(c["time"])
            c_open = float(c["open"])
            c_high = float(c["high"])
            c_low = float(c["low"])
            
            if direction == "LONG":
                target_p = round(ref_price - retrace_dist, 2)
                inval_p = round(ref_price - max_inval_dist, 2)
                
                # Invalidation check
                if c_low <= inval_p:
                    return SignalEntryStatus.INVALIDATED, None, None, f"Price breached invalidation level {inval_p} at bar +{k+1}m"
                
                # Retracement check
                if c_low <= target_p:
                    exec_price = min(target_p, c_open)
                    entry_price = round(exec_price + spread_val, 2)
                    status = SignalEntryStatus.ENTERED_IMMEDIATELY if k == 0 and c_open <= target_p else SignalEntryStatus.ENTERED_AFTER_DELAY
                    return status, c_time, entry_price, f"Retracement target {target_p} reached at bar +{k+1}m"
            else:  # SHORT
                target_p = round(ref_price + retrace_dist, 2)
                inval_p = round(ref_price + max_inval_dist, 2)
                
                if c_high >= inval_p:
                    return SignalEntryStatus.INVALIDATED, None, None, f"Price breached invalidation level {inval_p} at bar +{k+1}m"
                
                if c_high >= target_p:
                    exec_price = max(target_p, c_open)
                    entry_price = round(exec_price - spread_val, 2)
                    status = SignalEntryStatus.ENTERED_IMMEDIATELY if k == 0 and c_open >= target_p else SignalEntryStatus.ENTERED_AFTER_DELAY
                    return status, c_time, entry_price, f"Retracement target {target_p} reached at bar +{k+1}m"

        if len(subsequent_candles) < self.max_wait_bars:
            return SignalEntryStatus.WAITING_FOR_RETRACE, None, None, f"Waiting for retrace (bar {len(subsequent_candles)}/{self.max_wait_bars})"
        else:
            return SignalEntryStatus.TIMED_OUT, None, None, f"Retracement not reached within {self.max_wait_bars}m window"


class EMAReversionPolicy(BaseEntryPolicy):
    """
    Hypothesis 3: Wait for price to touch/approach 1M EMA21 anchor.
    """
    def __init__(self, max_wait_bars: int = 5):
        self.max_wait_bars = max_wait_bars
        self.policy_name = f"EMAReversion_EMA21_{max_wait_bars}m"
        self.max_wait_minutes = max_wait_bars

    def evaluate_entry(
        self,
        signal_candle: Dict[str, Any],
        subsequent_candles: List[Dict[str, Any]],
        direction: str,
        atr_val: float,
        spread_val: float,
        sig_obj: MarketSignal,
    ) -> Tuple[SignalEntryStatus, Optional[int], Optional[float], Optional[str]]:
        if not subsequent_candles:
            return SignalEntryStatus.WAITING_FOR_RETRACE, None, None, "Waiting for bars"

        ema21 = sig_obj.indicators.ema21_1m or float(signal_candle["close"])
        ref_price = float(signal_candle["close"])
        
        for k, c in enumerate(subsequent_candles):
            if k >= self.max_wait_bars:
                break
            c_time = int(c["time"])
            c_open = float(c["open"])
            c_high = float(c["high"])
            c_low = float(c["low"])
            
            if direction == "LONG":
                if c_low <= (ref_price - 1.2 * atr_val):
                    return SignalEntryStatus.INVALIDATED, None, None, f"Structural invalidation before EMA21 touch at bar +{k+1}m"
                
                if c_low <= ema21:
                    exec_p = min(ema21, c_open)
                    entry_price = round(exec_p + spread_val, 2)
                    status = SignalEntryStatus.ENTERED_IMMEDIATELY if k == 0 and c_open <= ema21 else SignalEntryStatus.ENTERED_AFTER_DELAY
                    return status, c_time, entry_price, f"EMA21 touch at {ema21:.2f} at bar +{k+1}m"
            else:  # SHORT
                if c_high >= (ref_price + 1.2 * atr_val):
                    return SignalEntryStatus.INVALIDATED, None, None, f"Structural invalidation before EMA21 touch at bar +{k+1}m"
                
                if c_high >= ema21:
                    exec_p = max(ema21, c_open)
                    entry_price = round(exec_p - spread_val, 2)
                    status = SignalEntryStatus.ENTERED_IMMEDIATELY if k == 0 and c_open >= ema21 else SignalEntryStatus.ENTERED_AFTER_DELAY
                    return status, c_time, entry_price, f"EMA21 touch at {ema21:.2f} at bar +{k+1}m"

        if len(subsequent_candles) < self.max_wait_bars:
            return SignalEntryStatus.WAITING_FOR_RETRACE, None, None, f"Waiting for EMA21 touch (bar {len(subsequent_candles)}/{self.max_wait_bars})"
        else:
            return SignalEntryStatus.TIMED_OUT, None, None, f"EMA21 touch not reached within {self.max_wait_bars}m window"


class MomentumConfirmationPolicy(BaseEntryPolicy):
    """
    Hypothesis 4: Wait for 1 subsequent closed M1 candle to confirm directional momentum.
    """
    def __init__(self, confirm_bars: int = 1):
        self.confirm_bars = confirm_bars
        self.policy_name = f"MomentumConfirm_{confirm_bars}Bar"
        self.max_wait_minutes = confirm_bars + 1

    def evaluate_entry(
        self,
        signal_candle: Dict[str, Any],
        subsequent_candles: List[Dict[str, Any]],
        direction: str,
        atr_val: float,
        spread_val: float,
        sig_obj: MarketSignal,
    ) -> Tuple[SignalEntryStatus, Optional[int], Optional[float], Optional[str]]:
        if len(subsequent_candles) < self.confirm_bars + 1:
            return SignalEntryStatus.WAITING_FOR_CONFIRMATION, None, None, f"Waiting for confirmation bar {len(subsequent_candles)}/{self.confirm_bars + 1}"
        
        c_confirm = subsequent_candles[self.confirm_bars - 1]
        c_next = subsequent_candles[self.confirm_bars]
        
        c_conf_open = float(c_confirm["open"])
        c_conf_close = float(c_confirm["close"])
        c_conf_high = float(c_confirm["high"])
        c_conf_low = float(c_confirm["low"])
        sig_high = float(signal_candle["high"])
        sig_low = float(signal_candle["low"])
        
        next_open = float(c_next["open"])
        entry_time = int(c_next["time"])
        
        if direction == "LONG":
            is_bullish = c_conf_close > c_conf_open
            breaks_high = c_conf_high > sig_high
            breaks_low = c_conf_low < sig_low
            
            if breaks_low and not breaks_high:
                return SignalEntryStatus.INVALIDATED, None, None, "Immediate adverse break of signal bar low"
            
            if is_bullish and breaks_high:
                entry_price = round(next_open + spread_val, 2)
                return SignalEntryStatus.ENTERED_AFTER_DELAY, entry_time, entry_price, "Confirmed bullish continuation"
            else:
                return SignalEntryStatus.INVALIDATED, None, None, "Failed directional momentum confirmation"
        else:  # SHORT
            is_bearish = c_conf_close < c_conf_open
            breaks_low = c_conf_low < sig_low
            breaks_high = c_conf_high > sig_high
            
            if breaks_high and not breaks_low:
                return SignalEntryStatus.INVALIDATED, None, None, "Immediate adverse break of signal bar high"
            
            if is_bearish and breaks_low:
                entry_price = round(next_open - spread_val, 2)
                return SignalEntryStatus.ENTERED_AFTER_DELAY, entry_time, entry_price, "Confirmed bearish continuation"
            else:
                return SignalEntryStatus.INVALIDATED, None, None, "Failed directional momentum confirmation"


class BreakoutContinuationPolicy(BaseEntryPolicy):
    """
    Hypothesis 4b: Require price to break signal bar extreme by 0.20 ATR within 2 minutes.
    """
    def __init__(self, breakout_atr: float = 0.20, max_wait_bars: int = 2):
        self.breakout_atr = breakout_atr
        self.max_wait_bars = max_wait_bars
        self.policy_name = f"Breakout_{breakout_atr}ATR_{max_wait_bars}m"
        self.max_wait_minutes = max_wait_bars

    def evaluate_entry(
        self,
        signal_candle: Dict[str, Any],
        subsequent_candles: List[Dict[str, Any]],
        direction: str,
        atr_val: float,
        spread_val: float,
        sig_obj: MarketSignal,
    ) -> Tuple[SignalEntryStatus, Optional[int], Optional[float], Optional[str]]:
        if not subsequent_candles:
            return SignalEntryStatus.WAITING_FOR_CONFIRMATION, None, None, "Waiting for bars"

        sig_high = float(signal_candle["high"])
        sig_low = float(signal_candle["low"])
        delta = round(self.breakout_atr * atr_val, 2)
        
        for k, c in enumerate(subsequent_candles):
            if k >= self.max_wait_bars:
                break
            c_time = int(c["time"])
            c_open = float(c["open"])
            c_high = float(c["high"])
            c_low = float(c["low"])
            
            if direction == "LONG":
                target_p = round(sig_high + delta, 2)
                inval_p = sig_low
                
                if c_low < inval_p:
                    return SignalEntryStatus.INVALIDATED, None, None, f"Break of signal low at bar +{k+1}m"
                
                if c_high >= target_p:
                    exec_p = max(target_p, c_open)
                    entry_price = round(exec_p + spread_val, 2)
                    return SignalEntryStatus.ENTERED_AFTER_DELAY, c_time, entry_price, f"Breakout target {target_p} reached at bar +{k+1}m"
            else:  # SHORT
                target_p = round(sig_low - delta, 2)
                inval_p = sig_high
                
                if c_high > inval_p:
                    return SignalEntryStatus.INVALIDATED, None, None, f"Break of signal high at bar +{k+1}m"
                
                if c_low <= target_p:
                    exec_p = min(target_p, c_open)
                    entry_price = round(exec_p - spread_val, 2)
                    return SignalEntryStatus.ENTERED_AFTER_DELAY, c_time, entry_price, f"Breakout target {target_p} reached at bar +{k+1}m"

        if len(subsequent_candles) < self.max_wait_bars:
            return SignalEntryStatus.WAITING_FOR_CONFIRMATION, None, None, f"Waiting for breakout (bar {len(subsequent_candles)}/{self.max_wait_bars})"
        else:
            return SignalEntryStatus.TIMED_OUT, None, None, f"Breakout not reached within {self.max_wait_bars}m"


class HybridRetraceOrConfirmPolicy(BaseEntryPolicy):
    """
    Hypothesis 5: Causal state machine permitting entry either on valid 0.20 ATR retrace recovery
    or strong 0.20 ATR momentum breakout within 3m window.
    """
    def __init__(self, retrace_atr: float = 0.20, breakout_atr: float = 0.20, max_wait_bars: int = 3):
        self.retrace_atr = retrace_atr
        self.breakout_atr = breakout_atr
        self.max_wait_bars = max_wait_bars
        self.policy_name = f"Hybrid_Retrace{retrace_atr}_Breakout{breakout_atr}_{max_wait_bars}m"
        self.max_wait_minutes = max_wait_bars

    def evaluate_entry(
        self,
        signal_candle: Dict[str, Any],
        subsequent_candles: List[Dict[str, Any]],
        direction: str,
        atr_val: float,
        spread_val: float,
        sig_obj: MarketSignal,
    ) -> Tuple[SignalEntryStatus, Optional[int], Optional[float], Optional[str]]:
        if not subsequent_candles:
            return SignalEntryStatus.WAITING_FOR_SIGNAL, None, None, "Waiting for bars"

        ref_p = float(signal_candle["close"])
        sig_high = float(signal_candle["high"])
        sig_low = float(signal_candle["low"])
        retrace_d = round(self.retrace_atr * atr_val, 2)
        breakout_d = round(self.breakout_atr * atr_val, 2)
        
        for k, c in enumerate(subsequent_candles):
            if k >= self.max_wait_bars:
                break
            c_time = int(c["time"])
            c_open = float(c["open"])
            c_high = float(c["high"])
            c_low = float(c["low"])
            
            if direction == "LONG":
                target_retrace = round(ref_p - retrace_d, 2)
                target_break = round(sig_high + breakout_d, 2)
                inval_p = round(ref_p - 0.9 * atr_val, 2)
                
                if c_low <= inval_p:
                    return SignalEntryStatus.INVALIDATED, None, None, f"Adverse invalidation at bar +{k+1}m"
                
                if c_low <= target_retrace:
                    exec_p = min(target_retrace, c_open)
                    entry_p = round(exec_p + spread_val, 2)
                    return SignalEntryStatus.ENTERED_AFTER_DELAY, c_time, entry_p, f"Hybrid retrace entry at bar +{k+1}m"
                
                if c_high >= target_break:
                    exec_p = max(target_break, c_open)
                    entry_p = round(exec_p + spread_val, 2)
                    return SignalEntryStatus.ENTERED_AFTER_DELAY, c_time, entry_p, f"Hybrid breakout entry at bar +{k+1}m"
            else:  # SHORT
                target_retrace = round(ref_p + retrace_d, 2)
                target_break = round(sig_low - breakout_d, 2)
                inval_p = round(ref_p + 0.9 * atr_val, 2)
                
                if c_high >= inval_p:
                    return SignalEntryStatus.INVALIDATED, None, None, f"Adverse invalidation at bar +{k+1}m"
                
                if c_high >= target_retrace:
                    exec_p = max(target_retrace, c_open)
                    entry_p = round(exec_p - spread_val, 2)
                    return SignalEntryStatus.ENTERED_AFTER_DELAY, c_time, entry_p, f"Hybrid retrace entry at bar +{k+1}m"
                
                if c_low <= target_break:
                    exec_p = min(target_break, c_open)
                    entry_p = round(exec_p - spread_val, 2)
                    return SignalEntryStatus.ENTERED_AFTER_DELAY, c_time, entry_p, f"Hybrid breakout entry at bar +{k+1}m"

        if len(subsequent_candles) < self.max_wait_bars:
            return SignalEntryStatus.WAITING_FOR_SIGNAL, None, None, f"Waiting for hybrid trigger (bar {len(subsequent_candles)}/{self.max_wait_bars})"
        else:
            return SignalEntryStatus.TIMED_OUT, None, None, f"Neither retrace nor breakout reached in {self.max_wait_bars}m"


class TightExpirationPolicy(BaseEntryPolicy):
    """
    Hypothesis 6: Fast 2-minute expiration with tight 0.15 ATR retrace requirement.
    """
    def __init__(self, retrace_atr: float = 0.15, max_wait_bars: int = 2):
        self.retrace_atr = retrace_atr
        self.max_wait_bars = max_wait_bars
        self.policy_name = f"TightExpiration_{retrace_atr}ATR_{max_wait_bars}m"
        self.max_wait_minutes = max_wait_bars

    def evaluate_entry(
        self,
        signal_candle: Dict[str, Any],
        subsequent_candles: List[Dict[str, Any]],
        direction: str,
        atr_val: float,
        spread_val: float,
        sig_obj: MarketSignal,
    ) -> Tuple[SignalEntryStatus, Optional[int], Optional[float], Optional[str]]:
        if not subsequent_candles:
            return SignalEntryStatus.WAITING_FOR_RETRACE, None, None, "Waiting for bars"

        ref_p = float(signal_candle["close"])
        retrace_d = round(self.retrace_atr * atr_val, 2)
        
        for k, c in enumerate(subsequent_candles):
            if k >= self.max_wait_bars:
                break
            c_time = int(c["time"])
            c_open = float(c["open"])
            c_high = float(c["high"])
            c_low = float(c["low"])
            
            if direction == "LONG":
                target_p = round(ref_p - retrace_d, 2)
                inval_p = round(ref_p - 0.75 * atr_val, 2)
                if c_low <= inval_p:
                    return SignalEntryStatus.INVALIDATED, None, None, f"Fast invalidation at bar +{k+1}m"
                if c_low <= target_p:
                    exec_p = min(target_p, c_open)
                    return SignalEntryStatus.ENTERED_AFTER_DELAY, c_time, round(exec_p + spread_val, 2), f"Tight retrace reached at bar +{k+1}m"
            else:
                target_p = round(ref_p + retrace_d, 2)
                inval_p = round(ref_p + 0.75 * atr_val, 2)
                if c_high >= inval_p:
                    return SignalEntryStatus.INVALIDATED, None, None, f"Fast invalidation at bar +{k+1}m"
                if c_high >= target_p:
                    exec_p = max(target_p, c_open)
                    return SignalEntryStatus.ENTERED_AFTER_DELAY, c_time, round(exec_p - spread_val, 2), f"Tight retrace reached at bar +{k+1}m"

        if len(subsequent_candles) < self.max_wait_bars:
            return SignalEntryStatus.WAITING_FOR_RETRACE, None, None, f"Waiting for tight retrace (bar {len(subsequent_candles)}/{self.max_wait_bars})"
        else:
            return SignalEntryStatus.TIMED_OUT, None, None, f"Expired after {self.max_wait_bars}m"


class EntryTimingResearchEngine:
    """
    Master research engine for Phase 6F entry timing and price-path analysis.
    Executes backtesting with arbitrary causal entry policies and performs exhaustive forensics.
    """
    def __init__(
        self,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]],
        precomputed_signals: Dict[int, Tuple[MarketSignal, float]],
    ):
        self.candles_1m = candles_1m
        self.candles_5m = candles_5m
        self.precomputed_signals = precomputed_signals
        self.c1_times = [int(c["time"]) for c in candles_1m]
        self.c5_times = [int(c["time"]) for c in candles_5m]
        self.baseline_config = get_frozen_baseline_config()

    def run_timing_simulation(
        self,
        entry_policy: BaseEntryPolicy,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
    ) -> Tuple[List[BacktestTrade], SignalConversionMetrics, List[Dict[str, Any]]]:
        """
        Run full deterministic simulation with the given entry policy.
        Preserves baseline SL, TP, holding time, spread, concurrency, same-candle rules.
        """
        spread_cost = self.baseline_config.assumed_spread
        trades: List[BacktestTrade] = []
        conversion_log: List[Dict[str, Any]] = []
        
        signal_count = 0
        entered_imm_count = 0
        entered_delay_count = 0
        missed_count = 0
        inval_count = 0
        timeout_count = 0
        delay_minutes_list: List[float] = []

        active_trade: Optional[Dict[str, Any]] = None
        pending_signal_state: Optional[Dict[str, Any]] = None

        start_idx = 30
        for i in range(start_idx, len(self.candles_1m)):
            current_1m = self.candles_1m[i]
            t_1m = int(current_1m["time"])

            # Filter by timestamp range if specified
            if start_ts is not None and t_1m < start_ts:
                continue
            if end_ts is not None and t_1m > end_ts:
                break

            # ------------------------------------------------------------------
            # Step A: Check Pending Signal Entry Transition (Causal chronologically)
            # ------------------------------------------------------------------
            if pending_signal_state is not None and active_trade is None:
                sig_obj = pending_signal_state["signal"]
                sig_idx = pending_signal_state["sig_idx"]
                sig_time = pending_signal_state["sig_time"]
                sig_candle = self.candles_1m[sig_idx]
                direction = "LONG" if sig_obj.type == "LONG_SETUP" else "SHORT"
                atr_val = pending_signal_state["atr"]

                # Slices available strictly from sig_idx + 1 up to current index i
                subsequent_slice = self.candles_1m[sig_idx + 1: i + 1]

                status, entry_t, entry_p, reason = entry_policy.evaluate_entry(
                    signal_candle=sig_candle,
                    subsequent_candles=subsequent_slice,
                    direction=direction,
                    atr_val=atr_val,
                    spread_val=spread_cost,
                    sig_obj=sig_obj,
                )

                if status in [SignalEntryStatus.ENTERED_IMMEDIATELY, SignalEntryStatus.ENTERED_AFTER_DELAY]:
                    delay_m = (entry_t - sig_time) / 60.0 if entry_t else 0.0
                    delay_minutes_list.append(delay_m)
                    if status == SignalEntryStatus.ENTERED_IMMEDIATELY:
                        entered_imm_count += 1
                    else:
                        entered_delay_count += 1

                    # Initialize active trade with baseline model
                    sl_dist = max(0.50, round(atr_val * self.baseline_config.sl_atr_multiplier, 2))
                    tp1_dist = round(atr_val * self.baseline_config.tp1_atr_multiplier, 2)
                    tp2_dist = round(atr_val * self.baseline_config.tp2_atr_multiplier, 2)

                    if direction == "LONG":
                        sl = round(entry_p - sl_dist, 2)
                        tp1 = round(entry_p + tp1_dist, 2)
                        tp2 = round(entry_p + tp2_dist, 2)
                    else:
                        sl = round(entry_p + sl_dist, 2)
                        tp1 = round(entry_p - tp1_dist, 2)
                        tp2 = round(entry_p - tp2_dist, 2)

                    active_trade = {
                        "id": str(uuid.uuid4())[:8],
                        "direction": direction,
                        "signal_time": sig_time,
                        "entry_time": entry_t,
                        "signal_strength": sig_obj.strength,
                        "entry_price": entry_p,
                        "stop_loss": sl,
                        "take_profit_1": tp1,
                        "take_profit_2": tp2,
                        "sl_dist": sl_dist,
                        "atr": atr_val,
                        "entry_reason": reason,
                        "market_regime": sig_obj.trend_5m,
                        "session": determine_session(entry_t),
                        "peak_mfe_price": 0.0,
                        "peak_mae_price": 0.0,
                        "peak_mfe_r": 0.0,
                        "peak_mae_r": 0.0,
                        "entry_bar_idx": i,
                    }
                    conversion_log.append({
                        "sig_time": sig_time,
                        "status": status.value,
                        "entry_time": entry_t,
                        "entry_price": entry_p,
                        "delay_minutes": delay_m,
                    })
                    pending_signal_state = None

                elif status == SignalEntryStatus.INVALIDATED:
                    inval_count += 1
                    conversion_log.append({"sig_time": sig_time, "status": status.value, "reason": reason})
                    pending_signal_state = None

                elif status == SignalEntryStatus.TIMED_OUT:
                    timeout_count += 1
                    conversion_log.append({"sig_time": sig_time, "status": status.value, "reason": reason})
                    pending_signal_state = None

                elif status == SignalEntryStatus.MISSED:
                    missed_count += 1
                    conversion_log.append({"sig_time": sig_time, "status": status.value, "reason": reason})
                    pending_signal_state = None

                # Otherwise status is WAITING_FOR_RETRACE / WAITING_FOR_CONFIRMATION -> stay pending for next bar

            # ------------------------------------------------------------------
            # Step B: Evaluate Active Trade Exits (Frozen Baseline Trade Model)
            # ------------------------------------------------------------------
            if active_trade is not None:
                c_high = float(current_1m["high"])
                c_low = float(current_1m["low"])
                c_close = float(current_1m["close"])
                dir_t = active_trade["direction"]
                sl = active_trade["stop_loss"]
                tp1 = active_trade["take_profit_1"]
                tp2 = active_trade["take_profit_2"]
                entry_p = active_trade["entry_price"]
                sl_dist = active_trade["sl_dist"]
                holding_mins = (t_1m - active_trade["entry_time"]) / 60.0

                if dir_t == "LONG":
                    bar_fav = max(0.0, c_high - entry_p)
                    bar_adv = max(0.0, entry_p - c_low)
                else:
                    bar_fav = max(0.0, entry_p - c_low)
                    bar_adv = max(0.0, c_high - entry_p)

                active_trade["peak_mfe_price"] = max(active_trade["peak_mfe_price"], bar_fav)
                active_trade["peak_mae_price"] = max(active_trade["peak_mae_price"], bar_adv)
                active_trade["peak_mfe_r"] = active_trade["peak_mfe_price"] / sl_dist if sl_dist > 0 else 0.0
                active_trade["peak_mae_r"] = active_trade["peak_mae_price"] / sl_dist if sl_dist > 0 else 0.0

                trade_closed = False
                exit_price = c_close
                result = "EXPIRED"
                exit_reason = "Holding time limit reached"

                if dir_t == "LONG":
                    hit_sl = c_low <= sl
                    hit_tp2 = c_high >= tp2
                    hit_tp1 = c_high >= tp1

                    if hit_sl and hit_tp1:
                        trade_closed = True
                        exit_price = sl
                        result = "STOP_LOSS"
                        exit_reason = "Stop-loss triggered (Stop-first conflict policy)"
                    elif hit_sl:
                        trade_closed = True
                        exit_price = sl
                        result = "STOP_LOSS"
                        exit_reason = "Stop-loss price reached"
                    elif hit_tp2:
                        trade_closed = True
                        exit_price = tp2
                        result = "TP2"
                        exit_reason = "Take-profit 2 reached"
                    elif hit_tp1:
                        trade_closed = True
                        exit_price = tp1
                        result = "TP1"
                        exit_reason = "Take-profit 1 reached"
                    elif holding_mins >= self.baseline_config.max_holding_minutes:
                        trade_closed = True
                        exit_price = c_close
                        result = "EXPIRED"
                        exit_reason = f"Max holding time ({self.baseline_config.max_holding_minutes}m) expired"

                else:  # SHORT
                    hit_sl = c_high >= sl
                    hit_tp2 = c_low <= tp2
                    hit_tp1 = c_low <= tp1

                    if hit_sl and hit_tp1:
                        trade_closed = True
                        exit_price = sl
                        result = "STOP_LOSS"
                        exit_reason = "Stop-loss triggered (Stop-first conflict policy)"
                    elif hit_sl:
                        trade_closed = True
                        exit_price = sl
                        result = "STOP_LOSS"
                        exit_reason = "Stop-loss price reached"
                    elif hit_tp2:
                        trade_closed = True
                        exit_price = tp2
                        result = "TP2"
                        exit_reason = "Take-profit 2 reached"
                    elif hit_tp1:
                        trade_closed = True
                        exit_price = tp1
                        result = "TP1"
                        exit_reason = "Take-profit 1 reached"
                    elif holding_mins >= self.baseline_config.max_holding_minutes:
                        trade_closed = True
                        exit_price = c_close
                        result = "EXPIRED"
                        exit_reason = f"Max holding time ({self.baseline_config.max_holding_minutes}m) expired"

                if trade_closed:
                    if dir_t == "LONG":
                        price_diff = exit_price - entry_p
                    else:
                        price_diff = entry_p - exit_price

                    r_multiple = round(price_diff / sl_dist, 2) if sl_dist > 0 else 0.0
                    pnl = round(r_multiple * self.baseline_config.risk_per_trade_usd, 2)

                    trade_obj = BacktestTrade(
                        id=active_trade["id"],
                        symbol=self.baseline_config.symbol,
                        direction=dir_t,
                        signal_time=active_trade["signal_time"],
                        signal_time_iso=datetime.fromtimestamp(active_trade["signal_time"], tz=timezone.utc).isoformat(),
                        entry_time=active_trade["entry_time"],
                        entry_time_iso=datetime.fromtimestamp(active_trade["entry_time"], tz=timezone.utc).isoformat(),
                        exit_time=t_1m,
                        exit_time_iso=datetime.fromtimestamp(t_1m, tz=timezone.utc).isoformat(),
                        signal_strength=active_trade["signal_strength"],
                        entry_price=entry_p,
                        stop_loss=sl,
                        take_profit_1=tp1,
                        take_profit_2=tp2,
                        exit_price=exit_price,
                        result=result,
                        pnl=pnl,
                        r_multiple=r_multiple,
                        holding_minutes=round(max(1.0, holding_mins), 1),
                        exit_reason=exit_reason,
                        entry_reason=active_trade["entry_reason"],
                        market_regime=active_trade["market_regime"],
                        session=active_trade["session"],
                        mae_r=round(active_trade["peak_mae_r"], 2),
                        mfe_r=round(active_trade["peak_mfe_r"], 2),
                        mae_price=round(active_trade["peak_mae_price"], 2),
                        mfe_price=round(active_trade["peak_mfe_price"], 2),
                    )
                    trades.append(trade_obj)
                    active_trade = None

            # ------------------------------------------------------------------
            # Step C: Evaluate Signal on Closed Bar i (Strict Anti-Lookahead)
            # ------------------------------------------------------------------
            if active_trade is None and pending_signal_state is None and (i < len(self.candles_1m) - 1):
                cached = self.precomputed_signals.get(i)
                if cached is not None:
                    sig_obj, atr_val = cached
                    if sig_obj.strength >= self.baseline_config.signal_threshold:
                        signal_count += 1
                        pending_signal_state = {
                            "signal": sig_obj,
                            "sig_idx": i,
                            "sig_time": t_1m,
                            "atr": atr_val,
                        }

        total_entered = entered_imm_count + entered_delay_count
        conv_rate = round((total_entered / signal_count * 100.0), 2) if signal_count > 0 else 0.0
        trade_reduc = round(((signal_count - total_entered) / signal_count * 100.0), 2) if signal_count > 0 else 0.0

        conversion_metrics = SignalConversionMetrics(
            signal_count=signal_count,
            entered_immediately_count=entered_imm_count,
            entered_after_delay_count=entered_delay_count,
            total_entered_count=total_entered,
            missed_count=missed_count,
            invalidated_count=inval_count,
            timed_out_count=timeout_count,
            signal_conversion_rate_pct=conv_rate,
            trade_reduction_pct=trade_reduc,
            average_delay_minutes=round(float(np.mean(delay_minutes_list)), 2) if delay_minutes_list else 0.0,
            median_delay_minutes=round(float(np.median(delay_minutes_list)), 2) if delay_minutes_list else 0.0,
        )

        return trades, conversion_metrics, conversion_log

    def compute_detailed_forensics(self, baseline_trades: List[BacktestTrade]) -> Dict[str, Any]:
        """
        Forensic excursion study across 1m, 2m, 3m, 5m horizons and causal signal records.
        """
        records: List[SignalTimingRecord] = []
        path_label_counts = {lbl.value: 0 for lbl in PathForensicLabel}
        early_adverse_recovery_count = 0
        instant_stop_count = 0

        rolling_atrs = []
        for i in range(len(self.candles_1m)):
            if i in self.precomputed_signals:
                rolling_atrs.append(self.precomputed_signals[i][1])
            elif rolling_atrs:
                rolling_atrs.append(rolling_atrs[-1])
            else:
                rolling_atrs.append(1.50)

        trade_by_sig_time = {t.signal_time: t for t in baseline_trades}

        for sig_idx, (sig_obj, atr_val) in self.precomputed_signals.items():
            if sig_obj.strength < self.baseline_config.signal_threshold:
                continue
            if sig_idx + 60 >= len(self.candles_1m):
                continue

            sig_candle = self.candles_1m[sig_idx]
            sig_time = int(sig_candle["time"])
            direction = "LONG" if sig_obj.type == "LONG_SETUP" else "SHORT"
            sl_dist = max(0.50, round(atr_val * 1.0, 2))

            c_open = float(sig_candle["open"])
            c_high = float(sig_candle["high"])
            c_low = float(sig_candle["low"])
            c_close = float(sig_candle["close"])
            c_body = abs(c_close - c_open)
            c_range = max(0.01, c_high - c_low)
            body_ratio = round(c_body / c_range, 3)

            ind = sig_obj.indicators
            ema21 = ind.ema21_1m or c_close
            ema50 = ind.ema50_1m or c_close
            ema50_5m = ind.ema50_5m or c_close

            dist_ema21_atr = round(abs(c_close - ema21) / atr_val, 2)
            dist_ema50_atr = round(abs(c_close - ema50) / atr_val, 2)

            sess_block, _, _, _ = classify_session_utc(sig_time)
            past_atrs = rolling_atrs[max(0, sig_idx - 120):sig_idx + 1]
            vol_quantile = classify_volatility_quantile(atr_val, past_atrs)
            impulse_state = classify_impulse_pullback_state(self.candles_1m, sig_idx, direction, atr_val, ema21, ema50)
            dist_5m_ema50_atr = abs(c_close - ema50_5m) / max(0.1, atr_val)
            trend_regime = classify_trend_range_regime(sig_obj.trend_5m, sig_obj.structure_1m, dist_5m_ema50_atr, atr_val)

            next_candles = self.candles_1m[sig_idx + 1: sig_idx + 6]
            paths = {}
            cum_mfe = 0.0
            cum_mae = 0.0

            for h_idx, fc in enumerate(next_candles, start=1):
                fh = float(fc["high"])
                fl = float(fc["low"])
                fc_close = float(fc["close"])
                if direction == "LONG":
                    adv = max(0.0, c_close - fl)
                    fav = max(0.0, fh - c_close)
                    cont = fc_close > c_close
                    p_diff = (fc_close - c_close) / atr_val
                else:
                    adv = max(0.0, fh - c_close)
                    fav = max(0.0, c_close - fl)
                    cont = fc_close < c_close
                    p_diff = (c_close - fc_close) / atr_val

                cum_mfe = max(cum_mfe, fav)
                cum_mae = max(cum_mae, adv)

                paths[h_idx] = EarlyPathExcursion(
                    horizon_minutes=h_idx,
                    mfe_r=round(cum_mfe / sl_dist, 2),
                    mae_r=round(cum_mae / sl_dist, 2),
                    directional_continuation=cont,
                    price_change_atr=round(p_diff, 2),
                )

            mae_1m = paths[1].mae_r
            mfe_5m = paths[min(5, len(paths))].mfe_r
            mae_5m = paths[min(5, len(paths))].mae_r

            if mae_1m >= 1.0:
                instant_stop_count += 1
                if mfe_5m >= 1.0:
                    lbl = PathForensicLabel.EARLY_ADVERSE_THEN_RECOVERY
                    early_adverse_recovery_count += 1
                else:
                    lbl = PathForensicLabel.PURE_ADVERSE
            elif mfe_5m >= 1.0 and mae_5m <= 0.3:
                lbl = PathForensicLabel.FAST_CONTINUATION
            elif mae_5m <= 0.4 and mfe_5m >= 0.8:
                lbl = PathForensicLabel.IMMEDIATE_FAVORABLE
            elif 0.2 <= mae_5m <= 0.6 and mfe_5m >= 0.6:
                lbl = PathForensicLabel.CONTROLLED_RETRACE
            else:
                lbl = PathForensicLabel.CHOP

            path_label_counts[lbl.value] += 1

            matched_trade = trade_by_sig_time.get(sig_time)
            rec = SignalTimingRecord(
                signal_id=f"SIG_{sig_time}",
                signal_timestamp=sig_time,
                signal_timestamp_iso=datetime.fromtimestamp(sig_time, tz=timezone.utc).isoformat(),
                signal_direction=direction,
                signal_score=sig_obj.strength,
                signal_open=c_open,
                signal_high=c_high,
                signal_low=c_low,
                signal_close=c_close,
                atr_at_signal=round(atr_val, 2),
                ema21_at_signal=round(ema21, 2),
                ema50_at_signal=round(ema50, 2),
                distance_to_ema21_atr=dist_ema21_atr,
                distance_to_ema50_atr=dist_ema50_atr,
                recent_impulse_size_atr=dist_ema21_atr,
                recent_range_atr=round(c_range / atr_val, 2),
                recent_body_ratio=body_ratio,
                spread_at_signal=self.baseline_config.assumed_spread,
                session=sess_block.value,
                volatility_regime=vol_quantile.value,
                market_regime=trend_regime.value,
                entry_state=impulse_state.value,
                baseline_entry_price=round(float(next_candles[0]["open"]) + (self.baseline_config.assumed_spread if direction == "LONG" else -self.baseline_config.assumed_spread), 2),
                baseline_entry_time=int(next_candles[0]["time"]),
                baseline_realized_r=matched_trade.r_multiple if matched_trade else None,
                baseline_result=matched_trade.result if matched_trade else None,
                baseline_mae_r=matched_trade.mae_r if matched_trade else None,
                baseline_mfe_r=matched_trade.mfe_r if matched_trade else None,
                baseline_early_stop=(matched_trade.holding_minutes <= 3 and matched_trade.r_multiple < 0) if matched_trade else None,
                path_1m=paths.get(1),
                path_2m=paths.get(2),
                path_3m=paths.get(3),
                path_5m=paths.get(5),
                forensic_outcome_label=lbl,
            )
            records.append(rec)

        return {
            "total_signals": len(records),
            "records": records,
            "path_distribution": path_label_counts,
            "instant_stop_count": instant_stop_count,
            "early_adverse_recovery_count": early_adverse_recovery_count,
        }
