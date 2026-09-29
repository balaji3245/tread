import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from app.backtest_models import (
    BacktestStatistics,
    BacktestTrade,
    DirectionStat,
    EquityPoint,
    SessionStat,
    StrengthStat,
)


def determine_session(utc_timestamp: int) -> str:
    """
    Classify trade timestamp into market session based on explicit UTC hour:
    - Asia: 00:00 - 08:00 UTC
    - London: 08:00 - 13:00 UTC
    - NY/London Overlap: 13:00 - 16:00 UTC
    - New York Afternoon: 16:00 - 21:00 UTC
    - Off-Session: 21:00 - 24:00 UTC
    """
    dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    hour = dt.hour
    if 0 <= hour < 8:
        return "Asia"
    elif 8 <= hour < 13:
        return "London"
    elif 13 <= hour < 16:
        return "London/NY Overlap"
    elif 16 <= hour < 21:
        return "New York"
    else:
        return "Off-Session"


def compute_statistics(
    trades: List[BacktestTrade],
    total_signals: int,
    initial_capital: float = 10000.0,
    risk_per_trade_usd: float = 100.0
) -> Tuple[BacktestStatistics, List[EquityPoint]]:
    """
    Compute comprehensive mathematical statistics, breakdowns, and equity curve from simulated trades.
    """
    if not trades:
        empty_equity = [
            EquityPoint(
                time=int(datetime.now(timezone.utc).timestamp()),
                time_iso=datetime.now(timezone.utc).isoformat(),
                equity=initial_capital,
                drawdown=0.0,
                drawdown_pct=0.0
            )
        ]
        return BacktestStatistics(total_signals=total_signals), empty_equity

    total_trades = len(trades)
    long_trades = sum(1 for t in trades if t.direction == "LONG")
    short_trades = sum(1 for t in trades if t.direction == "SHORT")

    winning_trades = [t for t in trades if t.r_multiple > 0]
    losing_trades = [t for t in trades if t.r_multiple < 0]
    expired_trades = [t for t in trades if t.result == "EXPIRED"]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    expired_count = len(expired_trades)

    win_rate = round((win_count / total_trades) * 100.0, 2)

    r_list = [t.r_multiple for t in trades]
    total_r = round(sum(r_list), 2)
    avg_r = round(statistics.mean(r_list), 2) if r_list else 0.0
    med_r = round(statistics.median(r_list), 2) if r_list else 0.0

    gross_profit = sum(t.pnl for t in winning_trades)
    gross_loss = abs(sum(t.pnl for t in losing_trades))
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 2)
    elif gross_profit > 0:
        profit_factor = 999.0
    else:
        profit_factor = 0.0

    avg_win_r = round(statistics.mean([t.r_multiple for t in winning_trades]), 2) if winning_trades else 0.0
    avg_loss_r = round(statistics.mean([t.r_multiple for t in losing_trades]), 2) if losing_trades else 0.0
    largest_win_r = round(max(r_list), 2) if r_list else 0.0
    largest_loss_r = round(min(r_list), 2) if r_list else 0.0

    # Build Equity Curve & Drawdown
    equity_curve: List[EquityPoint] = []
    current_equity = initial_capital
    peak_equity = initial_capital
    max_dd = 0.0
    max_dd_pct = 0.0

    # Initial start point
    start_time = trades[0].entry_time
    equity_curve.append(
        EquityPoint(
            time=start_time,
            time_iso=datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
            equity=round(current_equity, 2),
            drawdown=0.0,
            drawdown_pct=0.0
        )
    )

    for trade in trades:
        current_equity += trade.pnl
        if current_equity > peak_equity:
            peak_equity = current_equity

        dd = peak_equity - current_equity
        dd_pct = (dd / peak_equity) * 100.0 if peak_equity > 0 else 0.0

        if dd > max_dd:
            max_dd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

        equity_curve.append(
            EquityPoint(
                time=trade.exit_time,
                time_iso=datetime.fromtimestamp(trade.exit_time, tz=timezone.utc).isoformat(),
                equity=round(current_equity, 2),
                drawdown=round(dd, 2),
                drawdown_pct=round(dd_pct, 2)
            )
        )

    # Calculate Streaks
    max_cons_wins = 0
    max_cons_losses = 0
    cur_wins = 0
    cur_losses = 0

    for r in r_list:
        if r > 0:
            cur_wins += 1
            cur_losses = 0
            if cur_wins > max_cons_wins:
                max_cons_wins = cur_wins
        elif r < 0:
            cur_losses += 1
            cur_wins = 0
            if cur_losses > max_cons_losses:
                max_cons_losses = cur_losses
        else:
            cur_wins = 0
            cur_losses = 0

    holding_times = [t.holding_minutes for t in trades]
    avg_holding = round(statistics.mean(holding_times), 1) if holding_times else 0.0
    max_holding = round(max(holding_times), 1) if holding_times else 0.0

    # Strength breakdown (7, 8, 9, 10)
    by_strength: List[StrengthStat] = []
    for s_val in [7, 8, 9, 10]:
        s_trades = [t for t in trades if t.signal_strength == s_val]
        if s_trades:
            s_wins = sum(1 for t in s_trades if t.r_multiple > 0)
            s_loss = sum(1 for t in s_trades if t.r_multiple < 0)
            s_r = sum(t.r_multiple for t in s_trades)
            s_gp = sum(t.pnl for t in s_trades if t.pnl > 0)
            s_gl = abs(sum(t.pnl for t in s_trades if t.pnl < 0))
            s_pf = round(s_gp / s_gl, 2) if s_gl > 0 else (999.0 if s_gp > 0 else 0.0)

            by_strength.append(
                StrengthStat(
                    strength=s_val,
                    total_trades=len(s_trades),
                    winning_trades=s_wins,
                    losing_trades=s_loss,
                    win_rate=round((s_wins / len(s_trades)) * 100.0, 2),
                    total_r=round(s_r, 2),
                    average_r=round(s_r / len(s_trades), 2),
                    profit_factor=s_pf
                )
            )

    # Direction breakdown
    by_direction: Dict[str, DirectionStat] = {}
    for d_val in ["LONG", "SHORT"]:
        d_trades = [t for t in trades if t.direction == d_val]
        if d_trades:
            d_wins = sum(1 for t in d_trades if t.r_multiple > 0)
            d_loss = sum(1 for t in d_trades if t.r_multiple < 0)
            d_r = sum(t.r_multiple for t in d_trades)
            d_gp = sum(t.pnl for t in d_trades if t.pnl > 0)
            d_gl = abs(sum(t.pnl for t in d_trades if t.pnl < 0))
            d_pf = round(d_gp / d_gl, 2) if d_gl > 0 else (999.0 if d_gp > 0 else 0.0)

            # Drawdown for direction
            d_peak = initial_capital
            d_eq = initial_capital
            d_max_dd = 0.0
            for t in d_trades:
                d_eq += t.pnl
                if d_eq > d_peak:
                    d_peak = d_eq
                if (d_peak - d_eq) > d_max_dd:
                    d_max_dd = d_peak - d_eq

            by_direction[d_val] = DirectionStat(
                direction=d_val,
                total_trades=len(d_trades),
                winning_trades=d_wins,
                losing_trades=d_loss,
                win_rate=round((d_wins / len(d_trades)) * 100.0, 2),
                total_r=round(d_r, 2),
                average_r=round(d_r / len(d_trades), 2),
                profit_factor=d_pf,
                max_drawdown=round(d_max_dd, 2)
            )

    # Session breakdown
    session_map: Dict[str, List[BacktestTrade]] = {}
    for t in trades:
        sess = t.session or determine_session(t.entry_time)
        session_map.setdefault(sess, []).append(t)

    by_session: List[SessionStat] = []
    for sess_name, sess_trades in session_map.items():
        s_wins = sum(1 for t in sess_trades if t.r_multiple > 0)
        s_loss = sum(1 for t in sess_trades if t.r_multiple < 0)
        s_r = sum(t.r_multiple for t in sess_trades)
        by_session.append(
            SessionStat(
                session=sess_name,
                total_trades=len(sess_trades),
                winning_trades=s_wins,
                losing_trades=s_loss,
                win_rate=round((s_wins / len(sess_trades)) * 100.0, 2),
                total_r=round(s_r, 2),
                average_r=round(s_r / len(sess_trades), 2)
            )
        )

    # Regime breakdown
    by_regime: Dict[str, Dict[str, Any]] = {}
    regime_map: Dict[str, List[BacktestTrade]] = {}
    for t in trades:
        reg = t.market_regime or "UNCLASSIFIED"
        regime_map.setdefault(reg, []).append(t)

    for reg_name, reg_trades in regime_map.items():
        r_wins = sum(1 for t in reg_trades if t.r_multiple > 0)
        r_r = sum(t.r_multiple for t in reg_trades)
        by_regime[reg_name] = {
            "total_trades": len(reg_trades),
            "winning_trades": r_wins,
            "win_rate": round((r_wins / len(reg_trades)) * 100.0, 2),
            "total_r": round(r_r, 2),
            "average_r": round(r_r / len(reg_trades), 2)
        }

    stats = BacktestStatistics(
        total_signals=total_signals,
        total_trades=total_trades,
        long_trades=long_trades,
        short_trades=short_trades,
        winning_trades=win_count,
        losing_trades=loss_count,
        expired_trades=expired_count,
        win_rate=win_rate,
        total_r=total_r,
        average_r=avg_r,
        median_r=med_r,
        profit_factor=profit_factor,
        average_win_r=avg_win_r,
        average_loss_r=avg_loss_r,
        largest_win_r=largest_win_r,
        largest_loss_r=largest_loss_r,
        max_drawdown=round(max_dd, 2),
        max_drawdown_pct=round(max_dd_pct, 2),
        max_consecutive_wins=max_cons_wins,
        max_consecutive_losses=max_cons_losses,
        average_holding_minutes=avg_holding,
        longest_holding_minutes=max_holding,
        by_strength=by_strength,
        by_direction=by_direction,
        by_session=by_session,
        by_regime=by_regime
    )

    return stats, equity_curve
