"""
Phase 6E: Conditional Entry-State & Regime Expectancy Tests
Validates deterministic classification, timestamp integrity, Final OOS guards,
and experiment artifact contracts.
"""
import glob
import json
import pytest

from app.experiments.baseline_config import BASELINE_VERSION, get_frozen_baseline_config
from app.phase6e.conditional_engine import (
    ConditionalResearchEngine,
    FINAL_OOS_END_TS,
    FINAL_OOS_START_TS,
)
from app.phase6e.entry_classifier import (
    classify_impulse_pullback_state,
    classify_session_utc,
    classify_trend_range_regime,
    classify_volatility_quantile,
    get_feature_provenance_catalog,
)
from app.phase6e.models import (
    ImpulseState,
    ProtectedFinalOOSAccessError,
    SessionBlock,
    TrendRangeRegime,
    VolatilityQuantile,
)


def test_baseline_immutability_phase6e():
    """Verify that baseline configuration remains strictly frozen during Phase 6E."""
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


def test_session_classification_deterministic():
    """Verify UTC session classification is deterministic and correct."""
    # 03:00 UTC -> Asian
    ts_asian = 1700017200  # Nov 15 2023 03:00 UTC
    sb, b2h, hstr, dow = classify_session_utc(ts_asian)
    assert sb == SessionBlock.ASIAN

    # 09:00 UTC -> London
    ts_london = 1700038800  # Nov 15 2023 09:00 UTC
    sb_lon, _, _, _ = classify_session_utc(ts_london)
    assert sb_lon == SessionBlock.LONDON

    # 14:00 UTC -> NY Overlap
    ts_ny = 1700056800  # Nov 15 2023 14:00 UTC
    sb_ny, _, _, _ = classify_session_utc(ts_ny)
    assert sb_ny == SessionBlock.NY_OVERLAP


def test_volatility_quantile_classification():
    """Verify ATR quantile classification is monotonic and bounded."""
    past_atrs = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8]
    q_low = classify_volatility_quantile(0.9, past_atrs)
    q_high = classify_volatility_quantile(3.0, past_atrs)

    assert q_low == VolatilityQuantile.Q1_LOW
    assert q_high == VolatilityQuantile.Q5_HIGH


def test_impulse_state_classification():
    """Verify impulse and pullback state classification logic."""
    candles = [
        {"time": 1700000000 + i * 60, "open": 2000.0 + i * 0.1, "high": 2001.0 + i * 0.1, "low": 1999.5 + i * 0.1, "close": 2000.5 + i * 0.1}
        for i in range(20)
    ]
    state = classify_impulse_pullback_state(
        candles_1m=candles,
        sig_index=15,
        direction="LONG",
        atr_val=1.5,
        ema21_1m=2001.0,
        ema50_1m=1999.0
    )
    assert state in [ImpulseState.EARLY_IMPULSE, ImpulseState.CONTROLLED_PULLBACK, ImpulseState.LATE_IMPULSE, ImpulseState.NEUTRAL]


def test_final_oos_hard_guard_exception():
    """Assert that requesting evaluation within Final OOS raises ProtectedFinalOOSAccessError."""
    engine = ConditionalResearchEngine([], [], {}, {})
    
    # Valid Preliminary OOS window (Window #1)
    engine.assert_final_oos_locked(1767107700, 1769786100)  # Should NOT raise

    # Attempt to access Final OOS (Window #9)
    with pytest.raises(ProtectedFinalOOSAccessError):
        engine.assert_final_oos_locked(FINAL_OOS_START_TS, FINAL_OOS_END_TS)

    # Attempt partial overlap into Final OOS
    with pytest.raises(ProtectedFinalOOSAccessError):
        engine.assert_final_oos_locked(FINAL_OOS_START_TS - 100, FINAL_OOS_END_TS)


def test_feature_provenance_catalog():
    """Verify that all features in provenance catalog declare zero future data dependency."""
    catalog = get_feature_provenance_catalog()
    assert len(catalog) >= 5
    for prov in catalog:
        assert prov.future_data_dependency is False
        assert prov.required_historical_bars >= 1


def test_v6e_experiment_artifacts_contracts():
    """Verify that all Phase 6E experiment artifacts strictly maintain Final OOS lock."""
    exp_files = glob.glob("data/experiments/V6E-H*_result.json")
    assert len(exp_files) == 6, f"Expected exactly 6 V6E experiment files, found {len(exp_files)}"

    for fpath in exp_files:
        with open(fpath) as f:
            data = json.load(f)
        assert data.get("final_oos_locked") is True
        assert data.get("final_oos_evaluated") is False
        assert data.get("final_oos_date_range") == "2026-08-27 to 2026-09-25"
        assert data.get("status") in ["REJECTED", "EXPLORATORY", "PROMISING", "NEEDS_MORE_DATA"]
        assert data.get("status") != "PROMOTED"
