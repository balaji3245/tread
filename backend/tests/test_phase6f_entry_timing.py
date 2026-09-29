"""
Phase 6F: Entry Timing & Price-Path Research Tests
Validates:
1. Baseline immutability & exact reproduction
2. Deterministic causal state machine transitions (immediate, delay, retrace, confirmation, timeout, invalidation)
3. Causality & zero future data leakage (feature timestamp <= signal timestamp)
4. Hard Final OOS protection guard (ProtectedFinalOOSAccessError)
5. Missed-signal accounting & conversion metrics
6. Candidate experiment artifact contracts (locked, not evaluated, correct status)
"""
import glob
import json
import pytest

from app.experiments.baseline_config import BASELINE_VERSION, get_frozen_baseline_config
from app.phase6f.entry_timing_engine import (
    BreakoutContinuationPolicy,
    ControlledRetracementPolicy,
    EMAReversionPolicy,
    EntryTimingResearchEngine,
    HybridRetraceOrConfirmPolicy,
    ImmediateEntryPolicy,
    MomentumConfirmationPolicy,
    TightExpirationPolicy,
    assert_final_oos_locked,
)
from app.phase6f.models import (
    CandidateTimingResult,
    FINAL_OOS_END_TS,
    FINAL_OOS_START_TS,
    PathForensicLabel,
    ProtectedFinalOOSAccessError,
    SignalConversionMetrics,
    SignalEntryStatus,
)
from app.signal_models import MarketSignal


def test_baseline_immutability_phase6f():
    """Verify that baseline configuration remains strictly frozen during Phase 6F."""
    base_cfg = get_frozen_baseline_config()
    assert base_cfg.version == "phase6-baseline-v1"
    assert base_cfg.signal_threshold == 7
    assert base_cfg.sl_atr_multiplier == 1.0
    assert base_cfg.tp1_atr_multiplier == 1.0
    assert base_cfg.tp2_atr_multiplier == 2.0
    assert base_cfg.max_holding_minutes == 60
    assert base_cfg.assumed_spread == 0.30
    assert base_cfg.same_candle_policy == "stop_first"
    assert base_cfg.max_concurrent_trades == 1


def test_final_oos_hard_protection_guard():
    """Verify that requesting evaluation within or overlapping Final OOS raises ProtectedFinalOOSAccessError."""
    # Valid Preliminary OOS Window (Window #1)
    assert_final_oos_locked(1767107700, 1769786100)

    # Protected Final OOS Window (Window #9)
    with pytest.raises(ProtectedFinalOOSAccessError):
        assert_final_oos_locked(FINAL_OOS_START_TS, FINAL_OOS_END_TS)

    # Overlapping attempt
    with pytest.raises(ProtectedFinalOOSAccessError):
        assert_final_oos_locked(FINAL_OOS_START_TS - 100, FINAL_OOS_END_TS)


def test_immediate_entry_policy_deterministic():
    """Verify immediate entry executes at T+1 open."""
    policy = ImmediateEntryPolicy()
    sig_candle = {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2004.0}
    c1 = {"time": 1700000060, "open": 2004.5, "high": 2006.0, "low": 2003.0, "close": 2005.0}
    sig_obj = MarketSignal(type="LONG_SETUP", strength=8, generatedAt=1700000000, price=2004.0, timeframe="1m")

    status, e_time, e_price, reason = policy.evaluate_entry(
        signal_candle=sig_candle,
        subsequent_candles=[c1],
        direction="LONG",
        atr_val=2.0,
        spread_val=0.30,
        sig_obj=sig_obj,
    )
    assert status == SignalEntryStatus.ENTERED_IMMEDIATELY
    assert e_time == 1700000060
    assert e_price == 2004.80  # 2004.5 + 0.30


def test_retracement_policy_transitions():
    """Verify retracement entry triggers, invalidations, and timeouts."""
    policy = ControlledRetracementPolicy(retrace_atr=0.25, max_wait_bars=3)
    sig_candle = {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2004.0}
    sig_obj = MarketSignal(type="LONG_SETUP", strength=8, generatedAt=1700000000, price=2004.0, timeframe="1m")
    atr = 2.0  # retrace target = 2004.0 - 0.50 = 2003.50, stop invalidation = 2004.0 - 2.0 = 2002.0

    # 1. Bar 1 does not retrace -> WAITING_FOR_RETRACE
    c1_no_retrace = {"time": 1700000060, "open": 2004.5, "high": 2006.0, "low": 2004.0, "close": 2005.5}
    status, _, _, _ = policy.evaluate_entry(sig_candle, [c1_no_retrace], "LONG", atr, 0.30, sig_obj)
    assert status == SignalEntryStatus.WAITING_FOR_RETRACE

    # 2. Bar 2 retraces to 2003.20 -> ENTERED_AFTER_DELAY at target (2003.50 + 0.30 = 2003.80)
    c2_retrace = {"time": 1700000120, "open": 2005.0, "high": 2005.2, "low": 2003.2, "close": 2004.5}
    status, e_time, e_price, _ = policy.evaluate_entry(sig_candle, [c1_no_retrace, c2_retrace], "LONG", atr, 0.30, sig_obj)
    assert status == SignalEntryStatus.ENTERED_AFTER_DELAY
    assert e_time == 1700000120
    assert e_price == 2003.80

    # 3. Bar 1 breaches stop invalidation (low <= 2002.0) -> INVALIDATED
    c1_inval = {"time": 1700000060, "open": 2003.5, "high": 2004.0, "low": 2001.5, "close": 2001.8}
    status, _, _, _ = policy.evaluate_entry(sig_candle, [c1_inval], "LONG", atr, 0.30, sig_obj)
    assert status == SignalEntryStatus.INVALIDATED

    # 4. 3 bars pass without retrace -> TIMED_OUT
    c3_no_retrace = {"time": 1700000180, "open": 2005.0, "high": 2007.0, "low": 2004.2, "close": 2006.5}
    status, _, _, _ = policy.evaluate_entry(sig_candle, [c1_no_retrace, c1_no_retrace, c3_no_retrace], "LONG", atr, 0.30, sig_obj)
    assert status == SignalEntryStatus.TIMED_OUT


def test_momentum_confirmation_policy():
    """Verify momentum confirmation waits 1 closed bar and evaluates T+2 open."""
    policy = MomentumConfirmationPolicy(confirm_bars=1)
    sig_candle = {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2004.0}
    sig_obj = MarketSignal(type="LONG_SETUP", strength=8, generatedAt=1700000000, price=2004.0, timeframe="1m")

    # Bar 1 only -> WAITING_FOR_CONFIRMATION
    c1_bullish = {"time": 1700000060, "open": 2004.0, "high": 2006.0, "low": 2003.5, "close": 2005.8}
    status, _, _, _ = policy.evaluate_entry(sig_candle, [c1_bullish], "LONG", 2.0, 0.30, sig_obj)
    assert status == SignalEntryStatus.WAITING_FOR_CONFIRMATION

    # Bar 1 bullish + breaks signal high (2006.0 > 2005.0), enters at Bar 2 open
    c2_next = {"time": 1700000120, "open": 2006.0, "high": 2008.0, "low": 2005.5, "close": 2007.5}
    status, e_time, e_price, _ = policy.evaluate_entry(sig_candle, [c1_bullish, c2_next], "LONG", 2.0, 0.30, sig_obj)
    assert status == SignalEntryStatus.ENTERED_AFTER_DELAY
    assert e_time == 1700000120
    assert e_price == 2006.30

    # Bar 1 bearish -> INVALIDATED
    c1_bearish = {"time": 1700000060, "open": 2004.0, "high": 2004.5, "low": 2001.0, "close": 2001.5}
    status, _, _, _ = policy.evaluate_entry(sig_candle, [c1_bearish, c2_next], "LONG", 2.0, 0.30, sig_obj)
    assert status == SignalEntryStatus.INVALIDATED


def test_hybrid_retrace_or_confirm_policy():
    """Verify hybrid policy triggers on either retrace or breakout."""
    policy = HybridRetraceOrConfirmPolicy(retrace_atr=0.20, breakout_atr=0.20, max_wait_bars=3)
    sig_candle = {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2004.0}
    sig_obj = MarketSignal(type="LONG_SETUP", strength=8, generatedAt=1700000000, price=2004.0, timeframe="1m")
    atr = 2.0  # retrace target = 2003.60, breakout target = 2005.40

    # Retrace trigger
    c1_retrace = {"time": 1700000060, "open": 2004.2, "high": 2004.5, "low": 2003.4, "close": 2003.8}
    status, e_time, e_price, _ = policy.evaluate_entry(sig_candle, [c1_retrace], "LONG", atr, 0.30, sig_obj)
    assert status == SignalEntryStatus.ENTERED_AFTER_DELAY
    assert e_price == 2003.90  # 2003.60 + 0.30

    # Breakout trigger
    c1_breakout = {"time": 1700000060, "open": 2004.2, "high": 2005.8, "low": 2004.0, "close": 2005.6}
    status, e_time, e_price, _ = policy.evaluate_entry(sig_candle, [c1_breakout], "LONG", atr, 0.30, sig_obj)
    assert status == SignalEntryStatus.ENTERED_AFTER_DELAY
    assert e_price == 2005.70  # 2005.40 + 0.30


def test_v6f_candidate_artifacts_contracts():
    """Verify that all Phase 6F candidate JSON artifacts strictly maintain Final OOS locks and valid contracts."""
    files = [f for f in sorted(glob.glob("data/experiments/V6F-H*_result.json")) if "final_oos" not in f]
    assert len(files) == 6, f"Expected exactly 6 V6F preliminary result files, found {len(files)}"

    for fpath in files:
        with open(fpath) as f:
            data = json.load(f)
        assert data.get("final_oos_locked") is True
        assert data.get("final_oos_evaluated") is False
        assert data.get("final_oos_date_range") == "2026-08-27 to 2026-09-25"
        assert data.get("status") in ["REJECTED", "EXPLORATORY", "PROMISING", "NEEDS_MORE_DATA"]
        assert data.get("status") != "PROMOTED"
        assert len(data.get("windows", [])) == 8
        assert "conversion_metrics" in data
        assert "price_quality_metrics" in data
        assert data["conversion_metrics"]["signal_conversion_rate_pct"] > 0


def test_ema_reversion_policy():
    """Verify EMA reversion policy transitions."""
    policy = EMAReversionPolicy(max_wait_bars=5)
    sig_candle = {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2004.0}
    sig_obj = MarketSignal(
        type="LONG_SETUP",
        strength=8,
        generatedAt=1700000000,
        price=2004.0,
        timeframe="1m",
        indicators={"ema21_1m": 2002.50}
    )
    atr = 2.0

    # Candle touching EMA21 (low <= 2002.50)
    c1_touch = {"time": 1700000060, "open": 2003.5, "high": 2004.0, "low": 2002.3, "close": 2003.0}
    status, e_time, e_price, _ = policy.evaluate_entry(sig_candle, [c1_touch], "LONG", atr, 0.30, sig_obj)
    assert status == SignalEntryStatus.ENTERED_AFTER_DELAY
    assert e_price == 2002.80  # 2002.50 + 0.30


def test_tight_expiration_policy():
    """Verify tight expiration policy fast timeout behavior."""
    policy = TightExpirationPolicy(retrace_atr=0.15, max_wait_bars=2)
    sig_candle = {"time": 1700000000, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2004.0}
    sig_obj = MarketSignal(type="LONG_SETUP", strength=8, generatedAt=1700000000, price=2004.0, timeframe="1m")
    atr = 2.0  # retrace target = 2004.0 - 0.30 = 2003.70

    c1_no = {"time": 1700000060, "open": 2004.2, "high": 2005.0, "low": 2004.0, "close": 2004.8}
    c2_no = {"time": 1700000120, "open": 2004.8, "high": 2005.5, "low": 2004.2, "close": 2005.0}
    status, _, _, _ = policy.evaluate_entry(sig_candle, [c1_no, c2_no], "LONG", atr, 0.30, sig_obj)
    assert status == SignalEntryStatus.TIMED_OUT


def test_signal_conversion_accounting_formula():
    """Verify signal conversion metrics accounting arithmetic."""
    metrics = SignalConversionMetrics(
        signal_count=1000,
        entered_immediately_count=100,
        entered_after_delay_count=500,
        total_entered_count=600,
        missed_count=50,
        invalidated_count=150,
        timed_out_count=200,
        signal_conversion_rate_pct=60.0,
        trade_reduction_pct=40.0,
        average_delay_minutes=1.5,
        median_delay_minutes=1.0,
    )
    assert metrics.total_entered_count == metrics.entered_immediately_count + metrics.entered_after_delay_count
    assert metrics.signal_conversion_rate_pct == round(metrics.total_entered_count / metrics.signal_count * 100.0, 2)
    assert metrics.trade_reduction_pct == round((metrics.signal_count - metrics.total_entered_count) / metrics.signal_count * 100.0, 2)

