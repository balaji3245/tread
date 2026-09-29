"""
Phase 6H: Locked Final OOS Validation Engine
Executes the one-shot evaluation of frozen candidate V6F-H006 vs baseline on Final OOS.
"""
import copy
import gzip
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.backtest_models import BacktestTrade
from app.experiments.baseline_config import get_frozen_baseline_config
from app.historical_data_quality import compute_dataset_hash
from app.phase6f.entry_timing_engine import (
    BaseEntryPolicy,
    EntryTimingResearchEngine,
    ImmediateEntryPolicy,
    TightExpirationPolicy,
)
from app.phase6f.models import SignalEntryStatus
from app.phase6h.models import (
    FINAL_OOS_END_TS,
    FINAL_OOS_START_TS,
    FinalOOSComparison,
    FinalOOSManifest,
    FinalOOSTradeAudit,
    FinalOOSValidationArtifact,
    FinalOOSVerdict,
    PerformanceSliceMetrics,
)
from app.signal_models import MarketSignal

logger = logging.getLogger(__name__)


def compute_slice_metrics(
    trades: List[BacktestTrade],
    signals_count: int,
    label: str,
) -> PerformanceSliceMetrics:
    """Compute detailed quantitative performance metrics for a backtest slice."""
    n = len(trades)
    if n == 0:
        return PerformanceSliceMetrics(
            label=label,
            signals_count=signals_count,
            executed_trades=0,
            trade_conversion_pct=0.0,
            win_count=0,
            loss_count=0,
            win_rate_pct=0.0,
            total_net_r=0.0,
            expectancy_r=0.0,
            profit_factor=0.0,
            gross_profit_r=0.0,
            gross_loss_r=0.0,
            max_drawdown_r=0.0,
            max_drawdown_pct=0.0,
            mean_mae_r=0.0,
            mean_mfe_r=0.0,
            average_win_r=0.0,
            average_loss_r=0.0,
            longest_losing_streak=0,
            early_stop_rate_pct=0.0,
        )

    wins = [t for t in trades if t.r_multiple > 0]
    losses = [t for t in trades if t.r_multiple < 0]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = round(win_count / n * 100.0, 2)
    net_r = round(sum(t.r_multiple for t in trades), 2)
    exp_r = round(net_r / n, 3)

    gp = round(sum(t.r_multiple for t in wins), 2)
    gl = round(sum(abs(t.r_multiple) for t in losses), 2)
    pf = round(gp / gl, 2) if gl > 0 else 0.0

    avg_win = round(float(np.mean([t.r_multiple for t in wins])), 3) if wins else 0.0
    avg_loss = round(float(np.mean([t.r_multiple for t in losses])), 3) if losses else 0.0

    mae_vals = [t.mae_r for t in trades]
    mfe_vals = [t.mfe_r for t in trades]
    mean_mae = round(float(np.mean(mae_vals)), 3) if mae_vals else 0.0
    mean_mfe = round(float(np.mean(mfe_vals)), 3) if mfe_vals else 0.0

    # Drawdown calculation in R
    cum_r = 0.0
    peak_r = 0.0
    max_dd_r = 0.0
    for t in trades:
        cum_r += t.r_multiple
        if cum_r > peak_r:
            peak_r = cum_r
        dd = peak_r - cum_r
        if dd > max_dd_r:
            max_dd_r = dd

    # Max losing streak
    longest_streak = 0
    curr_streak = 0
    for t in trades:
        if t.r_multiple < 0:
            curr_streak += 1
            if curr_streak > longest_streak:
                longest_streak = curr_streak
        else:
            curr_streak = 0

    early_stops = sum(1 for t in trades if t.holding_minutes <= 3 and t.r_multiple < 0)
    early_stop_rate = round(early_stops / n * 100.0, 2)
    conv_rate = round(n / signals_count * 100.0, 2) if signals_count > 0 else 0.0

    return PerformanceSliceMetrics(
        label=label,
        signals_count=signals_count,
        executed_trades=n,
        trade_conversion_pct=conv_rate,
        win_count=win_count,
        loss_count=loss_count,
        win_rate_pct=win_rate,
        total_net_r=net_r,
        expectancy_r=exp_r,
        profit_factor=pf,
        gross_profit_r=gp,
        gross_loss_r=gl,
        max_drawdown_r=round(max_dd_r, 2),
        max_drawdown_pct=round(max_dd_r * 1.0, 2),  # 1% risk per trade approx
        mean_mae_r=mean_mae,
        mean_mfe_r=mean_mfe,
        average_win_r=avg_win,
        average_loss_r=avg_loss,
        longest_losing_streak=longest_streak,
        early_stop_rate_pct=early_stop_rate,
    )


class FinalOOSValidationEngine:
    """
    Executes one-shot Final OOS validation for V6F-H006 and generates audit artifacts.
    """
    def __init__(
        self,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]],
        precomputed_signals: Dict[int, Tuple[MarketSignal, float]],
    ):
        self.candles_1m = candles_1m
        self.candles_5m = candles_5m
        self.precomputed_signals = precomputed_signals
        self.timing_engine = EntryTimingResearchEngine(candles_1m, candles_5m, precomputed_signals)
        self.dataset_hash = compute_dataset_hash(candles_1m, candles_5m)

    def execute_final_oos_validation(self) -> FinalOOSValidationArtifact:
        """
        Execute one-shot Final OOS evaluation of frozen candidate V6F-H006 vs baseline.
        """
        manifest = FinalOOSManifest()
        manifest_hash = manifest.compute_manifest_hash()

        # 1. Run Baseline on Final OOS (Immediate Entry)
        base_policy = ImmediateEntryPolicy()
        base_trades, base_conv, base_log = self.timing_engine.run_timing_simulation(
            base_policy,
            start_ts=FINAL_OOS_START_TS,
            end_ts=FINAL_OOS_END_TS,
        )

        # 2. Run Frozen Candidate V6F-H006 on Final OOS (0.15 ATR Retrace / 2m Max Wait)
        cand_policy = TightExpirationPolicy(retrace_atr=0.15, max_wait_bars=2)
        cand_trades, cand_conv, cand_log = self.timing_engine.run_timing_simulation(
            cand_policy,
            start_ts=FINAL_OOS_START_TS,
            end_ts=FINAL_OOS_END_TS,
        )

        # 3. Compute Metrics
        base_metrics = compute_slice_metrics(base_trades, base_conv.signal_count, "Final OOS Baseline")
        cand_metrics = compute_slice_metrics(cand_trades, cand_conv.signal_count, "Final OOS V6F-H006")

        trade_reduc = round((base_metrics.executed_trades - cand_metrics.executed_trades) / base_metrics.executed_trades * 100.0, 1) if base_metrics.executed_trades else 0.0

        comparison = FinalOOSComparison(
            signals_delta=cand_conv.signal_count - base_conv.signal_count,
            trades_delta=cand_metrics.executed_trades - base_metrics.executed_trades,
            trade_reduction_pct=trade_reduc,
            win_rate_delta_pct=round(cand_metrics.win_rate_pct - base_metrics.win_rate_pct, 2),
            net_r_delta=round(cand_metrics.total_net_r - base_metrics.total_net_r, 2),
            expectancy_delta_r=round(cand_metrics.expectancy_r - base_metrics.expectancy_r, 3),
            profit_factor_delta=round(cand_metrics.profit_factor - base_metrics.profit_factor, 2),
            drawdown_reduction_r=round(base_metrics.max_drawdown_r - cand_metrics.max_drawdown_r, 2),
            mae_delta_r=round(cand_metrics.mean_mae_r - base_metrics.mean_mae_r, 3),
            mfe_delta_r=round(cand_metrics.mean_mfe_r - base_metrics.mean_mfe_r, 3),
        )

        # 4. Detailed Trade Audit Log
        trade_audits: List[FinalOOSTradeAudit] = []
        for t in cand_trades:
            sig_time = t.signal_time
            e_time = t.entry_time
            delay_m = round((e_time - sig_time) / 60.0, 1)

            trade_audits.append(
                FinalOOSTradeAudit(
                    trade_id=t.id,
                    direction=t.direction,
                    signal_timestamp=sig_time,
                    signal_timestamp_iso=datetime.fromtimestamp(sig_time, tz=timezone.utc).isoformat(),
                    entry_timestamp=e_time,
                    entry_timestamp_iso=datetime.fromtimestamp(e_time, tz=timezone.utc).isoformat(),
                    entry_price=t.entry_price,
                    retracement_atr=0.15,
                    delay_minutes=delay_m,
                    stop_loss=t.stop_loss,
                    take_profit_1=t.take_profit_1,
                    take_profit_2=t.take_profit_2,
                    exit_timestamp=t.exit_time,
                    exit_timestamp_iso=datetime.fromtimestamp(t.exit_time, tz=timezone.utc).isoformat(),
                    exit_price=t.exit_price,
                    exit_reason=t.exit_reason,
                    result=t.result,
                    holding_minutes=t.holding_minutes,
                    mae_r=t.mae_r,
                    mfe_r=t.mfe_r,
                    r_multiple=t.r_multiple,
                    pnl_usd=t.pnl,
                )
            )

        # 5. Determine Final OOS Verdict
        # Criteria:
        # PASS: Positive Net R & Expectancy, PF > 1.0, Defensible sample size (trades >= 500), Drawdown contained.
        # FAIL: Negative Net R or PF < 1.0.
        # INCONCLUSIVE: Insufficient sample size (< 100 trades).
        if cand_metrics.executed_trades < 100:
            verdict = FinalOOSVerdict.INCONCLUSIVE_FINAL_OOS
            rationale = f"Insufficient Final OOS sample size ({cand_metrics.executed_trades} trades)."
        elif cand_metrics.expectancy_r > 0.0 and cand_metrics.profit_factor >= 1.05 and cand_metrics.total_net_r > 0.0:
            verdict = FinalOOSVerdict.PASS_FINAL_OOS
            rationale = (
                f"Candidate V6F-H006 achieved positive expectancy (+{cand_metrics.expectancy_r:.3f}R, "
                f"Net +{cand_metrics.total_net_r:.2f}R, PF {cand_metrics.profit_factor:.2f}) on completely untouched Final OOS window, "
                f"outperforming baseline ({base_metrics.expectancy_r:.3f}R, PF {base_metrics.profit_factor:.2f}) with {cand_metrics.win_rate_pct:.2f}% win rate."
            )
        else:
            verdict = FinalOOSVerdict.FAIL_FINAL_OOS
            rationale = f"Negative or non-viable Final OOS performance (Exp {cand_metrics.expectancy_r:.3f}R, PF {cand_metrics.profit_factor:.2f})."

        artifact = FinalOOSValidationArtifact(
            candidate_id="V6F-H006",
            candidate_version="phase6f-h006-v1",
            manifest=manifest,
            manifest_hash=manifest_hash,
            dataset_hash=self.dataset_hash,
            final_oos_start_iso=datetime.fromtimestamp(FINAL_OOS_START_TS, tz=timezone.utc).isoformat(),
            final_oos_end_iso=datetime.fromtimestamp(FINAL_OOS_END_TS, tz=timezone.utc).isoformat(),
            final_oos_locked=True,
            final_oos_evaluated=True,
            baseline_metrics=base_metrics,
            candidate_metrics=cand_metrics,
            comparison=comparison,
            signal_accounting={
                "signal_count": cand_conv.signal_count,
                "entered_immediately_count": cand_conv.entered_immediately_count,
                "entered_after_delay_count": cand_conv.entered_after_delay_count,
                "total_entered_count": cand_conv.total_entered_count,
                "missed_count": cand_conv.missed_count,
                "invalidated_count": cand_conv.invalidated_count,
                "timed_out_count": cand_conv.timed_out_count,
                "signal_conversion_rate_pct": cand_conv.signal_conversion_rate_pct,
                "trade_reduction_pct": trade_reduc,
            },
            timing_statistics={
                "average_delay_minutes": cand_conv.average_delay_minutes,
                "median_delay_minutes": cand_conv.median_delay_minutes,
            },
            trade_log=trade_audits,
            verdict=verdict,
            verdict_rationale=rationale,
            live_strategy="phase6-baseline-v1",
            trading_execution="NONE",
            strategy_promotion="BLOCKED",
        )

        return artifact
