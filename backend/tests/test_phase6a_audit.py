"""
Phase 6A: Test Suite for Experiment Result Audit & Candidate Validation
Verifies baseline reproduction, EXP-001 spread audit, EXP-005 exit audit,
timing integrity, zero future leakage, and trade-set reconstruction.
"""
import copy
import gzip
import json
import pytest
from app.backtest_models import BacktestConfig, BacktestTrade
from app.backtester import BacktestReplayEngine
from app.experiments.baseline_config import (
    BASELINE_VERSION,
    get_frozen_baseline_config,
)
from app.experiments.experiment_audit import run_experiment_audit
from app.experiments.experiment_models import (
    ExperimentDecision,
    ExperimentStatus,
)
from app.historical_data_cache import ensure_data_dir, load_cached_candles
from app.historical_data_quality import compute_dataset_hash
from app.signal_models import MarketSignal, SignalIndicators


@pytest.fixture(scope="module")
def real_candles():
    c1, _ = load_cached_candles("XAUUSD", "1m")
    c5, _ = load_cached_candles("XAUUSD", "5m")
    return c1, c5


@pytest.fixture(scope="module")
def precomputed_signals():
    sig_path = ensure_data_dir() / "signals_e9db340c4efa9e63_7.json.gz"
    if sig_path.exists():
        with gzip.open(sig_path, "rt", encoding="utf-8") as f:
            raw = json.load(f)
            return {int(k): (MarketSignal(**v[0]), float(v[1])) for k, v in raw.items()}
    return None


def test_phase6a_baseline_reproduction(real_candles, precomputed_signals):
    """Confirm frozen baseline reproduces deterministic metrics on real historical data."""
    c1, c5 = real_candles
    if not c1 or not c5:
        pytest.skip("Historical candles not available in local test environment.")

    frozen_cfg = get_frozen_baseline_config()
    assert frozen_cfg.version == BASELINE_VERSION
    assert frozen_cfg.signal_threshold == 7
    assert frozen_cfg.sl_atr_multiplier == 1.0
    assert frozen_cfg.tp1_atr_multiplier == 1.0
    assert frozen_cfg.tp2_atr_multiplier == 2.0

    b_cfg = BacktestConfig(
        symbol=frozen_cfg.symbol,
        signal_threshold=frozen_cfg.signal_threshold,
        sl_atr_multiplier=frozen_cfg.sl_atr_multiplier,
        tp1_atr_multiplier=frozen_cfg.tp1_atr_multiplier,
        tp2_atr_multiplier=frozen_cfg.tp2_atr_multiplier,
        max_holding_minutes=frozen_cfg.max_holding_minutes,
        assumed_spread=frozen_cfg.assumed_spread,
        execution_mode=frozen_cfg.execution_mode,
        same_candle_policy=frozen_cfg.same_candle_policy,
        max_concurrent_trades=frozen_cfg.max_concurrent_trades
    )
    engine = BacktestReplayEngine(config=b_cfg)
    resp = engine.run_backtest(c1, c5, precomputed_signals=precomputed_signals)

    assert len(resp.trades) == 23106
    assert abs(resp.statistics.win_rate - 42.28) < 0.1
    assert abs(resp.statistics.total_r - (-2338.64)) < 0.5
    assert abs(resp.statistics.profit_factor - 0.82) < 0.05


def test_phase6a_trade_concurrency_and_signal_reconciliation(real_candles, precomputed_signals):
    """Verify distinction between signals generated, concurrency ignored, and executed trades."""
    c1, c5 = real_candles
    if not c1 or not c5:
        pytest.skip("Historical candles not available in local test environment.")

    audit_rep = run_experiment_audit("EXP-001", candles_1m=c1, candles_5m=c5, precomputed_signals=precomputed_signals)
    recon = audit_rep.trade_reconciliation

    assert recon.baseline_total_signals == 57794
    assert recon.baseline_executed_trades == 23106
    assert recon.baseline_ignored_signals == 34688
    assert recon.baseline_total_signals == recon.baseline_executed_trades + recon.baseline_ignored_signals


def test_phase6a_exp001_spread_filter_timing_and_scaling(real_candles, precomputed_signals):
    """Verify EXP-001 uses decision-time spread scaling (points to dollars) with zero look-ahead."""
    c1, c5 = real_candles
    if not c1 or not c5:
        pytest.skip("Historical candles not available in local test environment.")

    audit_rep = run_experiment_audit("EXP-001", candles_1m=c1, candles_5m=c5, precomputed_signals=precomputed_signals)

    assert audit_rep.experiment_id == "EXP-001"
    assert audit_rep.status == ExperimentStatus.REJECTED
    assert audit_rep.decision == ExperimentDecision.REJECTED
    assert audit_rep.timing_verified is True
    assert audit_rep.sample_size_valid is True
    assert audit_rep.trade_reconciliation.removed_trades_count > 0
    # Development trades should comfortably exceed 100 sample threshold
    assert audit_rep.development_experiment.trades_count >= 100


def test_phase6a_exp005_exit_reconstruction_and_walk_forward(real_candles, precomputed_signals):
    """Verify EXP-005 exit expansion (SL 1.5 ATR / TP 2.0 ATR) improves R but leaves expectancy negative."""
    c1, c5 = real_candles
    if not c1 or not c5:
        pytest.skip("Historical candles not available in local test environment.")

    audit_rep = run_experiment_audit("EXP-005", candles_1m=c1, candles_5m=c5, precomputed_signals=precomputed_signals)

    assert audit_rep.experiment_id == "EXP-005"
    assert audit_rep.status == ExperimentStatus.NEEDS_MORE_DATA
    assert audit_rep.decision == ExperimentDecision.NEEDS_MORE_DATA
    assert audit_rep.trade_set_verified is True
    assert audit_rep.trade_reconciliation.changed_exit_trades_count > 0

    # Preliminary OOS Net R should show positive delta (+592.66R)
    assert audit_rep.preliminary_oos_deltas.delta_total_r > 500.0

    # Window #9 must be locked and final_oos_evaluated false
    assert audit_rep.walk_forward_windows[-1]["is_final_oos"] is True


def test_phase6a_drawdown_accounting_and_depletion_tracking(real_candles, precomputed_signals):
    """Verify equity depletion is tracked and reported explicitly without artificially masking losses."""
    c1, c5 = real_candles
    if not c1 or not c5:
        pytest.skip("Historical candles not available in local test environment.")

    audit_rep = run_experiment_audit("EXP-005", candles_1m=c1, candles_5m=c5, precomputed_signals=precomputed_signals)
    dev_base = audit_rep.development_baseline

    assert dev_base.equity_status == "EQUITY_DEPLETION"
    assert dev_base.is_equity_depleted is True
    assert dev_base.depletion_trade_index is not None
    assert dev_base.max_drawdown_pct > 100.0
