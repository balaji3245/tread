import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.backtest_models import BacktestTrade
from app.validation.validation_models import (
    DrawdownAnalysis,
    ExpectancyAnalysis,
    MonthlyMetricItem,
    OosConsistencyMetrics,
    OutOfSampleSummary,
    PeriodConcentration,
    PeriodMetricSummary,
    WalkForwardWindowResult,
)


def summarize_trades_slice(
    trades: List[BacktestTrade],
    signals_count: int,
    period_name: str,
    start_ts: int,
    end_ts: int,
    initial_capital: float = 10000.0,
    risk_per_trade_usd: float = 100.0
) -> PeriodMetricSummary:
    """
    Summarize a specific historical slice of trades into a PeriodMetricSummary.
    """
    start_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat()
    end_iso = datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat()

    if not trades:
        return PeriodMetricSummary(
            period_name=period_name,
            start_time=start_ts,
            start_iso=start_iso,
            end_time=end_ts,
            end_iso=end_iso,
            trades_count=0,
            signals_count=signals_count,
            winning_trades=0,
            losing_trades=0,
            expired_trades=0,
            win_rate=0.0,
            total_r=0.0,
            average_r=0.0,
            median_r=0.0,
            profit_factor=None,
            gross_profit_usd=0.0,
            gross_loss_usd=0.0,
            average_win_r=0.0,
            average_loss_r=0.0,
            largest_win_r=0.0,
            largest_loss_r=0.0,
            max_drawdown_usd=0.0,
            max_drawdown_pct=0.0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            avg_holding_minutes=0.0,
            long_trades=0,
            short_trades=0,
            long_win_rate=0.0,
            short_win_rate=0.0,
            long_total_r=0.0,
            short_total_r=0.0
        )

    n_trades = len(trades)
    winning = [t for t in trades if t.r_multiple > 0]
    losing = [t for t in trades if t.r_multiple < 0]
    expired = [t for t in trades if t.result == "EXPIRED"]

    win_count = len(winning)
    loss_count = len(losing)
    win_rate = round((win_count / n_trades) * 100.0, 2)

    r_list = [t.r_multiple for t in trades]
    total_r = round(sum(r_list), 2)
    avg_r = round(statistics.mean(r_list), 2)
    med_r = round(statistics.median(r_list), 2)

    gross_profit = round(sum(t.pnl for t in winning), 2)
    gross_loss = round(abs(sum(t.pnl for t in losing)), 2)

    if gross_loss > 0:
        profit_factor: Optional[float] = round(gross_profit / gross_loss, 2)
    elif gross_profit > 0:
        profit_factor = None  # Undefined / infinite profit factor
    else:
        profit_factor = 0.0

    avg_win_r = round(statistics.mean([t.r_multiple for t in winning]), 2) if winning else 0.0
    avg_loss_r = round(statistics.mean([t.r_multiple for t in losing]), 2) if losing else 0.0
    largest_win_r = round(max(r_list), 2)
    largest_loss_r = round(min(r_list), 2)

    # Drawdown calculation
    equity = initial_capital
    peak = initial_capital
    max_dd = 0.0
    max_dd_pct = 0.0
    is_depleted = False
    depletion_idx = None

    for idx, t in enumerate(trades):
        equity += t.pnl
        if equity <= 0 and not is_depleted:
            is_depleted = True
            depletion_idx = idx
        if equity > peak:
            peak = equity
        dd = peak - equity
        dd_pct = (dd / peak) * 100.0 if peak > 0 else (100.0 if dd > 0 else 0.0)
        if dd > max_dd:
            max_dd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

    # Streaks
    max_wins = 0
    max_loss = 0
    cur_w = 0
    cur_l = 0
    for r in r_list:
        if r > 0:
            cur_w += 1
            cur_l = 0
            if cur_w > max_wins:
                max_wins = cur_w
        elif r < 0:
            cur_l += 1
            cur_w = 0
            if cur_l > max_loss:
                max_loss = cur_l
        else:
            cur_w = 0
            cur_l = 0

    holdings = [t.holding_minutes for t in trades]
    avg_holding = round(statistics.mean(holdings), 1) if holdings else 0.0

    # Direction breakdown
    longs = [t for t in trades if t.direction == "LONG"]
    shorts = [t for t in trades if t.direction == "SHORT"]

    long_wins = sum(1 for t in longs if t.r_multiple > 0)
    short_wins = sum(1 for t in shorts if t.r_multiple > 0)

    long_wr = round((long_wins / len(longs)) * 100.0, 2) if longs else 0.0
    short_wr = round((short_wins / len(shorts)) * 100.0, 2) if shorts else 0.0

    long_r = round(sum(t.r_multiple for t in longs), 2) if longs else 0.0
    short_r = round(sum(t.r_multiple for t in shorts), 2) if shorts else 0.0

    return PeriodMetricSummary(
        period_name=period_name,
        start_time=start_ts,
        start_iso=start_iso,
        end_time=end_ts,
        end_iso=end_iso,
        trades_count=n_trades,
        signals_count=signals_count,
        winning_trades=win_count,
        losing_trades=loss_count,
        expired_trades=len(expired),
        win_rate=win_rate,
        total_r=total_r,
        average_r=avg_r,
        median_r=med_r,
        profit_factor=profit_factor,
        gross_profit_usd=gross_profit,
        gross_loss_usd=gross_loss,
        average_win_r=avg_win_r,
        average_loss_r=avg_loss_r,
        largest_win_r=largest_win_r,
        largest_loss_r=largest_loss_r,
        max_drawdown_usd=round(max_dd, 2),
        max_drawdown_pct=round(max_dd_pct, 2),
        max_consecutive_wins=max_wins,
        max_consecutive_losses=max_loss,
        avg_holding_minutes=avg_holding,
        long_trades=len(longs),
        short_trades=len(shorts),
        long_win_rate=long_wr,
        short_win_rate=short_wr,
        long_total_r=long_r,
        short_total_r=short_r,
        is_equity_depleted=is_depleted,
        depletion_trade_index=depletion_idx,
        equity_status="EQUITY_DEPLETION" if is_depleted else "SOLVENT"
    )


def compute_expectancy(trades: List[BacktestTrade]) -> ExpectancyAnalysis:
    """Calculate mathematical expectancy per trade and risk/reward characteristics."""
    if not trades:
        return ExpectancyAnalysis(
            expectancy_per_trade=0.0,
            win_probability=0.0,
            loss_probability=0.0,
            avg_winning_r=0.0,
            avg_losing_r=0.0,
            risk_reward_ratio=0.0
        )

    winning = [t for t in trades if t.r_multiple > 0]
    losing = [t for t in trades if t.r_multiple < 0]
    n = len(trades)

    win_prob = round(len(winning) / n, 4)
    loss_prob = round(len(losing) / n, 4)

    avg_win_r = round(statistics.mean([t.r_multiple for t in winning]), 2) if winning else 0.0
    avg_loss_r = round(abs(statistics.mean([t.r_multiple for t in losing])), 2) if losing else 0.0

    rrr = round(avg_win_r / avg_loss_r, 2) if avg_loss_r > 0 else 0.0
    expectancy = round((win_prob * avg_win_r) - (loss_prob * avg_loss_r), 3)

    return ExpectancyAnalysis(
        expectancy_per_trade=expectancy,
        win_probability=win_prob,
        loss_probability=loss_prob,
        avg_winning_r=avg_win_r,
        avg_losing_r=avg_loss_r,
        risk_reward_ratio=rrr
    )


def compute_drawdown_analysis(trades: List[BacktestTrade], initial_capital: float = 10000.0) -> DrawdownAnalysis:
    """Compute granular drawdown profile and losing streak distributions."""
    if not trades:
        return DrawdownAnalysis(
            max_drawdown_usd=0.0,
            max_drawdown_pct=0.0,
            avg_drawdown_usd=0.0,
            num_drawdowns=0,
            longest_drawdown_duration_trades=0,
            max_losing_streak=0,
            avg_losing_streak=0.0,
            recovery_factor=None
        )

    equity = initial_capital
    peak = initial_capital
    max_dd = 0.0
    max_dd_pct = 0.0
    is_depleted = False
    depletion_idx = None

    drawdowns: List[float] = []
    in_drawdown = False
    current_dd_trades = 0
    longest_dd_trades = 0

    losing_streaks: List[int] = []
    current_loss_streak = 0

    for idx, t in enumerate(trades):
        equity += t.pnl
        if equity <= 0 and not is_depleted:
            is_depleted = True
            depletion_idx = idx
        if equity >= peak:
            if in_drawdown:
                in_drawdown = False
                if current_dd_trades > longest_dd_trades:
                    longest_dd_trades = current_dd_trades
                current_dd_trades = 0
            peak = equity
        else:
            in_drawdown = True
            current_dd_trades += 1
            dd = peak - equity
            dd_pct = (dd / peak) * 100.0 if peak > 0 else (100.0 if dd > 0 else 0.0)
            drawdowns.append(dd)
            if dd > max_dd:
                max_dd = dd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        if t.r_multiple < 0:
            current_loss_streak += 1
        else:
            if current_loss_streak > 0:
                losing_streaks.append(current_loss_streak)
                current_loss_streak = 0

    if in_drawdown and current_dd_trades > longest_dd_trades:
        longest_dd_trades = current_dd_trades
    if current_loss_streak > 0:
        losing_streaks.append(current_loss_streak)

    total_profit = equity - initial_capital
    recovery_factor = round(total_profit / max_dd, 2) if max_dd > 0 else (999.0 if total_profit > 0 else 0.0)
    avg_dd = round(statistics.mean(drawdowns), 2) if drawdowns else 0.0
    avg_loss_streak = round(statistics.mean(losing_streaks), 1) if losing_streaks else 0.0
    max_loss_streak = max(losing_streaks) if losing_streaks else 0

    return DrawdownAnalysis(
        max_drawdown_usd=round(max_dd, 2),
        max_drawdown_pct=round(max_dd_pct, 2),
        avg_drawdown_usd=avg_dd,
        num_drawdowns=len(drawdowns),
        longest_drawdown_duration_trades=longest_dd_trades,
        max_losing_streak=max_loss_streak,
        avg_losing_streak=avg_loss_streak,
        recovery_factor=recovery_factor,
        is_equity_depleted=is_depleted,
        depletion_trade_index=depletion_idx,
        equity_status="EQUITY_DEPLETION" if is_depleted else "SOLVENT"
    )


def compute_monthly_metrics(
    trades: List[BacktestTrade],
    candles_1m: Optional[List[Dict[str, Any]]] = None,
    candles_5m: Optional[List[Dict[str, Any]]] = None,
    initial_capital: float = 10000.0
) -> List[MonthlyMetricItem]:
    """Group trade results by month and compute performance metrics for each month."""
    if not trades:
        return []

    month_groups: Dict[str, List[BacktestTrade]] = {}
    for t in trades:
        dt = datetime.fromtimestamp(t.entry_time, tz=timezone.utc)
        ym = dt.strftime("%Y-%m")
        month_groups.setdefault(ym, []).append(t)

    # Index candles by month if provided
    c1_by_month: Dict[str, int] = {}
    if candles_1m:
        for c in candles_1m:
            ym = datetime.fromtimestamp(int(c["time"]), tz=timezone.utc).strftime("%Y-%m")
            c1_by_month[ym] = c1_by_month.get(ym, 0) + 1

    c5_by_month: Dict[str, int] = {}
    if candles_5m:
        for c in candles_5m:
            ym = datetime.fromtimestamp(int(c["time"]), tz=timezone.utc).strftime("%Y-%m")
            c5_by_month[ym] = c5_by_month.get(ym, 0) + 1

    monthly_items: List[MonthlyMetricItem] = []
    for ym in sorted(month_groups.keys()):
        m_trades = month_groups[ym]
        dt = datetime.strptime(ym, "%Y-%m").replace(tzinfo=timezone.utc)
        month_name = dt.strftime("%B %Y")

        n = len(m_trades)
        wins = sum(1 for t in m_trades if t.r_multiple > 0)
        losses = sum(1 for t in m_trades if t.r_multiple < 0)
        win_rate = round((wins / n) * 100.0, 2) if n > 0 else 0.0

        r_vals = [t.r_multiple for t in m_trades]
        total_r = round(sum(r_vals), 2)
        avg_r = round(statistics.mean(r_vals), 2) if r_vals else 0.0

        gp = sum(t.pnl for t in m_trades if t.pnl > 0)
        gl = abs(sum(t.pnl for t in m_trades if t.pnl < 0))
        if gl > 0:
            pf: Optional[float] = round(gp / gl, 2)
        elif gp > 0:
            pf = None
        else:
            pf = 0.0

        # Month drawdown
        m_eq = initial_capital
        m_peak = initial_capital
        m_max_dd = 0.0
        for t in m_trades:
            m_eq += t.pnl
            if m_eq > m_peak:
                m_peak = m_eq
            dd = m_peak - m_eq
            if dd > m_max_dd:
                m_max_dd = dd

        long_count = sum(1 for t in m_trades if t.direction == "LONG")
        short_count = sum(1 for t in m_trades if t.direction == "SHORT")

        c1_count = c1_by_month.get(ym, 0)
        c5_count = c5_by_month.get(ym, 0)
        completeness_str = "100%" if c1_count >= 20000 else f"{round((c1_count / 30000) * 100)}%" if c1_count > 0 else "N/A"

        monthly_items.append(
            MonthlyMetricItem(
                year_month=ym,
                month_name=month_name,
                trades=n,
                winning_trades=wins,
                losing_trades=losses,
                win_rate=win_rate,
                total_r=total_r,
                average_r=avg_r,
                profit_factor=pf,
                max_drawdown_usd=round(m_max_dd, 2),
                long_trades=long_count,
                short_trades=short_count,
                candle_count_1m=c1_count,
                candle_count_5m=c5_count,
                data_completeness=completeness_str
            )
        )

    return monthly_items


def compute_period_concentration(monthly_items: List[MonthlyMetricItem], total_r: float) -> PeriodConcentration:
    """Analyze whether performance is concentrated in a small number of months."""
    if not monthly_items or total_r == 0.0:
        return PeriodConcentration(
            total_r=total_r,
            top_1_month_r=0.0,
            top_1_month_pct=0.0,
            top_1_month_label="None",
            top_2_month_r=0.0,
            top_2_month_pct=0.0,
            top_3_month_r=0.0,
            top_3_month_pct=0.0,
            top_month_removed_total_r=total_r,
            description="No monthly data available for concentration analysis."
        )

    # Sort months by total R descending
    sorted_months = sorted(monthly_items, key=lambda m: m.total_r, reverse=True)

    top1 = sorted_months[0]
    top1_r = top1.total_r
    top1_pct = round((top1_r / total_r) * 100.0, 1) if total_r > 0 else 0.0

    top2_r = top1_r + (sorted_months[1].total_r if len(sorted_months) > 1 else 0.0)
    top2_pct = round((top2_r / total_r) * 100.0, 1) if total_r > 0 else 0.0

    top3_r = top2_r + (sorted_months[2].total_r if len(sorted_months) > 2 else 0.0)
    top3_pct = round((top3_r / total_r) * 100.0, 1) if total_r > 0 else 0.0

    top_removed_r = round(total_r - top1_r, 2)
    desc = (
        f"Top month ({top1.month_name}) contributed {top1_r:+.2f}R ({top1_pct}% of total return). "
        f"Excluding top month, aggregate return is {top_removed_r:+.2f}R."
    )

    return PeriodConcentration(
        total_r=total_r,
        top_1_month_r=round(top1_r, 2),
        top_1_month_pct=top1_pct,
        top_1_month_label=top1.month_name,
        top_2_month_r=round(top2_r, 2),
        top_2_month_pct=top2_pct,
        top_3_month_r=round(top3_r, 2),
        top_3_month_pct=top3_pct,
        top_month_removed_total_r=top_removed_r,
        description=desc
    )


def compute_oos_consistency_metrics(
    monthly_items: List[MonthlyMetricItem],
    oos_windows: List[WalkForwardWindowResult],
    total_r: float
) -> OosConsistencyMetrics:
    """
    Compute objective stability & consistency statistics across months and OOS validation windows.
    """
    pos_months = sum(1 for m in monthly_items if m.total_r > 0)
    month_frac = round(pos_months / len(monthly_items), 3) if monthly_items else 0.0

    oos_r_list = [w.validation_metrics.total_r for w in oos_windows]
    pos_oos = sum(1 for r in oos_r_list if r > 0)
    oos_frac = round(pos_oos / len(oos_windows), 3) if oos_windows else 0.0

    m_r_list = [m.total_r for m in monthly_items]
    med_m_r = round(statistics.median(m_r_list), 2) if m_r_list else 0.0
    med_oos_r = round(statistics.median(oos_r_list), 2) if oos_r_list else 0.0

    std_m_r = round(statistics.stdev(m_r_list), 2) if len(m_r_list) >= 2 else 0.0
    std_oos_r = round(statistics.stdev(oos_r_list), 2) if len(oos_r_list) >= 2 else 0.0

    # Best / worst months
    best_m = max(monthly_items, key=lambda m: m.total_r) if monthly_items else None
    worst_m = min(monthly_items, key=lambda m: m.total_r) if monthly_items else None

    # Best / worst OOS windows
    best_oos = max(oos_windows, key=lambda w: w.validation_metrics.total_r) if oos_windows else None
    worst_oos = min(oos_windows, key=lambda w: w.validation_metrics.total_r) if oos_windows else None

    best_m_str = f"{best_m.month_name} ({best_m.total_r:+.2f}R)" if best_m else None
    worst_m_str = f"{worst_m.month_name} ({worst_m.total_r:+.2f}R)" if worst_m else None

    best_oos_str = f"Window #{best_oos.window_index} ({best_oos.validation_metrics.total_r:+.2f}R)" if best_oos else None
    worst_oos_str = f"Window #{worst_oos.window_index} ({worst_oos.validation_metrics.total_r:+.2f}R)" if worst_oos else None

    top_m_r = best_m.total_r if best_m else 0.0
    top_removed_r = round(total_r - top_m_r, 2)
    impact_str = f"Excluding {best_m.month_name if best_m else 'top month'} adjusts total return from {total_r:+.2f}R to {top_removed_r:+.2f}R."

    return OosConsistencyMetrics(
        positive_month_fraction=month_frac,
        positive_oos_window_fraction=oos_frac,
        median_monthly_r=med_m_r,
        median_oos_window_r=med_oos_r,
        std_dev_monthly_r=std_m_r,
        std_dev_oos_r=std_oos_r,
        largest_positive_month=best_m_str,
        largest_negative_month=worst_m_str,
        largest_positive_oos_window=best_oos_str,
        largest_negative_oos_window=worst_oos_str,
        top_month_removed_total_r=top_removed_r,
        top_month_removed_impact=impact_str
    )


def aggregate_out_of_sample(oos_windows: List[PeriodMetricSummary]) -> OutOfSampleSummary:
    """Aggregate multiple out-of-sample validation windows into a consolidated OOS summary."""
    if not oos_windows:
        return OutOfSampleSummary(
            oos_periods_count=0,
            positive_oos_periods=0,
            negative_oos_periods=0,
            profitable_period_fraction=0.0,
            total_oos_trades=0,
            total_oos_r=0.0,
            average_oos_r=0.0,
            oos_profit_factor=None,
            oos_max_drawdown_usd=0.0,
            oos_max_drawdown_pct=0.0,
            oos_expectancy=0.0,
            windows=[]
        )

    pos_count = sum(1 for w in oos_windows if w.total_r > 0)
    neg_count = sum(1 for w in oos_windows if w.total_r <= 0)
    frac = round(pos_count / len(oos_windows), 3) if oos_windows else 0.0

    tot_trades = sum(w.trades_count for w in oos_windows)
    tot_r = round(sum(w.total_r for w in oos_windows), 2)
    avg_r = round(tot_r / tot_trades, 2) if tot_trades > 0 else 0.0

    gross_p = sum(w.gross_profit_usd for w in oos_windows)
    gross_l = sum(w.gross_loss_usd for w in oos_windows)
    if gross_l > 0:
        oos_pf: Optional[float] = round(gross_p / gross_l, 2)
    elif gross_p > 0:
        oos_pf = None
    else:
        oos_pf = 0.0

    max_dd = max([w.max_drawdown_usd for w in oos_windows], default=0.0)
    max_dd_pct = max([w.max_drawdown_pct for w in oos_windows], default=0.0)

    # Combined OOS expectancy = average OOS R per trade
    expectancy = avg_r

    return OutOfSampleSummary(
        oos_periods_count=len(oos_windows),
        positive_oos_periods=pos_count,
        negative_oos_periods=neg_count,
        profitable_period_fraction=frac,
        total_oos_trades=tot_trades,
        total_oos_r=tot_r,
        average_oos_r=avg_r,
        oos_profit_factor=oos_pf,
        oos_max_drawdown_usd=round(max_dd, 2),
        oos_max_drawdown_pct=round(max_dd_pct, 2),
        oos_expectancy=expectancy,
        windows=oos_windows
    )
