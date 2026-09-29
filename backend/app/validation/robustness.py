import gzip
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.backtest_models import BacktestConfig
from app.backtester import BacktestReplayEngine
from app.historical_data_cache import atomic_write_gzip_json, ensure_data_dir
from app.historical_data_quality import audit_dataset_quality, compute_dataset_hash
from app.signal_models import MarketSignal
from app.validation.monte_carlo import run_monte_carlo
from app.validation.sensitivity import (
    run_exit_sensitivity,
    run_spread_sensitivity,
    run_threshold_sensitivity,
)
from app.validation.validation_models import (
    DatasetCoverage,
    DiagnosticFlag,
    ExitSensitivityItem,
    MonthlyMetricItem,
    OosConsistencyMetrics,
    OutOfSampleSummary,
    PeriodConcentration,
    PeriodMetricSummary,
    RobustnessSummary,
    SpreadSensitivityItem,
    ThresholdSensitivityItem,
    ValidationRequest,
    ValidationResponse,
    ValidationStatus,
    WalkForwardWindowResult,
)
from app.validation.validation_statistics import (
    aggregate_out_of_sample,
    compute_drawdown_analysis,
    compute_expectancy,
    compute_monthly_metrics,
    compute_oos_consistency_metrics,
    compute_period_concentration,
    summarize_trades_slice,
)
from app.validation.walk_forward import run_walk_forward_validation

logger = logging.getLogger(__name__)


def generate_robustness_flags(
    baseline_summary: PeriodMetricSummary,
    oos_summary: OutOfSampleSummary,
    spread_items: List[SpreadSensitivityItem],
    threshold_items: List[ThresholdSensitivityItem],
    exit_items: List[ExitSensitivityItem],
    concentration: PeriodConcentration,
    max_dd_pct: float,
    history_days: int,
    oos_windows_count: int,
    data_complete: bool
) -> List[DiagnosticFlag]:
    """
    Generate factual, evidence-backed diagnostic flags for strategy robustness.
    Strictly reports measured numbers without subjective investment claims.
    """
    flags: List[DiagnosticFlag] = []

    # 1. Historical Data Sufficiency Flags
    if history_days < 180:
        flags.append(
            DiagnosticFlag(
                code="INSUFFICIENT_HISTORY",
                severity="CAUTION",
                title="Insufficient Historical Duration",
                measured_evidence=(
                    f"Dataset spans only {history_days} days (< 180 days minimum requirement). "
                    "At least 6-12 months of historical data is required for meaningful multi-period validation."
                )
            )
        )
    elif history_days < 350:
        flags.append(
            DiagnosticFlag(
                code="LIMITED_HISTORY",
                severity="INFO",
                title="Limited Historical Duration",
                measured_evidence=(
                    f"Dataset spans {history_days} days (180-349 days). "
                    "Meets minimum threshold but 350+ days is recommended for full 12-month coverage."
                )
            )
        )

    if not data_complete:
        flags.append(
            DiagnosticFlag(
                code="INCOMPLETE_DATASET",
                severity="WARNING",
                title="Incomplete Historical Range",
                measured_evidence=(
                    "Requested date range was not completely covered by the available MT5 broker history."
                )
            )
        )

    # 2. Walk-Forward OOS Window Sufficiency Flags
    if oos_windows_count < 1:
        flags.append(
            DiagnosticFlag(
                code="INSUFFICIENT_OOS_WINDOWS",
                severity="CAUTION",
                title="No Out-of-Sample Windows",
                measured_evidence="No walk-forward out-of-sample validation windows could be formed."
            )
        )
    elif oos_windows_count < 6:
        flags.append(
            DiagnosticFlag(
                code="INSUFFICIENT_OOS_WINDOWS",
                severity="WARNING",
                title="Insufficient Out-of-Sample Windows",
                measured_evidence=(
                    f"Only {oos_windows_count} OOS window(s) generated (< 6 required minimum for Phase 5 validation). "
                    "More historical data is required to substantiate walk-forward stability."
                )
            )
        )

    # 3. Sample Size Flag
    if baseline_summary.trades_count < 30:
        flags.append(
            DiagnosticFlag(
                code="LOW_SAMPLE_SIZE",
                severity="WARNING",
                title="Low Sample Size",
                measured_evidence=(
                    f"Baseline generated only {baseline_summary.trades_count} trades (< 30). "
                    "Sample size is too small for statistical certainty."
                )
            )
        )

    # 4. Out-of-Sample Performance Flags
    if oos_summary.oos_periods_count >= 1:
        if oos_summary.total_oos_trades < 30:
            flags.append(
                DiagnosticFlag(
                    code="LOW_OOS_SAMPLE",
                    severity="INFO",
                    title="Low Out-of-Sample Trade Count",
                    measured_evidence=(
                        f"Cumulative OOS trades across all windows is {oos_summary.total_oos_trades} (< 30)."
                    )
                )
            )

        if oos_summary.average_oos_r < 0 or oos_summary.total_oos_r < 0:
            flags.append(
                DiagnosticFlag(
                    code="NEGATIVE_OOS_EXPECTANCY",
                    severity="WARNING",
                    title="Negative Out-of-Sample Expectancy",
                    measured_evidence=(
                        f"Combined out-of-sample return across {oos_summary.oos_periods_count} validation windows is "
                        f"{oos_summary.total_oos_r:+.2f}R (average {oos_summary.average_oos_r:+.2f}R per trade)."
                    )
                )
            )

    # 5. Spread Sensitivity Flag
    if len(spread_items) >= 2:
        spread_0 = spread_items[0]
        spread_high = spread_items[-1]
        r_drop = spread_0.average_r - spread_high.average_r
        if r_drop >= 0.12 or (spread_0.total_r > 0 and spread_high.total_r < 0):
            flags.append(
                DiagnosticFlag(
                    code="HIGH_SPREAD_SENSITIVITY",
                    severity="WARNING",
                    title="High Spread Sensitivity",
                    measured_evidence=(
                        f"Average return changed from {spread_0.average_r:+.2f}R at ${spread_0.spread:.2f} spread "
                        f"to {spread_high.average_r:+.2f}R at ${spread_high.spread:.2f} spread (delta of {r_drop:.2f}R per trade)."
                    )
                )
            )

    # 6. Threshold Sensitivity Flag (Development Period)
    if len(threshold_items) >= 2:
        t_low = threshold_items[0]
        t_high = threshold_items[-1]
        if abs(t_low.win_rate - t_high.win_rate) > 20.0 or (t_high.trades < 10 and t_low.trades >= 30):
            flags.append(
                DiagnosticFlag(
                    code="HIGH_THRESHOLD_SENSITIVITY",
                    severity="INFO",
                    title="High Threshold Sensitivity (Development)",
                    measured_evidence=(
                        f"Score threshold {t_low.threshold}/10 generated {t_low.trades} trades ({t_low.win_rate}% win rate) "
                        f"vs threshold {t_high.threshold}/10 which had {t_high.trades} trades ({t_high.win_rate}% win rate)."
                    )
                )
            )

    # 7. Exit Multiplier Sensitivity Flag (Development Period)
    if len(exit_items) >= 2:
        tot_r_values = [e.total_r for e in exit_items]
        min_r = min(tot_r_values)
        max_r = max(tot_r_values)
        if (max_r - min_r) > 10.0:
            flags.append(
                DiagnosticFlag(
                    code="HIGH_EXIT_SENSITIVITY",
                    severity="INFO",
                    title="High Exit Sensitivity (Development)",
                    measured_evidence=(
                        f"Total return fluctuated between {min_r:+.2f}R and {max_r:+.2f}R across predefined ATR exit scenarios."
                    )
                )
            )

    # 8. Period Concentration Flag
    if concentration.top_1_month_pct > 50.0 and concentration.total_r > 0:
        flags.append(
            DiagnosticFlag(
                code="HIGH_PERIOD_CONCENTRATION",
                severity="WARNING",
                title="High Period Concentration",
                measured_evidence=(
                    f"Top month ({concentration.top_1_month_label}) accounted for {concentration.top_1_month_pct}% "
                    f"({concentration.top_1_month_r:+.2f}R) of total positive return."
                )
            )
        )

    # 9. Directional Asymmetry Flag
    if baseline_summary.long_trades > 5 and baseline_summary.short_trades > 5:
        wr_diff = abs(baseline_summary.long_win_rate - baseline_summary.short_win_rate)
        if wr_diff > 15.0 or (baseline_summary.long_total_r * baseline_summary.short_total_r < 0):
            flags.append(
                DiagnosticFlag(
                    code="DIRECTIONAL_ASYMMETRY",
                    severity="INFO",
                    title="Directional Performance Asymmetry",
                    measured_evidence=(
                        f"LONG setups win rate: {baseline_summary.long_win_rate}% ({baseline_summary.long_total_r:+.2f}R across {baseline_summary.long_trades} trades) "
                        f"vs SHORT setups win rate: {baseline_summary.short_win_rate}% ({baseline_summary.short_total_r:+.2f}R across {baseline_summary.short_trades} trades)."
                    )
                )
            )

    # 10. High Drawdown Flag
    if max_dd_pct >= 15.0:
        flags.append(
            DiagnosticFlag(
                code="HIGH_DRAWDOWN",
                severity="CAUTION",
                title="High Historical Drawdown",
                measured_evidence=(
                    f"Maximum observed drawdown reached {max_dd_pct:.1f}% (${baseline_summary.max_drawdown_usd:.2f}) "
                    "relative to peak capital."
                )
            )
        )

    return flags


def run_strategy_validation(
    candles_1m: List[Dict[str, Any]],
    candles_5m: List[Dict[str, Any]],
    req: ValidationRequest,
    requested_start_ts: Optional[int] = None,
    requested_end_ts: Optional[int] = None
) -> ValidationResponse:
    """
    Execute end-to-end multi-period strategy validation, chronological walk-forward analysis,
    sensitivity matrices, Monte Carlo trade-order simulation, and robustness diagnostics.
    """
    if len(candles_1m) < 40 or len(candles_5m) < 15:
        raise ValueError(
            f"Insufficient historical candles for validation. Provided 1m: {len(candles_1m)}, 5m: {len(candles_5m)}."
        )

    # 1. Dataset Timestamps & Quality Audit
    start_ts = int(candles_1m[0]["time"])
    end_ts = int(candles_1m[-1]["time"])
    req_start_ts = requested_start_ts or start_ts
    req_end_ts = requested_end_ts or end_ts

    req_days = max(1, round((req_end_ts - req_start_ts) / 86400))
    avail_days = max(1, round((end_ts - start_ts) / 86400))

    # Audit Data Quality
    _, _, quality_report = audit_dataset_quality(
        candles_1m=candles_1m,
        candles_5m=candles_5m,
        requested_days=req_days,
        symbol=req.symbol
    )

    data_complete = (avail_days >= int(req_days * 0.90)) and (
        quality_report.invalid_candles_count_1m + quality_report.invalid_candles_count_5m == 0
    )

    if avail_days < 180:
        cov_status = "INSUFFICIENT_HISTORY"
    elif avail_days < 350:
        cov_status = "LIMITED_HISTORY"
    else:
        cov_status = "12_MONTH_HISTORY_AVAILABLE"

    dataset_hash = compute_dataset_hash(candles_1m, candles_5m)

    dataset_coverage = DatasetCoverage(
        requested_start_iso=datetime.fromtimestamp(req_start_ts, tz=timezone.utc).isoformat(),
        requested_end_iso=datetime.fromtimestamp(req_end_ts, tz=timezone.utc).isoformat(),
        actual_start_iso=datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(),
        actual_end_iso=datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat(),
        requested_days=req_days,
        available_days=avail_days,
        candle_count_1m=len(candles_1m),
        candle_count_5m=len(candles_5m),
        data_complete=data_complete,
        coverage_status=cov_status,
        dataset_hash=dataset_hash,
        source="Exness MT5"
    )

    # 2. Construct Baseline Configuration
    base_config = BacktestConfig(
        symbol=req.symbol,
        signal_threshold=req.signal_threshold,
        sl_atr_multiplier=req.sl_atr_multiplier,
        tp1_atr_multiplier=req.tp1_atr_multiplier,
        tp2_atr_multiplier=req.tp2_atr_multiplier,
        max_holding_minutes=req.max_holding_minutes,
        initial_capital=req.initial_capital,
        risk_per_trade_usd=req.risk_per_trade_usd,
        assumed_spread=req.assumed_spread,
        execution_mode=req.execution_mode,
        same_candle_policy=req.same_candle_policy,
        max_concurrent_trades=req.max_concurrent_trades
    )

    # 3. Run Baseline Replay over entire available historical range
    base_engine = BacktestReplayEngine(config=base_config)
    sig_cache_file = ensure_data_dir() / f"signals_{dataset_hash}_{base_config.signal_threshold}.json.gz"
    cached_signals = None
    if sig_cache_file.exists():
        try:
            with gzip.open(sig_cache_file, "rt", encoding="utf-8") as f:
                raw_sig_data = json.load(f)
                cached_signals = {
                    int(k): (MarketSignal(**v[0]), float(v[1]))
                    for k, v in raw_sig_data.items()
                }
        except Exception as e:
            logger.warning("Could not read precomputed signals cache: %s", e)
            cached_signals = None

    if cached_signals is None:
        cached_signals = base_engine.precompute_signals(candles_1m=candles_1m, candles_5m=candles_5m)
        try:
            raw_sig_dump = {
                str(k): (v[0].model_dump(), float(v[1]))
                for k, v in cached_signals.items()
            }
            atomic_write_gzip_json(sig_cache_file, raw_sig_dump)
        except Exception as e:
            logger.warning("Could not cache precomputed signals: %s", e)

    baseline_resp = base_engine.run_backtest(candles_1m=candles_1m, candles_5m=candles_5m, precomputed_signals=cached_signals)
    baseline_trades = baseline_resp.trades

    overall_metrics = summarize_trades_slice(
        trades=baseline_trades,
        signals_count=baseline_resp.statistics.total_signals,
        period_name="Full Evaluation Period",
        start_ts=start_ts,
        end_ts=end_ts,
        initial_capital=req.initial_capital,
        risk_per_trade_usd=req.risk_per_trade_usd
    )

    # 4. Granular Statistics & Breakdowns
    expectancy = compute_expectancy(baseline_trades)
    drawdown_analysis = compute_drawdown_analysis(baseline_trades, initial_capital=req.initial_capital)
    monthly_metrics = compute_monthly_metrics(
        trades=baseline_trades,
        initial_capital=req.initial_capital,
        candles_1m=candles_1m,
        candles_5m=candles_5m
    )
    concentration = compute_period_concentration(monthly_metrics, total_r=overall_metrics.total_r)

    # 5. Walk-Forward Chronological Validation
    wf_windows = run_walk_forward_validation(
        candles_1m=candles_1m,
        candles_5m=candles_5m,
        base_config=base_config,
        train_days=req.train_days,
        validation_days=req.validation_days,
        step_days=req.step_days,
        all_trades=baseline_trades
    )

    oos_summaries = [w.validation_metrics for w in wf_windows]
    oos_aggregated = aggregate_out_of_sample(oos_summaries)
    oos_consistency = compute_oos_consistency_metrics(
        monthly_items=monthly_metrics,
        oos_windows=wf_windows,
        total_r=overall_metrics.total_r
    )

    # 6. Separate Development Candles vs Locked Final OOS for Sensitivity Analysis
    # If final_oos_locked is True and we have walk-forward windows, threshold and exit sensitivities
    # are run strictly on development / in-sample history before the final OOS period.
    if req.final_oos_locked and wf_windows:
        final_window = wf_windows[-1]
        final_oos_start_ts = int(
            datetime.fromisoformat(final_window.validation_start_iso).replace(tzinfo=timezone.utc).timestamp()
        )
        dev_candles_1m = [c for c in candles_1m if int(c["time"]) < final_oos_start_ts]
        dev_candles_5m = [c for c in candles_5m if int(c["time"]) < final_oos_start_ts]
        if len(dev_candles_1m) < 40 or len(dev_candles_5m) < 15:
            dev_candles_1m = candles_1m
            dev_candles_5m = candles_5m
    else:
        dev_candles_1m = candles_1m
        dev_candles_5m = candles_5m

    # Spread sensitivity runs on the expanded dataset
    spread_sensitivity = run_spread_sensitivity(
        candles_1m=candles_1m,
        candles_5m=candles_5m,
        base_config=base_config,
        spread_values=req.spread_values,
        precomputed_signals=cached_signals
    )

    # Threshold & Exit sensitivity run strictly on Development / In-Sample data
    if dev_candles_1m is candles_1m or len(dev_candles_1m) == len(candles_1m):
        dev_signals = cached_signals
    else:
        dev_signals = {k: v for k, v in cached_signals.items() if k < len(dev_candles_1m)}

    threshold_sensitivity = run_threshold_sensitivity(
        candles_1m=dev_candles_1m,
        candles_5m=dev_candles_5m,
        base_config=base_config,
        threshold_values=req.threshold_values,
        precomputed_signals=dev_signals
    )

    exit_sensitivity = run_exit_sensitivity(
        candles_1m=dev_candles_1m,
        candles_5m=dev_candles_5m,
        base_config=base_config,
        precomputed_signals=dev_signals
    )

    # 7. Monte Carlo Trade-Order Simulation
    r_multiples = [t.r_multiple for t in baseline_trades]
    monte_carlo_res = run_monte_carlo(
        r_multiples=r_multiples,
        initial_capital=req.initial_capital,
        risk_per_trade_usd=req.risk_per_trade_usd,
        simulations=req.monte_carlo_simulations,
        random_seed=req.random_seed
    )

    # 8. Validation Status & Objective Flags
    if avail_days < 180:
        val_status_str = "INSUFFICIENT_HISTORY"
    elif len(wf_windows) < 6:
        val_status_str = "INSUFFICIENT_OOS_WINDOWS"
    elif avail_days < 350:
        val_status_str = "LIMITED_HISTORY"
    else:
        val_status_str = "VALIDATION_SUFFICIENT_COVERAGE"

    val_notes: List[str] = []
    if len(wf_windows) < 6:
        val_notes.append(f"Only {len(wf_windows)} OOS window(s) formed. Phase 5 requires minimum 6 windows for full multi-OOS validation.")
    if avail_days < 180:
        val_notes.append(f"Available history is {avail_days} days (< 180 days minimum).")
    if req.final_oos_locked:
        val_notes.append("Final out-of-sample period is locked against parameter tuning and optimization.")

    validation_status = ValidationStatus(
        status=val_status_str,
        history_days=avail_days,
        oos_windows=len(wf_windows),
        minimum_oos_windows=6,
        baseline_evaluated=True,
        final_oos_locked=req.final_oos_locked,
        parameter_optimization=False,
        notes=val_notes
    )

    flags = generate_robustness_flags(
        baseline_summary=overall_metrics,
        oos_summary=oos_aggregated,
        spread_items=spread_sensitivity,
        threshold_items=threshold_sensitivity,
        exit_items=exit_sensitivity,
        concentration=concentration,
        max_dd_pct=overall_metrics.max_drawdown_pct,
        history_days=avail_days,
        oos_windows_count=len(wf_windows),
        data_complete=data_complete
    )

    pos_periods = sum(1 for m in monthly_metrics if m.total_r > 0)
    neg_periods = sum(1 for m in monthly_metrics if m.total_r <= 0)
    prof_frac = round(pos_periods / len(monthly_metrics), 3) if monthly_metrics else 0.0

    robustness_summary = RobustnessSummary(
        periods_tested=len(monthly_metrics),
        positive_periods=pos_periods,
        negative_periods=neg_periods,
        profitable_period_fraction=prof_frac,
        oos_periods_tested=oos_aggregated.oos_periods_count,
        oos_positive_periods=oos_aggregated.positive_oos_periods,
        spread_sensitive=any(f.code == "HIGH_SPREAD_SENSITIVITY" for f in flags),
        threshold_sensitive=any(f.code == "HIGH_THRESHOLD_SENSITIVITY" for f in flags),
        exit_sensitive=any(f.code == "HIGH_EXIT_SENSITIVITY" for f in flags),
        flags=flags
    )

    # 9. Deterministic Configuration Hash & Run ID
    hash_payload = {
        "symbol": req.symbol,
        "start": start_ts,
        "end": end_ts,
        "candles_1m": len(candles_1m),
        "candles_5m": len(candles_5m),
        "config": base_config.model_dump()
    }
    config_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode()).hexdigest()[:16]
    run_date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    val_run_id = f"VAL-{run_date_str}-{config_hash[:6].upper()}"

    return ValidationResponse(
        validation_run_id=val_run_id,
        symbol=req.symbol,
        dataset_coverage=dataset_coverage,
        data_quality=quality_report,
        validation_status=validation_status,
        oos_consistency=oos_consistency,
        baseline_configuration=base_config.model_dump(),
        configuration_hash=config_hash,
        overall_metrics=overall_metrics,
        expectancy=expectancy,
        drawdown_analysis=drawdown_analysis,
        monthly=monthly_metrics,
        period_concentration=concentration,
        walk_forward=wf_windows,
        out_of_sample=oos_aggregated,
        spread_sensitivity=spread_sensitivity,
        threshold_sensitivity_development=threshold_sensitivity,
        exit_sensitivity_development=exit_sensitivity,
        direction_breakdown={
            k: v.model_dump() for k, v in baseline_resp.statistics.by_direction.items()
        },
        session_breakdown=[s.model_dump() for s in baseline_resp.statistics.by_session],
        regime_breakdown=baseline_resp.statistics.by_regime,
        monte_carlo=monte_carlo_res,
        diagnostics=flags,
        robustness_summary=robustness_summary
    )

