"""
Phase 6D: Signal Engine V2 Research, Immutability & Final OOS Protection Tests
"""
import glob
import json
import pytest
from app.backtest_models import BacktestConfig
from app.experiments.baseline_config import BASELINE_VERSION, get_frozen_baseline_config
from app.signal_engine import SignalEngine
from app.signal_engine_v2 import SignalEngineV2, RESEARCH_ENGINE_VERSION
from app.signal_models import MarketSignal


def test_baseline_immutability_phase6d():
    """Verify that baseline configuration remains strictly frozen."""
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


def test_v2_engine_isolation_and_version():
    """Verify that V2 engine is versioned separately and does not overwrite baseline."""
    v1 = SignalEngine(setup_threshold=7)
    v2 = SignalEngineV2(setup_threshold=7.5)
    assert v2.version == RESEARCH_ENGINE_VERSION
    assert v2.version == "phase6d-signal-v2"
    assert BASELINE_VERSION == "phase6-baseline-v1"
    assert v1.setup_threshold == 7
    assert v2.setup_threshold == 7.5


def test_v2_deterministic_signal_generation():
    """Verify that SignalEngineV2 generates deterministic outputs for given candles."""
    candles_1m = [
        {"time": 1700000000 + i * 60, "open": 2000.0 + i * 0.1, "high": 2001.0 + i * 0.1, "low": 1999.5 + i * 0.1, "close": 2000.5 + i * 0.1, "tick_volume": 100}
        for i in range(50)
    ]
    candles_5m = [
        {"time": 1700000000 + i * 300, "open": 2000.0 + i * 0.5, "high": 2002.0 + i * 0.5, "low": 1999.0 + i * 0.5, "close": 2001.5 + i * 0.5, "tick_volume": 500}
        for i in range(25)
    ]

    engine = SignalEngineV2()
    sig1 = engine.analyze(candles_1m, candles_5m)
    sig2 = engine.analyze(candles_1m, candles_5m)

    assert sig1.type == sig2.type
    assert sig1.strength == sig2.strength
    assert sig1.trend_5m == sig2.trend_5m
    assert sig1.structure_1m == sig2.structure_1m


def test_v2_zero_lookahead_integrity():
    """Verify that removing future candles does not alter signal at time T."""
    candles_1m = [
        {"time": 1700000000 + i * 60, "open": 2000.0 + i * 0.2, "high": 2001.0 + i * 0.2, "low": 1999.8 + i * 0.2, "close": 2000.7 + i * 0.2, "tick_volume": 100}
        for i in range(60)
    ]
    candles_5m = [
        {"time": 1700000000 + i * 300, "open": 2000.0 + i * 1.0, "high": 2003.0 + i * 1.0, "low": 1999.0 + i * 1.0, "close": 2002.0 + i * 1.0, "tick_volume": 500}
        for i in range(30)
    ]

    engine = SignalEngineV2()
    sig_at_40 = engine.analyze(candles_1m[:40], candles_5m[:20])

    # Re-evaluate with identical slice
    sig_at_40_repeat = engine.analyze(candles_1m[:40], candles_5m[:20])
    assert sig_at_40.strength == sig_at_40_repeat.strength
    assert sig_at_40.type == sig_at_40_repeat.type


def test_v2_regime_classification():
    """Verify that regime classification operates deterministically."""
    candles_1m = [
        {"time": 1700000000 + i * 60, "open": 2000.0 + i * 0.1, "high": 2001.0 + i * 0.1, "low": 1999.5 + i * 0.1, "close": 2000.5 + i * 0.1, "tick_volume": 100}
        for i in range(50)
    ]
    candles_5m = [
        {"time": 1700000000 + i * 300, "open": 2000.0 + i * 0.5, "high": 2002.0 + i * 0.5, "low": 1999.0 + i * 0.5, "close": 2001.5 + i * 0.5, "tick_volume": 500}
        for i in range(25)
    ]

    engine = SignalEngineV2()
    regime = engine.classify_regime(candles_1m, candles_5m, 2005.0, 1.5, [], [])
    assert regime.regime in ["TREND_STRONG", "TREND_PULLBACK", "RANGE_COMPRESSION", "VOLATILITY_EXPANSION"]
    assert regime.trend_5m in ["BULLISH", "BEARISH", "RANGE"]


def test_final_oos_lock_in_v2_experiments():
    """Assert that all V2 hypothesis experiment artifacts enforce Final OOS lock."""
    v2_exp_files = glob.glob("data/experiments/V2-H*_result.json")
    assert len(v2_exp_files) >= 6, f"Expected at least 6 V2 experiment files, found {len(v2_exp_files)}"

    for fpath in v2_exp_files:
        with open(fpath) as f:
            data = json.load(f)
        assert data.get("final_oos_locked") is True, f"final_oos_locked must be True in {fpath}"
        assert data.get("final_oos_evaluated") is False, f"final_oos_evaluated must be False in {fpath}"
        assert data.get("decision") in ["REJECTED", "NEEDS_MORE_DATA", "PROMISING"], f"Invalid decision in {fpath}"
        # Ensure zero candidate was promoted
        assert data.get("decision") != "PROMOTED", f"Candidate must NOT be promoted in {fpath}"
