import pytest
from app.backtest_models import BacktestTrade
from app.backtest_statistics import compute_statistics, determine_session


def make_mock_trade(id_str: str, direction: str, pnl: float, r_mult: float, strength: int = 7, holding: float = 15.0, ts: int = 1700000000) -> BacktestTrade:
    res = "TP1" if r_mult > 0 else "STOP_LOSS"
    return BacktestTrade(
        id=id_str,
        symbol="XAUUSD",
        direction=direction, # "LONG" | "SHORT"
        signal_time=ts,
        signal_time_iso="2026-01-01T10:00:00Z",
        entry_time=ts + 60,
        entry_time_iso="2026-01-01T10:01:00Z",
        exit_time=ts + int(holding * 60),
        exit_time_iso="2026-01-01T10:15:00Z",
        signal_strength=strength,
        entry_price=2000.0,
        stop_loss=1998.0 if direction == "LONG" else 2002.0,
        take_profit_1=2002.0 if direction == "LONG" else 1998.0,
        take_profit_2=2004.0 if direction == "LONG" else 1996.0,
        exit_price=2002.0 if r_mult > 0 else 1998.0,
        result=res,
        pnl=pnl,
        r_multiple=r_mult,
        holding_minutes=holding,
        exit_reason="Target reached" if r_mult > 0 else "Stop hit"
    )


def test_session_classification():
    # 02:00 UTC -> Asia
    asia_ts = 1767232800  # 2026-01-01 02:00:00 UTC
    assert determine_session(asia_ts) == "Asia"

    # 09:00 UTC -> London
    london_ts = 1767258000  # 2026-01-01 09:00:00 UTC
    assert determine_session(london_ts) == "London"

    # 14:00 UTC -> London/NY Overlap
    overlap_ts = 1767276000  # 2026-01-01 14:00:00 UTC
    assert determine_session(overlap_ts) == "London/NY Overlap"

    # 18:00 UTC -> New York
    ny_ts = 1767290400  # 2026-01-01 18:00:00 UTC
    assert determine_session(ny_ts) == "New York"


def test_statistics_calculation():
    trades = [
        make_mock_trade("t1", "LONG", pnl=100.0, r_mult=1.0, strength=7),
        make_mock_trade("t2", "LONG", pnl=-100.0, r_mult=-1.0, strength=7),
        make_mock_trade("t3", "SHORT", pnl=200.0, r_mult=2.0, strength=8),
        make_mock_trade("t4", "SHORT", pnl=100.0, r_mult=1.0, strength=8),
        make_mock_trade("t5", "LONG", pnl=-100.0, r_mult=-1.0, strength=9),
    ]

    stats, equity = compute_statistics(trades, total_signals=10, initial_capital=10000.0)

    assert stats.total_trades == 5
    assert stats.winning_trades == 3
    assert stats.losing_trades == 2
    assert stats.win_rate == 60.0
    assert stats.total_r == 2.0
    assert stats.average_r == 0.4
    # Gross profit = 100+200+100 = 400. Gross loss = 200. Profit factor = 400/200 = 2.0
    assert stats.profit_factor == 2.0
    assert len(equity) == 6  # start + 5 trades

    # Strength breakdown checks
    assert len(stats.by_strength) == 3
    s7 = next(s for s in stats.by_strength if s.strength == 7)
    assert s7.total_trades == 2
    assert s7.win_rate == 50.0

    s8 = next(s for s in stats.by_strength if s.strength == 8)
    assert s8.total_trades == 2
    assert s8.win_rate == 100.0


def test_empty_statistics():
    stats, equity = compute_statistics([], total_signals=0, initial_capital=10000.0)
    assert stats.total_trades == 0
    assert stats.win_rate == 0.0
    assert len(equity) == 1
    assert equity[0].equity == 10000.0
