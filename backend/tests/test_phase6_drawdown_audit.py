"""
Phase 6 Drawdown and Metrics Audit Tests
Verifies mathematical correctness of equity tracking, drawdown percentages,
depletion flagging, and baseline configuration immutability.
"""
import pytest
from app.backtest_models import BacktestTrade
from app.experiments.baseline_config import (
    BASELINE_VERSION,
    FrozenBaselineConfig,
    get_frozen_baseline_config,
)
from app.validation.validation_statistics import (
    compute_drawdown_analysis,
    summarize_trades_slice,
)


def _make_trade(r_multiple: float, pnl: float, entry_time: int = 1759331700, holding_mins: float = 10.0) -> BacktestTrade:
    """Helper to construct a mock BacktestTrade for audit testing."""
    return BacktestTrade(
        id="test-trade",
        symbol="XAUUSD",
        direction="LONG" if r_multiple > 0 else "SHORT",
        signal_time=entry_time - 60,
        signal_time_iso="2025-10-01T15:14:00+00:00",
        entry_time=entry_time,
        entry_time_iso="2025-10-01T15:15:00+00:00",
        exit_time=entry_time + int(holding_mins * 60),
        exit_time_iso="2025-10-01T15:25:00+00:00",
        signal_strength=7,
        entry_price=2650.0,
        stop_loss=2648.0,
        take_profit_1=2652.0,
        take_profit_2=2654.0,
        exit_price=2652.0 if r_multiple > 0 else 2648.0,
        result="TP1" if r_multiple > 0 else "STOP_LOSS",
        pnl=pnl,
        r_multiple=r_multiple,
        holding_minutes=holding_mins,
        exit_reason="Test exit",
        entry_reason="Test entry",
        market_regime="BULLISH",
        session="London"
    )


def test_drawdown_audit_standard_positive_equity():
    """Verify standard drawdown calculation when equity remains positive."""
    # Start: $10,000 -> +$200 ($10,200) -> -$300 ($9,900) -> +$500 ($10,400)
    trades = [
        _make_trade(2.0, 200.0, entry_time=1000),
        _make_trade(-3.0, -300.0, entry_time=2000),
        _make_trade(5.0, 500.0, entry_time=3000),
    ]
    dd = compute_drawdown_analysis(trades, initial_capital=10000.0)
    assert dd.max_drawdown_usd == 300.0
    # Peak was $10,200, low was $9,900 => 300 / 10200 = 2.94%
    assert round(dd.max_drawdown_pct, 2) == 2.94
    assert not dd.is_equity_depleted
    assert dd.equity_status == "SOLVENT"


def test_drawdown_audit_equity_depletion_exceeding_100_percent():
    """
    Audit why fixed dollar risk can produce drawdown > 100%.
    When initial capital is $10,000 and cumulative loss is $15,000 (150 losing trades of -$100),
    equity becomes -$5,000 and max drawdown is $15,000 (150% of starting capital).
    """
    # 150 consecutive losing trades of -$100
    trades = [_make_trade(-1.0, -100.0, entry_time=1000 + i * 60) for i in range(150)]
    dd = compute_drawdown_analysis(trades, initial_capital=10000.0)

    assert dd.max_drawdown_usd == 15000.0
    assert dd.max_drawdown_pct == 150.0  # 15,000 / 10,000 * 100 = 150%
    assert dd.is_equity_depleted is True
    assert dd.depletion_trade_index == 99  # Trade #100 drops balance to $0
    assert dd.equity_status == "EQUITY_DEPLETION"

    summary = summarize_trades_slice(
        trades=trades,
        signals_count=150,
        period_name="Depletion Test",
        start_ts=1000,
        end_ts=10000,
        initial_capital=10000.0,
        risk_per_trade_usd=100.0
    )
    assert summary.is_equity_depleted is True
    assert summary.depletion_trade_index == 99
    assert summary.equity_status == "EQUITY_DEPLETION"
    assert summary.max_drawdown_pct == 150.0



def test_baseline_config_immutability():
    """Verify FrozenBaselineConfig is strictly immutable and cannot be modified at runtime."""
    cfg = get_frozen_baseline_config()
    assert cfg.version == BASELINE_VERSION
    assert cfg.signal_threshold == 7
    assert cfg.sl_atr_multiplier == 1.0
    assert cfg.tp1_atr_multiplier == 1.0
    assert cfg.tp2_atr_multiplier == 2.0
    assert cfg.assumed_spread == 0.30

    # Attempting to mutate an immutable frozen config must raise a ValidationError / TypeError
    with pytest.raises(Exception):
        cfg.signal_threshold = 8

    with pytest.raises(Exception):
        cfg.sl_atr_multiplier = 1.5
