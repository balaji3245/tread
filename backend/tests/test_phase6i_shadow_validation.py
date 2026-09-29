"""
Phase 6I: Live Shadow / Paper Validation Test Suite
Tests:
1. State machine: signal -> waiting -> fill -> exit
2. Timeouts: 120-second max wait expiration
3. Invalidations: adverse 0.75 ATR price movement
4. Concurrency: max 1 active virtual trade / pending slot
5. Deduplication: idempotent signal processing
6. Persistence: state file recovery and append-only journal
7. Failure isolation: engine exceptions do not disrupt caller
8. Execution safety: strictly virtual paper mode (zero live order calls)
9. Causality: strict temporal monotonicity (signal <= entry <= exit)
"""
import json
import shutil
import tempfile
import time
from pathlib import Path
import pytest

from app.phase6i.models import (
    ActiveVirtualTrade,
    PendingShadowSignal,
    ShadowHealthStatus,
    ShadowJournalEntry,
    ShadowSignalClassification,
    ShadowState,
)
from app.phase6i.shadow_engine import LiveShadowEngine
from app.signal_models import MarketSignal, SignalIndicators


@pytest.fixture
def temp_shadow_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def make_dummy_signal(direction="LONG", price=2500.0, atr=2.0, timestamp=1780000000) -> MarketSignal:
    return MarketSignal(
        type="LONG_SETUP" if direction == "LONG" else "SHORT_SETUP",
        strength=8,
        price=price,
        trend_5m="BULLISH" if direction == "LONG" else "BEARISH",
        structure_1m="BULLISH" if direction == "LONG" else "BEARISH",
        indicators=SignalIndicators(
            ema21_1m=price - 0.5,
            ema50_1m=price - 1.0,
            ema21_5m=price - 1.5,
            ema50_5m=price - 2.0,
            rsi_1m=55.0,
            atr_1m=atr,
        ),
        generatedAt=timestamp * 1000,
        reasons=["Test Setup"],
    )


def test_shadow_frozen_parameters(temp_shadow_dir):
    """Verify H006 parameters are strictly frozen according to Phase 6H specs."""
    engine = LiveShadowEngine(data_dir=temp_shadow_dir)
    assert engine.retrace_atr == 0.15
    assert engine.max_wait_seconds == 120
    assert engine.invalidation_atr == 0.75
    assert engine.sl_atr_multiplier == 1.0
    assert engine.tp1_atr_multiplier == 1.0
    assert engine.tp2_atr_multiplier == 2.0
    assert engine.assumed_spread == 0.30
    assert engine.max_holding_seconds == 3600


def test_state_machine_long_fill_and_tp1_exit(temp_shadow_dir):
    """Verify full state machine lifecycle for LONG setup with 0.15 ATR retracement and TP1 exit."""
    engine = LiveShadowEngine(data_dir=temp_shadow_dir)
    sig_ts = 1780000000
    signal = make_dummy_signal(direction="LONG", price=2500.00, atr=2.0, timestamp=sig_ts)

    # 1. New Signal Registration
    engine.process_new_signal(signal, [], {"bid": 2500.00, "ask": 2500.30, "spread": 30})
    assert engine.pending_signal is not None
    assert engine.pending_signal.direction == "LONG"
    # Target = 2500.00 - 0.15*2.0 = 2500.00 - 0.30 = 2499.70
    assert engine.pending_signal.target_price == 2499.70
    assert engine.active_trade is None

    # 2. Intermediate tick (no retrace yet)
    engine.process_tick_update({"bid": 2499.90, "ask": 2500.20, "timestamp": (sig_ts + 30) * 1000})
    assert engine.pending_signal is not None
    assert engine.active_trade is None

    # 3. Retracement tick triggers limit fill (Bid <= 2499.70)
    # Long enters at min(target, bid) + spread = 2499.70 + 0.30 = 2500.00
    engine.process_tick_update({"bid": 2499.65, "ask": 2499.95, "timestamp": (sig_ts + 45) * 1000})
    assert engine.pending_signal is None
    assert engine.active_trade is not None
    at = engine.active_trade
    assert at.entry_price == 2499.95  # 2499.65 + 0.30
    assert at.stop_loss == round(2499.95 - 2.0, 2)
    assert at.take_profit_1 == round(2499.95 + 2.0, 2)

    # 4. Price moves up and hits TP1 (Bid >= 2501.95)
    exit_entry = engine.process_tick_update({"bid": 2502.00, "ask": 2502.30, "timestamp": (sig_ts + 120) * 1000})
    assert engine.active_trade is None
    assert exit_entry is not None
    assert exit_entry.entry_triggered is True
    assert exit_entry.result == "TP1"
    assert exit_entry.r_multiple == 1.0
    assert exit_entry.delay_seconds == 45.0
    assert exit_entry.delay_minutes == 0.75
    assert exit_entry.exit_price == at.take_profit_1


def test_state_machine_timeout(temp_shadow_dir):
    """Verify that signal times out after 120 seconds if retrace is not reached."""
    engine = LiveShadowEngine(data_dir=temp_shadow_dir)
    sig_ts = 1780000000
    signal = make_dummy_signal(direction="LONG", price=2500.00, atr=2.0, timestamp=sig_ts)

    engine.process_new_signal(signal, [], {"bid": 2500.00, "ask": 2500.30, "spread": 30})
    assert engine.pending_signal is not None

    # Tick at 121 seconds without retracement
    entry = engine.process_tick_update({"bid": 2501.00, "ask": 2501.30, "timestamp": (sig_ts + 121) * 1000})
    assert engine.pending_signal is None
    assert engine.active_trade is None
    assert entry is not None
    assert entry.entry_state == "TIMED_OUT"
    assert entry.timeout is True
    assert entry.entry_triggered is False


def test_state_machine_invalidation(temp_shadow_dir):
    """Verify that signal is invalidated if price drops past 0.75 ATR before retracement."""
    engine = LiveShadowEngine(data_dir=temp_shadow_dir)
    sig_ts = 1780000000
    signal = make_dummy_signal(direction="LONG", price=2500.00, atr=2.0, timestamp=sig_ts)

    engine.process_new_signal(signal, [], {"bid": 2500.00, "ask": 2500.30, "spread": 30})
    assert engine.pending_signal is not None
    # Invalidation price = 2500.00 - 0.75*2.0 = 2498.50

    # Severe adverse movement hitting invalidation
    entry = engine.process_tick_update({"bid": 2498.40, "ask": 2498.70, "timestamp": (sig_ts + 15) * 1000})
    assert engine.pending_signal is None
    assert engine.active_trade is None
    assert entry is not None
    assert entry.entry_state == "INVALIDATED"
    assert entry.invalidation is True
    assert entry.entry_triggered is False


def test_concurrency_max_one(temp_shadow_dir):
    """Verify that only 1 active pending signal or virtual trade is permitted at a time."""
    engine = LiveShadowEngine(data_dir=temp_shadow_dir)
    sig_ts = 1780000000
    signal1 = make_dummy_signal(direction="LONG", price=2500.00, atr=2.0, timestamp=sig_ts)
    signal2 = make_dummy_signal(direction="SHORT", price=2502.00, atr=2.0, timestamp=sig_ts + 30)

    # First signal becomes pending
    engine.process_new_signal(signal1, [], {"bid": 2500.00, "ask": 2500.30, "spread": 30})
    assert engine.pending_signal is not None

    # Second signal while first is pending must be blocked by concurrency
    entry2 = engine.process_new_signal(signal2, [], {"bid": 2502.00, "ask": 2502.30, "spread": 30})
    assert entry2 is not None
    assert entry2.entry_state == "CONCURRENCY_BLOCKED"
    assert "pending signal waiting" in entry2.cancellation_reason
    assert engine.pending_signal.signal_id == "XAUUSD_1m_1780000000_LONG"


def test_deduplication(temp_shadow_dir):
    """Verify identical signals are deduplicated."""
    engine = LiveShadowEngine(data_dir=temp_shadow_dir)
    sig_ts = 1780000000
    signal = make_dummy_signal(direction="LONG", price=2500.00, atr=2.0, timestamp=sig_ts)

    engine.process_new_signal(signal, [], {"bid": 2500.00, "ask": 2500.30, "spread": 30})
    assert len(engine.processed_signal_ids) == 1

    # Exact duplicate
    res = engine.process_new_signal(signal, [], {"bid": 2500.00, "ask": 2500.30, "spread": 30})
    assert res is None
    assert len(engine.processed_signal_ids) == 1


def test_persistence_and_restart_recovery(temp_shadow_dir):
    """Verify state persists to disk and recovers cleanly on new engine instance."""
    engine1 = LiveShadowEngine(data_dir=temp_shadow_dir)
    sig_ts = 1780000000
    signal = make_dummy_signal(direction="LONG", price=2500.00, atr=2.0, timestamp=sig_ts)

    engine1.process_new_signal(signal, [], {"bid": 2500.00, "ask": 2500.30, "spread": 30})
    assert engine1.pending_signal is not None

    # Fill the trade
    engine1.process_tick_update({"bid": 2499.60, "ask": 2499.90, "timestamp": (sig_ts + 20) * 1000})
    assert engine1.active_trade is not None

    # Simulate restart by instantiating new engine on same directory
    engine2 = LiveShadowEngine(data_dir=temp_shadow_dir)
    assert engine2.active_trade is not None
    assert engine2.active_trade.trade_id == engine1.active_trade.trade_id
    assert engine2.active_trade.entry_price == engine1.active_trade.entry_price
    assert "XAUUSD_1m_1780000000_LONG" in engine2.processed_signal_ids


def test_failure_isolation(temp_shadow_dir):
    """Verify engine isolates exceptions and never bubbles errors up to caller."""
    engine = LiveShadowEngine(data_dir=temp_shadow_dir)

    # Invalid / corrupt object
    res1 = engine.process_new_signal(None, None, None)
    assert res1 is None

    # Corrupt tick dict
    res2 = engine.process_tick_update({"corrupt_key": 123})
    assert res2 is None


def test_zero_real_trading_code_in_repo():
    """Verify strictly 0 live execution or order submission calls exist."""
    forbidden_terms = [
        "mt5.order_send",
        "order_send(",
        "account_info().equity",
    ]
    # Check shadow package
    shadow_files = list(Path("app/phase6i").glob("*.py")) + [Path("app/routes/shadow.py")]
    for sf in shadow_files:
        content = sf.read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert term not in content, f"Forbidden live order call '{term}' found in {sf}"


def test_causality_and_temporal_monotonicity(temp_shadow_dir):
    """Verify signal_timestamp <= entry_timestamp <= exit_timestamp in all journal entries."""
    engine = LiveShadowEngine(data_dir=temp_shadow_dir)
    sig_ts = 1780000000
    signal = make_dummy_signal(direction="SHORT", price=2500.00, atr=2.0, timestamp=sig_ts)

    engine.process_new_signal(signal, [], {"bid": 2500.00, "ask": 2500.30, "spread": 30})
    # Fill at 2500.30 (retrace up) at t+25s
    engine.process_tick_update({"bid": 2500.10, "ask": 2500.40, "timestamp": (sig_ts + 25) * 1000})
    # Exit at TP1 at t+90s
    entry = engine.process_tick_update({"bid": 2497.00, "ask": 2497.30, "timestamp": (sig_ts + 90) * 1000})

    assert entry is not None
    assert entry.signal_timestamp <= entry.entry_timestamp
    assert entry.entry_timestamp <= entry.exit_timestamp
    assert entry.delay_seconds >= 0.0
    assert entry.r_multiple > 0.0
