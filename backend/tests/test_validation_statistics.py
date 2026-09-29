import pytest
from app.backtest_models import BacktestTrade
from app.validation.validation_models import PeriodMetricSummary
from app.validation.validation_statistics import (
    aggregate_out_of_sample,
    compute_drawdown_analysis,
    compute_expectancy,
    compute_monthly_metrics,
    compute_period_concentration,
    summarize_trades_slice,
)


def _make_sample_trade(trade_id: str, entry_time: int, direction: str, r_multiple: float, pnl: float) -> BacktestTrade:
    res = "TP1" if r_multiple > 0 else "STOP_LOSS"
    return BacktestTrade(
        id=trade_id,
        symbol="XAUUSD",
        direction=direction,
        signal_time=entry_time - 60,
        signal_time_iso="2026-09-01T00:00:00+00:00",
        entry_time=entry_time,
        entry_time_iso="2026-09-01T00:01:00+00:00",
        exit_time=entry_time + 600,
        exit_time_iso="2026-09-01T00:10:00+00:00",
        signal_strength=8,
        entry_price=2000.0,
        stop_loss=1998.0,
        take_profit_1=2002.0,
        take_profit_2=2004.0,
        exit_price=2002.0 if r_multiple > 0 else 1998.0,
        result=res,
        pnl=pnl,
        r_multiple=r_multiple,
        holding_minutes=10.0,
        exit_reason="Test trade"
    )


def test_expectancy_calculation():
    trades = [
        _make_sample_trade("1", 1700000000, "LONG", 1.0, 100.0),
        _make_sample_trade("2", 1700000600, "LONG", 1.5, 150.0),
        _make_sample_trade("3", 1700001200, "SHORT", -1.0, -100.0),
        _make_sample_trade("4", 1700001800, "SHORT", -1.0, -100.0),
    ]

    exp = compute_expectancy(trades)
    assert exp.win_probability == 0.50
    assert exp.loss_probability == 0.50
    assert exp.avg_winning_r == 1.25
    assert exp.avg_losing_r == 1.0
    # Expectancy = (0.5 * 1.25) - (0.5 * 1.0) = 0.625 - 0.5 = 0.125
    assert exp.expectancy_per_trade == 0.125


def test_drawdown_analysis():
    trades = [
        _make_sample_trade("1", 1700000000, "LONG", 1.0, 100.0),
        _make_sample_trade("2", 1700000600, "LONG", -1.0, -100.0),
        _make_sample_trade("3", 1700001200, "LONG", -1.0, -100.0),
        _make_sample_trade("4", 1700001800, "SHORT", 2.0, 200.0),
    ]

    dd = compute_drawdown_analysis(trades, initial_capital=10000.0)
    assert dd.max_drawdown_usd == 200.0
    assert dd.max_losing_streak == 2
    assert dd.recovery_factor is not None


def test_monthly_metrics_and_concentration():
    # Jan 2026: 1767225600, Feb 2026: 1769904000
    t_jan = 1767225600 + 3600
    t_feb = 1769904000 + 3600

    trades = [
        _make_sample_trade("1", t_jan, "LONG", 3.0, 300.0),
        _make_sample_trade("2", t_jan + 600, "LONG", 2.0, 200.0),
        _make_sample_trade("3", t_feb, "SHORT", 1.0, 100.0),
    ]

    monthly = compute_monthly_metrics(trades, initial_capital=10000.0)
    assert len(monthly) == 2

    # Total R is 5.0 + 1.0 = 6.0
    conc = compute_period_concentration(monthly, total_r=6.0)
    assert conc.top_1_month_r == 5.0
    assert conc.top_1_month_pct > 80.0
