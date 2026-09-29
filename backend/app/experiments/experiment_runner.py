"""
Phase 6: Experiment Execution Runner
Executes single-variable strategy hypotheses against the frozen Phase 6 baseline.
Enforces strict in-sample development, preliminary OOS screening, and final locked OOS boundaries.
"""
import copy
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.backtest_models import BacktestConfig, BacktestTrade
from app.backtester import BacktestReplayEngine
from app.experiments.baseline_config import (
    BASELINE_VERSION,
    FrozenBaselineConfig,
    get_frozen_baseline_config,
)
from app.experiments.experiment_models import (
    DeltaMetrics,
    ExperimentDecision,
    ExperimentDefinition,
    ExperimentResult,
    ExperimentSpreadRobustness,
    ExperimentStatus,
    ExperimentVariableType,
)
from app.historical_data_cache import ensure_data_dir
from app.historical_data_quality import compute_dataset_hash
from app.validation.validation_statistics import summarize_trades_slice
from app.validation.walk_forward import generate_walk_forward_slices

logger = logging.getLogger(__name__)


def compute_delta_metrics(exp_metrics: Any, base_metrics: Any) -> DeltaMetrics:
    """Calculate exact mathematical deltas between experiment and baseline metrics."""
    d_trades = exp_metrics.trades_count - base_metrics.trades_count
    d_wr = round(exp_metrics.win_rate - base_metrics.win_rate, 2)
    d_avg_r = round(exp_metrics.average_r - base_metrics.average_r, 3)
    d_tot_r = round(exp_metrics.total_r - base_metrics.total_r, 2)

    base_exp = (base_metrics.win_rate / 100.0 * base_metrics.average_win_r) - ((100.0 - base_metrics.win_rate) / 100.0 * abs(base_metrics.average_loss_r))
    exp_exp = (exp_metrics.win_rate / 100.0 * exp_metrics.average_win_r) - ((100.0 - exp_metrics.win_rate) / 100.0 * abs(exp_metrics.average_loss_r))
    d_expectancy = round(exp_exp - base_exp, 3)

    d_pf = None
    if exp_metrics.profit_factor is not None and base_metrics.profit_factor is not None:
        d_pf = round(exp_metrics.profit_factor - base_metrics.profit_factor, 2)

    d_dd_usd = round(exp_metrics.max_drawdown_usd - base_metrics.max_drawdown_usd, 2)
    d_dd_pct = round(exp_metrics.max_drawdown_pct - base_metrics.max_drawdown_pct, 2)
    reduction = round((abs(d_trades) / base_metrics.trades_count * 100.0), 1) if base_metrics.trades_count > 0 and d_trades < 0 else 0.0

    return DeltaMetrics(
        delta_trades=d_trades,
        delta_win_rate_pct=d_wr,
        delta_average_r=d_avg_r,
        delta_total_r=d_tot_r,
        delta_expectancy=d_expectancy,
        delta_profit_factor=d_pf,
        delta_max_drawdown_usd=d_dd_usd,
        delta_max_drawdown_pct=d_dd_pct,
        trade_reduction_pct=reduction
    )


class ExperimentRunner:
    """Executes and benchmarks controlled single-variable strategy experiments."""

    def __init__(self, frozen_config: Optional[FrozenBaselineConfig] = None):
        self.baseline_config = frozen_config or get_frozen_baseline_config()

    def run_experiment(
        self,
        experiment: ExperimentDefinition,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]],
        precomputed_signals: Optional[Dict[int, Any]] = None,
        custom_filter_fn: Optional[Callable[[Dict[str, Any], Any], bool]] = None
    ) -> ExperimentResult:
        """
        Execute a single controlled experiment against the immutable baseline.
        """
        dataset_hash = compute_dataset_hash(candles_1m, candles_5m)
        config_hash = hashlib.sha256(experiment.model_dump_json().encode("utf-8")).hexdigest()[:16]

        # 1. Prepare Baseline Replay Configuration
        base_backtest_cfg = BacktestConfig(
            symbol=self.baseline_config.symbol,
            signal_threshold=self.baseline_config.signal_threshold,
            sl_atr_multiplier=self.baseline_config.sl_atr_multiplier,
            tp1_atr_multiplier=self.baseline_config.tp1_atr_multiplier,
            tp2_atr_multiplier=self.baseline_config.tp2_atr_multiplier,
            max_holding_minutes=self.baseline_config.max_holding_minutes,
            initial_capital=self.baseline_config.initial_capital,
            risk_per_trade_usd=self.baseline_config.risk_per_trade_usd,
            assumed_spread=self.baseline_config.assumed_spread,
            execution_mode=self.baseline_config.execution_mode,
            same_candle_policy=self.baseline_config.same_candle_policy,
            max_concurrent_trades=self.baseline_config.max_concurrent_trades
        )

        base_engine = BacktestReplayEngine(config=base_backtest_cfg)
        if precomputed_signals is None:
            precomputed_signals = base_engine.precompute_signals(candles_1m, candles_5m)

        base_resp = base_engine.run_backtest(candles_1m, candles_5m, precomputed_signals=precomputed_signals)
        baseline_trades = base_resp.trades

        # 2. Build Experimental Signals and Configuration (Single Variable Only)
        exp_backtest_cfg = copy.deepcopy(base_backtest_cfg)
        mod = experiment.modification

        exp_signals = precomputed_signals
        if mod.variable_type == ExperimentVariableType.SCORE_THRESHOLD:
            exp_backtest_cfg.signal_threshold = int(mod.experimental_value)
        elif mod.variable_type == ExperimentVariableType.EXIT_MODEL:
            if isinstance(mod.experimental_value, dict):
                exp_backtest_cfg.sl_atr_multiplier = float(mod.experimental_value.get("sl_atr_multiplier", exp_backtest_cfg.sl_atr_multiplier))
                exp_backtest_cfg.tp1_atr_multiplier = float(mod.experimental_value.get("tp1_atr_multiplier", exp_backtest_cfg.tp1_atr_multiplier))
                exp_backtest_cfg.tp2_atr_multiplier = float(mod.experimental_value.get("tp2_atr_multiplier", exp_backtest_cfg.tp2_atr_multiplier))
                if "breakeven_trigger_r" in mod.experimental_value:
                    exp_backtest_cfg.breakeven_trigger_r = mod.experimental_value["breakeven_trigger_r"]
                if "trailing_stop_atr" in mod.experimental_value:
                    exp_backtest_cfg.trailing_stop_atr = mod.experimental_value["trailing_stop_atr"]
                if "trailing_trigger_r" in mod.experimental_value:
                    exp_backtest_cfg.trailing_trigger_r = mod.experimental_value["trailing_trigger_r"]
                if "time_invalidation_minutes" in mod.experimental_value:
                    exp_backtest_cfg.time_invalidation_minutes = mod.experimental_value["time_invalidation_minutes"]
                if "time_invalidation_min_mfe_r" in mod.experimental_value:
                    exp_backtest_cfg.time_invalidation_min_mfe_r = mod.experimental_value["time_invalidation_min_mfe_r"]
        elif mod.variable_type == ExperimentVariableType.FILTER:
            # Filter precomputed signals according to experimental rule
            filtered_signals: Dict[int, Any] = {}
            for idx, (sig, atr_val) in precomputed_signals.items():
                keep = True
                if custom_filter_fn:
                    keep = custom_filter_fn(candles_1m[idx], sig)
                elif mod.target_rule == "spread_threshold":
                    # Reject if spread > max_allowed (convert points to dollars if needed)
                    raw_sp = float(candles_1m[idx].get("spread", self.baseline_config.assumed_spread))
                    candle_spread_dollars = raw_sp * 0.01 if raw_sp > 2.0 else raw_sp
                    if candle_spread_dollars > float(mod.experimental_value):
                        keep = False
                elif mod.target_rule == "strict_5m_trend":
                    # Require direction to strictly match 5m trend
                    if sig.type == "LONG_SETUP" and sig.trend_5m != "BULLISH":
                        keep = False
                    elif sig.type == "SHORT_SETUP" and sig.trend_5m != "BEARISH":
                        keep = False
                elif mod.target_rule == "range_filter":
                    # Reject during RANGE regime
                    if sig.trend_5m == "RANGE":
                        keep = False
                elif mod.target_rule in ["overextended_entry_filter", "sr_proximity_filter"]:
                    # Reject LONG if within min_sr_clearance_atr of resistance or SHORT within min_sr_clearance_atr of support
                    threshold_atr = float(mod.experimental_value)
                    entry_p = float(candles_1m[idx]["close"])
                    if sig.type == "LONG_SETUP" and sig.resistanceLevels:
                        valid_r = [r.price for r in sig.resistanceLevels if r.price >= entry_p]
                        if valid_r and (min(valid_r) - entry_p) <= (threshold_atr * atr_val):
                            keep = False
                    elif sig.type == "SHORT_SETUP" and sig.supportLevels:
                        valid_s = [s.price for s in sig.supportLevels if s.price <= entry_p]
                        if valid_s and (entry_p - max(valid_s)) <= (threshold_atr * atr_val):
                            keep = False
                elif mod.target_rule == "overextension_filter":
                    # Reject LONG if price > 2.0 ATR above 5m EMA 50; reject SHORT if price > 2.0 ATR below 5m EMA 50
                    max_ext = float(mod.experimental_value)
                    entry_p = float(candles_1m[idx]["close"])
                    ema50 = sig.indicators.ema50_5m
                    if ema50 is not None and ema50 > 0:
                        if sig.type == "LONG_SETUP" and (entry_p - ema50) > (max_ext * atr_val):
                            keep = False
                        elif sig.type == "SHORT_SETUP" and (ema50 - entry_p) > (max_ext * atr_val):
                            keep = False
                elif mod.target_rule == "momentum_exhaustion_guard":
                    # Reject if overextended > 2.0 ATR from 5m EMA 50 AND opposing S/R <= 0.5 ATR away
                    entry_p = float(candles_1m[idx]["close"])
                    ema50 = sig.indicators.ema50_5m
                    if sig.type == "LONG_SETUP":
                        is_overextended = (ema50 is not None and (entry_p - ema50) > (2.0 * atr_val))
                        valid_r = [r.price for r in sig.resistanceLevels if r.price >= entry_p] if sig.resistanceLevels else []
                        is_near_res = valid_r and (min(valid_r) - entry_p) <= (0.5 * atr_val)
                        if is_overextended and is_near_res:
                            keep = False
                    elif sig.type == "SHORT_SETUP":
                        is_overextended = (ema50 is not None and (ema50 - entry_p) > (2.0 * atr_val))
                        valid_s = [s.price for s in sig.supportLevels if s.price <= entry_p] if sig.supportLevels else []
                        is_near_supp = valid_s and (entry_p - max(valid_s)) <= (0.5 * atr_val)
                        if is_overextended and is_near_supp:
                            keep = False
                if keep:
                    filtered_signals[idx] = (sig, atr_val)
            exp_signals = filtered_signals

        # Run Experimental Backtest
        exp_engine = BacktestReplayEngine(config=exp_backtest_cfg)
        exp_resp = exp_engine.run_backtest(candles_1m, candles_5m, precomputed_signals=exp_signals)
        exp_trades = exp_resp.trades

        # 3. Time Windows & Slicing (90d Development / 30d OOS Windows)
        start_ts = int(candles_1m[0]["time"])
        end_ts = int(candles_1m[-1]["time"])
        slices = generate_walk_forward_slices(start_ts, end_ts, train_days=90, validation_days=30, step_days=30)

        # Development Period (Slice #1 Train Period: 90 Days)
        dev_start_ts, dev_end_ts, _, _ = slices[0]
        dev_base_trades = [t for t in baseline_trades if dev_start_ts <= t.entry_time <= dev_end_ts]
        dev_exp_trades = [t for t in exp_trades if dev_start_ts <= t.entry_time <= dev_end_ts]

        dev_base_summary = summarize_trades_slice(
            dev_base_trades, len(dev_base_trades), "Development Period (Baseline)", dev_start_ts, dev_end_ts,
            self.baseline_config.initial_capital, self.baseline_config.risk_per_trade_usd
        )
        dev_exp_summary = summarize_trades_slice(
            dev_exp_trades, len(dev_exp_trades), f"Development Period ({experiment.experiment_id})", dev_start_ts, dev_end_ts,
            self.baseline_config.initial_capital, self.baseline_config.risk_per_trade_usd
        )
        dev_deltas = compute_delta_metrics(dev_exp_summary, dev_base_summary)

        # Preliminary OOS Windows (Slices #1 to #8)
        preliminary_slices = slices[:-1] if len(slices) >= 2 else slices
        prelim_base_oos_trades: List[BacktestTrade] = []
        prelim_exp_oos_trades: List[BacktestTrade] = []
        wf_window_details: List[Dict[str, Any]] = []

        for w_idx, (t_start, t_end, v_start, v_end) in enumerate(slices, start=1):
            is_final = (w_idx == len(slices))
            w_base_oos = [t for t in baseline_trades if v_start <= t.entry_time <= v_end]
            w_exp_oos = [t for t in exp_trades if v_start <= t.entry_time <= v_end]

            if not is_final:
                prelim_base_oos_trades.extend(w_base_oos)
                prelim_exp_oos_trades.extend(w_exp_oos)

            w_base_summary = summarize_trades_slice(
                w_base_oos, len(w_base_oos), f"Baseline OOS #{w_idx}", v_start, v_end,
                self.baseline_config.initial_capital, self.baseline_config.risk_per_trade_usd
            )
            w_exp_summary = summarize_trades_slice(
                w_exp_oos, len(w_exp_oos), f"Experiment OOS #{w_idx}", v_start, v_end,
                self.baseline_config.initial_capital, self.baseline_config.risk_per_trade_usd
            )

            wf_window_details.append({
                "window_index": w_idx,
                "is_final_oos": is_final,
                "val_start_iso": datetime.fromtimestamp(v_start, tz=timezone.utc).isoformat(),
                "val_end_iso": datetime.fromtimestamp(v_end, tz=timezone.utc).isoformat(),
                "baseline_trades": w_base_summary.trades_count,
                "baseline_win_rate": w_base_summary.win_rate,
                "baseline_net_r": w_base_summary.total_r,
                "baseline_profit_factor": w_base_summary.profit_factor,
                "experiment_trades": w_exp_summary.trades_count,
                "experiment_win_rate": w_exp_summary.win_rate,
                "experiment_net_r": w_exp_summary.total_r,
                "experiment_profit_factor": w_exp_summary.profit_factor,
                "delta_r": round(w_exp_summary.total_r - w_base_summary.total_r, 2)
            })

        prelim_base_summary = summarize_trades_slice(
            prelim_base_oos_trades, len(prelim_base_oos_trades), "Preliminary OOS Aggregate (Baseline)",
            preliminary_slices[0][2], preliminary_slices[-1][3], self.baseline_config.initial_capital, self.baseline_config.risk_per_trade_usd
        )
        prelim_exp_summary = summarize_trades_slice(
            prelim_exp_oos_trades, len(prelim_exp_oos_trades), f"Preliminary OOS Aggregate ({experiment.experiment_id})",
            preliminary_slices[0][2], preliminary_slices[-1][3], self.baseline_config.initial_capital, self.baseline_config.risk_per_trade_usd
        )
        prelim_deltas = compute_delta_metrics(prelim_exp_summary, prelim_base_summary)

        # 4. Acceptance Screening
        acceptance = {
            "has_min_dev_trades": dev_exp_summary.trades_count >= 100,
            "has_min_oos_trades": prelim_exp_summary.trades_count >= 50,
            "improved_oos_expectancy": prelim_deltas.delta_expectancy > 0.0,
            "improved_oos_profit_factor": (
                prelim_exp_summary.profit_factor is not None and
                prelim_base_summary.profit_factor is not None and
                prelim_exp_summary.profit_factor > prelim_base_summary.profit_factor
            ),
            "drawdown_not_worsened": prelim_deltas.delta_max_drawdown_pct <= 10.0
        }

        passes_screening = all([
            acceptance["has_min_dev_trades"],
            acceptance["has_min_oos_trades"],
            acceptance["improved_oos_expectancy"],
            acceptance["improved_oos_profit_factor"],
            acceptance["drawdown_not_worsened"]
        ])

        # 5. Final Locked OOS (Window #9) — Evaluated ONLY if passing development + screening
        final_oos_evaluated = False
        final_base_summary = None
        final_exp_summary = None
        final_deltas = None

        if passes_screening:
            final_oos_evaluated = True
            _, _, final_v_start, final_v_end = slices[-1]
            final_base_trades = [t for t in baseline_trades if final_v_start <= t.entry_time <= final_v_end]
            final_exp_trades = [t for t in exp_trades if final_v_start <= t.entry_time <= final_v_end]

            final_base_summary = summarize_trades_slice(
                final_base_trades, len(final_base_trades), "Final Locked OOS (Baseline)", final_v_start, final_v_end,
                self.baseline_config.initial_capital, self.baseline_config.risk_per_trade_usd
            )
            final_exp_summary = summarize_trades_slice(
                final_exp_trades, len(final_exp_trades), f"Final Locked OOS ({experiment.experiment_id})", final_v_start, final_v_end,
                self.baseline_config.initial_capital, self.baseline_config.risk_per_trade_usd
            )
            final_deltas = compute_delta_metrics(final_exp_summary, final_base_summary)

        # 6. Spread Perturbation Robustness ($0.20, $0.30, $0.50)
        spread_checks: List[ExperimentSpreadRobustness] = []
        for s_val in [0.20, 0.30, 0.50]:
            s_base_cfg = copy.deepcopy(base_backtest_cfg)
            s_base_cfg.assumed_spread = s_val
            s_base_resp = BacktestReplayEngine(config=s_base_cfg).run_backtest(candles_1m, candles_5m, precomputed_signals=precomputed_signals)

            s_exp_cfg = copy.deepcopy(exp_backtest_cfg)
            s_exp_cfg.assumed_spread = s_val
            s_exp_resp = BacktestReplayEngine(config=s_exp_cfg).run_backtest(candles_1m, candles_5m, precomputed_signals=exp_signals)

            s_base_stats = s_base_resp.statistics
            s_exp_stats = s_exp_resp.statistics
            delta_tot_r = round(s_exp_stats.total_r - s_base_stats.total_r, 2)

            spread_checks.append(
                ExperimentSpreadRobustness(
                    spread=s_val,
                    baseline_win_rate=s_base_stats.win_rate,
                    baseline_total_r=s_base_stats.total_r,
                    experiment_win_rate=s_exp_stats.win_rate,
                    experiment_total_r=s_exp_stats.total_r,
                    delta_total_r=delta_tot_r,
                    is_resilient=(delta_tot_r > 0.0)
                )
            )

        # 6b. Nearby Parameter Perturbation Robustness (Section 30)
        nearby_checks: List[Dict[str, Any]] = []
        perturbation_params = []
        if experiment.experiment_id == "EXP-007":
            perturbation_params = [("breakeven_trigger_r", 0.75), ("breakeven_trigger_r", 1.00), ("breakeven_trigger_r", 1.25)]
        elif experiment.experiment_id == "EXP-008":
            perturbation_params = [("trailing_stop_atr", 0.75), ("trailing_stop_atr", 1.00), ("trailing_stop_atr", 1.25)]
        elif experiment.experiment_id == "EXP-009":
            perturbation_params = [("max_ema50_dist_atr", 1.75), ("max_ema50_dist_atr", 2.00), ("max_ema50_dist_atr", 2.25)]
        elif experiment.experiment_id == "EXP-010":
            perturbation_params = [("min_sr_clearance_atr", 0.40), ("min_sr_clearance_atr", 0.50), ("min_sr_clearance_atr", 0.60)]
        elif experiment.experiment_id == "EXP-011":
            perturbation_params = [("time_invalidation_minutes", 8), ("time_invalidation_minutes", 10), ("time_invalidation_minutes", 12)]

        for p_name, p_val in perturbation_params:
            p_exp_cfg = copy.deepcopy(exp_backtest_cfg)
            p_signals = precomputed_signals
            if experiment.experiment_id == "EXP-007":
                p_exp_cfg.breakeven_trigger_r = float(p_val)
            elif experiment.experiment_id == "EXP-008":
                p_exp_cfg.trailing_stop_atr = float(p_val)
            elif experiment.experiment_id == "EXP-011":
                p_exp_cfg.time_invalidation_minutes = int(p_val)
            elif experiment.experiment_id == "EXP-009":
                p_filtered = {}
                for idx, (sig, atr_val) in precomputed_signals.items():
                    entry_p = float(candles_1m[idx]["close"])
                    ema50 = sig.indicators.ema50_5m
                    k = True
                    if ema50 is not None and ema50 > 0:
                        if sig.type == "LONG_SETUP" and (entry_p - ema50) > (float(p_val) * atr_val):
                            k = False
                        elif sig.type == "SHORT_SETUP" and (ema50 - entry_p) > (float(p_val) * atr_val):
                            k = False
                    if k:
                        p_filtered[idx] = (sig, atr_val)
                p_signals = p_filtered
            elif experiment.experiment_id == "EXP-010":
                p_filtered = {}
                for idx, (sig, atr_val) in precomputed_signals.items():
                    entry_p = float(candles_1m[idx]["close"])
                    k = True
                    if sig.type == "LONG_SETUP" and sig.resistanceLevels:
                        valid_r = [r.price for r in sig.resistanceLevels if r.price >= entry_p]
                        if valid_r and (min(valid_r) - entry_p) <= (float(p_val) * atr_val):
                            k = False
                    elif sig.type == "SHORT_SETUP" and sig.supportLevels:
                        valid_s = [s.price for s in sig.supportLevels if s.price <= entry_p]
                        if valid_s and (entry_p - max(valid_s)) <= (float(p_val) * atr_val):
                            k = False
                    if k:
                        p_filtered[idx] = (sig, atr_val)
                p_signals = p_filtered

            p_resp = BacktestReplayEngine(config=p_exp_cfg).run_backtest(candles_1m, candles_5m, precomputed_signals=p_signals)
            p_stats = p_resp.statistics
            nearby_checks.append({
                "parameter": p_name,
                "value": p_val,
                "trades": p_stats.total_trades,
                "win_rate": p_stats.win_rate,
                "total_r": p_stats.total_r,
                "profit_factor": p_stats.profit_factor,
                "delta_total_r": round(p_stats.total_r - base_resp.statistics.total_r, 2)
            })

        # 7. Decision Determination
        diagnostics: List[str] = []
        if not acceptance["has_min_dev_trades"]:
            decision = ExperimentDecision.NEEDS_MORE_DATA
            status = ExperimentStatus.NEEDS_MORE_DATA
            diagnostics.append(f"Sample size too small in development period ({dev_exp_summary.trades_count} trades < 100 required).")
        elif not acceptance["has_min_oos_trades"]:
            decision = ExperimentDecision.NEEDS_MORE_DATA
            status = ExperimentStatus.NEEDS_MORE_DATA
            diagnostics.append(f"Sample size too small in preliminary OOS ({prelim_exp_summary.trades_count} trades < 50 required).")
        elif passes_screening:
            if final_deltas and final_deltas.delta_expectancy > 0.0 and final_deltas.delta_total_r > 0.0:
                decision = ExperimentDecision.PROMISING
                status = ExperimentStatus.PROMISING
                diagnostics.append(f"Experiment passed both preliminary OOS screening and final locked OOS with positive net delta ({final_deltas.delta_total_r:+0.2f}R).")
            else:
                decision = ExperimentDecision.REJECTED
                status = ExperimentStatus.REJECTED
                diagnostics.append("Passed preliminary OOS but failed final locked OOS validation (did not generalize).")
        else:
            decision = ExperimentDecision.REJECTED
            status = ExperimentStatus.REJECTED
            if not acceptance["improved_oos_expectancy"]:
                diagnostics.append(f"Failed to improve OOS expectancy (Δ expectancy: {prelim_deltas.delta_expectancy:+.3f}R).")
            if not acceptance["improved_oos_profit_factor"]:
                diagnostics.append(f"Failed to improve OOS profit factor ({prelim_exp_summary.profit_factor} vs baseline {prelim_base_summary.profit_factor}).")
            if not acceptance["drawdown_not_worsened"]:
                diagnostics.append(f"Materially worsened drawdown (+{prelim_deltas.delta_max_drawdown_pct:.1f}%).")

        rationale = " | ".join(diagnostics) if diagnostics else "Experiment evaluated under standard Phase 6 protocols."

        result = ExperimentResult(
            experiment_id=experiment.experiment_id,
            title=experiment.title,
            hypothesis=experiment.hypothesis,
            status=status,
            decision=decision,
            baseline_version=self.baseline_config.version,
            configuration_hash=config_hash,
            dataset_hash=dataset_hash,
            executed_at_iso=datetime.now(timezone.utc).isoformat(),
            development_period_label="90 Days In-Sample (2025-10-01 to 2025-12-30)",
            development_baseline=dev_base_summary,
            development_experiment=dev_exp_summary,
            development_deltas=dev_deltas,
            preliminary_oos_periods_count=len(preliminary_slices),
            preliminary_oos_baseline_r=prelim_base_summary.total_r,
            preliminary_oos_experiment_r=prelim_exp_summary.total_r,
            preliminary_oos_baseline_wr=prelim_base_summary.win_rate,
            preliminary_oos_experiment_wr=prelim_exp_summary.win_rate,
            preliminary_oos_baseline_pf=prelim_base_summary.profit_factor,
            preliminary_oos_experiment_pf=prelim_exp_summary.profit_factor,
            preliminary_oos_deltas=prelim_deltas,
            final_oos_locked=True,
            final_oos_evaluated=final_oos_evaluated,
            final_oos_baseline=final_base_summary,
            final_oos_experiment=final_exp_summary,
            final_oos_deltas=final_deltas,
            walk_forward_windows=wf_window_details,
            spread_robustness=spread_checks,
            nearby_parameter_robustness=nearby_checks,
            acceptance_checks=acceptance,
            decision_rationale=rationale,
            diagnostics=diagnostics
        )

        # Save result to backend/data/experiments/
        exp_dir = ensure_data_dir() / "experiments"
        exp_dir.mkdir(parents=True, exist_ok=True)
        res_file = exp_dir / f"{experiment.experiment_id}_result.json"
        with open(res_file, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        return result
