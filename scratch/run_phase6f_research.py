"""
Phase 6F: Entry Timing & Price-Path Forensic Runner
Executes comprehensive analysis across:
1. Baseline reproduction
2. Signal-to-entry path quantification & early adverse path analysis
3. Retracement & continuation path quantification
4. Delay horizons & signal decay (1m, 2m, 3m, 5m, 10m)
5. Candidate evaluation (V6F-H001 through V6F-H006) on Dev + Preliminary OOS W#1-#8
6. Final OOS strict lock and result serialization to backend/data/experiments/
"""
import copy
import gzip
import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.backtest_models import BacktestConfig, BacktestTrade
from app.backtester import BacktestReplayEngine
from app.experiments.baseline_config import BASELINE_VERSION, get_frozen_baseline_config
from app.historical_data_quality import compute_dataset_hash
from app.phase6f.entry_timing_engine import (
    BaseEntryPolicy,
    BreakoutContinuationPolicy,
    ControlledRetracementPolicy,
    EMAReversionPolicy,
    EntryTimingResearchEngine,
    HybridRetraceOrConfirmPolicy,
    ImmediateEntryPolicy,
    MomentumConfirmationPolicy,
    TightExpirationPolicy,
    assert_final_oos_locked,
)
from app.phase6f.models import (
    CandidateTimingResult,
    EarlyPathExcursion,
    EntryPriceQualityMetrics,
    FINAL_OOS_END_TS,
    FINAL_OOS_START_TS,
    PathForensicLabel,
    ProtectedFinalOOSAccessError,
    SignalConversionMetrics,
    SignalEntryStatus,
    TimingFeatureProvenance,
    WindowTimingMetrics,
)
from app.signal_models import MarketSignal
from app.validation.validation_statistics import summarize_trades_slice
from app.validation.walk_forward import generate_walk_forward_slices

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phase6f_runner")


def load_candles_and_signals() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[int, Tuple[MarketSignal, float]]]:
    data_dir = backend_dir / "data"
    c1_path = data_dir / "XAUUSD_1m.json.gz"
    c5_path = data_dir / "XAUUSD_5m.json.gz"
    sig_path = data_dir / "signals_e9db340c4efa9e63_7.json.gz"

    logger.info("Loading M1 candles...")
    with gzip.open(c1_path, "rt", encoding="utf-8") as f:
        candles_1m = json.load(f)

    logger.info("Loading M5 candles...")
    with gzip.open(c5_path, "rt", encoding="utf-8") as f:
        candles_5m = json.load(f)

    logger.info("Loading precomputed signals...")
    with gzip.open(sig_path, "rt", encoding="utf-8") as f:
        raw_signals = json.load(f)
        precomputed_signals = {int(k): (MarketSignal(**v[0]), float(v[1])) for k, v in raw_signals.items()}

    logger.info("Loaded %d 1m bars, %d 5m bars, %d signals", len(candles_1m), len(candles_5m), len(precomputed_signals))
    return candles_1m, candles_5m, precomputed_signals


def get_provenance_list() -> List[TimingFeatureProvenance]:
    return [
        TimingFeatureProvenance(
            feature_name="baseline_signal_strength",
            source_timeframe="5m+1m",
            calculation_timestamp=0,
            required_historical_bars=30,
            future_data_dependency=False,
            formula_description="Confluence rule score at closed bar T (threshold >= 7/10)."
        ),
        TimingFeatureProvenance(
            feature_name="signal_atr_14",
            source_timeframe="1m",
            calculation_timestamp=0,
            required_historical_bars=14,
            future_data_dependency=False,
            formula_description="14-period Wilder ATR calculated on closed 1m bars up to bar T."
        ),
        TimingFeatureProvenance(
            feature_name="ema21_anchor_displacement",
            source_timeframe="1m",
            calculation_timestamp=0,
            required_historical_bars=21,
            future_data_dependency=False,
            formula_description="Distance from bar T close to 1m EMA21 in ATR units."
        ),
        TimingFeatureProvenance(
            feature_name="causal_retrace_trigger",
            source_timeframe="1m",
            calculation_timestamp=0,
            required_historical_bars=1,
            future_data_dependency=False,
            formula_description="Intrabar limit price reached on subsequent 1m bar T+k without prior stop invalidation."
        ),
        TimingFeatureProvenance(
            feature_name="momentum_confirmation_trigger",
            source_timeframe="1m",
            calculation_timestamp=0,
            required_historical_bars=2,
            future_data_dependency=False,
            formula_description="Closed candle T+1 momentum and extreme breakout condition evaluated at T+2 open."
        ),
    ]


def main():
    candles_1m, candles_5m, precomputed_signals = load_candles_and_signals()
    ds_hash = compute_dataset_hash(candles_1m, candles_5m)
    logger.info("Dataset Hash: %s", ds_hash)

    engine = EntryTimingResearchEngine(candles_1m, candles_5m, precomputed_signals)
    
    # ---------------------------------------------------------
    # 1. Baseline Reproduction Check (phase6-baseline-v1)
    # ---------------------------------------------------------
    logger.info("=== STEP 1: Frozen Baseline Reproduction ===")
    base_policy = ImmediateEntryPolicy()
    base_trades, base_conv, _ = engine.run_timing_simulation(base_policy)
    
    n_base = len(base_trades)
    base_wins = sum(1 for t in base_trades if t.r_multiple > 0)
    base_losses = sum(1 for t in base_trades if t.r_multiple < 0)
    base_wr = round(base_wins / n_base * 100.0, 2)
    base_net_r = round(sum(t.r_multiple for t in base_trades), 2)
    base_avg_r = round(base_net_r / n_base, 3)
    base_gp = sum(t.r_multiple for t in base_trades if t.r_multiple > 0)
    base_gl = sum(abs(t.r_multiple) for t in base_trades if t.r_multiple < 0)
    base_pf = round(base_gp / base_gl, 2)
    base_mae = round(float(np.mean([t.mae_r for t in base_trades])), 3)
    base_mfe = round(float(np.mean([t.mfe_r for t in base_trades])), 3)
    base_early_stops = sum(1 for t in base_trades if t.holding_minutes <= 3 and t.r_multiple < 0)
    base_early_stop_rate = round(base_early_stops / n_base * 100.0, 2)
    base_reach_1r = round(sum(1 for t in base_trades if t.mfe_r >= 1.0) / n_base * 100.0, 2)
    base_reach_2r = round(sum(1 for t in base_trades if t.mfe_r >= 2.0) / n_base * 100.0, 2)

    logger.info(
        "Baseline Verified: %d trades, WR %.2f%%, Net R %.2fR, Avg R %.3fR, PF %.2f, MAE %.3fR, MFE %.3fR, Early Stop Rate %.2f%%",
        n_base, base_wr, base_net_r, base_avg_r, base_pf, base_mae, base_mfe, base_early_stop_rate
    )

    # ---------------------------------------------------------
    # 2. Forensic Path Analysis across Horizions (1m, 2m, 3m, 5m)
    # ---------------------------------------------------------
    logger.info("=== STEP 2: Forensic Signal-to-Entry Path Analysis ===")
    forensics = engine.compute_detailed_forensics(base_trades)
    logger.info("Forensic signal count: %d", forensics["total_signals"])
    logger.info("Path label distribution: %s", forensics["path_distribution"])
    logger.info("Instant Stopouts (1m MAE >= 1.0R): %d", forensics["instant_stop_count"])
    logger.info("Early Adverse then Recovery: %d", forensics["early_adverse_recovery_count"])

    # Path excursion summaries across all signals
    records: List[SignalTimingRecord] = forensics["records"]
    mfe_1m_mean = np.mean([r.path_1m.mfe_r for r in records if r.path_1m])
    mae_1m_mean = np.mean([r.path_1m.mae_r for r in records if r.path_1m])
    mfe_2m_mean = np.mean([r.path_2m.mfe_r for r in records if r.path_2m])
    mae_2m_mean = np.mean([r.path_2m.mae_r for r in records if r.path_2m])
    mfe_3m_mean = np.mean([r.path_3m.mfe_r for r in records if r.path_3m])
    mae_3m_mean = np.mean([r.path_3m.mae_r for r in records if r.path_3m])
    mfe_5m_mean = np.mean([r.path_5m.mfe_r for r in records if r.path_5m])
    mae_5m_mean = np.mean([r.path_5m.mae_r for r in records if r.path_5m])

    logger.info("Average 1m: MFE %.3fR | MAE %.3fR", mfe_1m_mean, mae_1m_mean)
    logger.info("Average 2m: MFE %.3fR | MAE %.3fR", mfe_2m_mean, mae_2m_mean)
    logger.info("Average 3m: MFE %.3fR | MAE %.3fR", mfe_3m_mean, mae_3m_mean)
    logger.info("Average 5m: MFE %.3fR | MAE %.3fR", mfe_5m_mean, mae_5m_mean)

    # ---------------------------------------------------------
    # 3. Delay Horizon & Signal Decay Study (1m, 2m, 3m, 5m, 10m)
    # ---------------------------------------------------------
    logger.info("=== STEP 3: Delay Horizon & Signal Decay Study ===")
    delay_horizons = [
        ("1m Retrace 0.20 ATR", ControlledRetracementPolicy(retrace_atr=0.20, max_wait_bars=1)),
        ("2m Retrace 0.20 ATR", ControlledRetracementPolicy(retrace_atr=0.20, max_wait_bars=2)),
        ("3m Retrace 0.20 ATR", ControlledRetracementPolicy(retrace_atr=0.20, max_wait_bars=3)),
        ("5m Retrace 0.20 ATR", ControlledRetracementPolicy(retrace_atr=0.20, max_wait_bars=5)),
        ("10m Retrace 0.20 ATR", ControlledRetracementPolicy(retrace_atr=0.20, max_wait_bars=10)),
    ]
    for d_name, d_policy in delay_horizons:
        d_trades, d_conv, _ = engine.run_timing_simulation(d_policy)
        d_net_r = sum(t.r_multiple for t in d_trades)
        d_avg_r = d_net_r / len(d_trades) if d_trades else 0.0
        d_wr = sum(1 for t in d_trades if t.r_multiple > 0) / len(d_trades) * 100.0 if d_trades else 0.0
        logger.info(
            "Delay Study [%s]: %d trades (reduc %.1f%%), conv %.1f%%, WR %.2f%%, Net R %.2fR, Exp %.3fR, avg delay %.2fm",
            d_name, len(d_trades), d_conv.trade_reduction_pct, d_conv.signal_conversion_rate_pct, d_wr, d_net_r, d_avg_r, d_conv.average_delay_minutes
        )

    # ---------------------------------------------------------
    # 4. Walk-Forward Window Setup (Dev 90d, Prelim OOS #1-#8)
    # ---------------------------------------------------------
    start_ts = int(candles_1m[0]["time"])
    end_ts = int(candles_1m[-1]["time"])
    slices = generate_walk_forward_slices(start_ts, end_ts, train_days=90, validation_days=30, step_days=30)
    dev_start_ts, dev_end_ts, _, _ = slices[0]
    preliminary_slices = slices[:-1]

    logger.info("Total slices: %d. Preliminary OOS slices: %d (Windows #1-#8). Final OOS: Window #9.", len(slices), len(preliminary_slices))

    # ---------------------------------------------------------
    # 5. Candidate Definitions (V6F-H001 to V6F-H006)
    # ---------------------------------------------------------
    candidates = [
        {
            "id": "V6F-H001",
            "title": "Controlled Retracement Entry (0.25 ATR / 3m Window)",
            "type": "RETRACEMENT",
            "desc": "Wait up to 3 minutes for price to retrace 0.25 ATR toward signal reference before entering. Invalidate if 1.0 ATR stop is breached prior to entry.",
            "policy": ControlledRetracementPolicy(retrace_atr=0.25, max_wait_bars=3),
        },
        {
            "id": "V6F-H002",
            "title": "1M EMA21 Reversion Entry (Max 5m Window)",
            "type": "EMA_REVERSION",
            "desc": "Wait up to 5 minutes for price to touch 1M EMA21 anchor. Invalidate if adverse move exceeds 1.2 ATR before touch.",
            "policy": EMAReversionPolicy(max_wait_bars=5),
        },
        {
            "id": "V6F-H003",
            "title": "1-Bar Momentum Confirmation Entry",
            "type": "CONFIRMATION",
            "desc": "Wait for 1 closed M1 candle; enter at next open (T+2) only if confirmation bar closed directionally and broke signal-bar extreme.",
            "policy": MomentumConfirmationPolicy(confirm_bars=1),
        },
        {
            "id": "V6F-H004",
            "title": "Breakout Continuation Entry (0.20 ATR Breakout / 2m Window)",
            "type": "BREAKOUT_CONTINUATION",
            "desc": "Enter if price breaks beyond signal-bar extreme by 0.20 ATR within 2 minutes. Invalidate if opposite extreme is broken.",
            "policy": BreakoutContinuationPolicy(breakout_atr=0.20, max_wait_bars=2),
        },
        {
            "id": "V6F-H005",
            "title": "Hybrid Retrace-or-Confirm State Machine (3m Window)",
            "type": "HYBRID_STATE_MACHINE",
            "desc": "Causal state machine: enter on 0.20 ATR retrace or 0.20 ATR breakout within 3m; cancel immediately on adverse invalidation.",
            "policy": HybridRetraceOrConfirmPolicy(retrace_atr=0.20, breakout_atr=0.20, max_wait_bars=3),
        },
        {
            "id": "V6F-H006",
            "title": "Tight Expiration Window (0.15 ATR Retrace / 2m Window)",
            "type": "EXPIRATION_LIMIT",
            "desc": "Strict short-delay entry requiring 0.15 ATR pullback within 2 minutes, fast timeout to prevent stale signal entry.",
            "policy": TightExpirationPolicy(retrace_atr=0.15, max_wait_bars=2),
        },
    ]

    exp_dir = backend_dir / "data" / "experiments"
    exp_dir.mkdir(exist_ok=True)

    candidate_results: List[CandidateTimingResult] = []

    for c_info in candidates:
        c_id = c_info["id"]
        c_title = c_info["title"]
        c_type = c_info["type"]
        c_desc = c_info["desc"]
        c_policy = c_info["policy"]

        logger.info("Evaluating candidate %s: %s...", c_id, c_title)

        # Run candidate full simulation
        c_trades, c_conv, _ = engine.run_timing_simulation(c_policy)

        # Development period (90 days)
        dev_base = [t for t in base_trades if dev_start_ts <= t.entry_time <= dev_end_ts]
        dev_cand = [t for t in c_trades if dev_start_ts <= t.entry_time <= dev_end_ts]

        dev_n = len(dev_cand)
        dev_wins = sum(1 for t in dev_cand if t.r_multiple > 0)
        dev_wr = round(dev_wins / dev_n * 100.0, 2) if dev_n > 0 else 0.0
        dev_net_r = round(sum(t.r_multiple for t in dev_cand), 2)
        dev_exp = round(dev_net_r / dev_n, 3) if dev_n > 0 else 0.0
        dev_gp = sum(t.r_multiple for t in dev_cand if t.r_multiple > 0)
        dev_gl = sum(abs(t.r_multiple) for t in dev_cand if t.r_multiple < 0)
        dev_pf = round(dev_gp / dev_gl, 2) if dev_gl > 0 else 0.0
        dev_reduc = round((len(dev_base) - dev_n) / len(dev_base) * 100.0, 1) if dev_base else 0.0

        # Preliminary OOS Windows #1 to #8
        window_metrics_list: List[WindowTimingMetrics] = []
        prelim_base_trades: List[BacktestTrade] = []
        prelim_cand_trades: List[BacktestTrade] = []
        positive_w = 0
        negative_w = 0
        window_exp_list: List[float] = []

        for w_idx, (t_start, t_end, v_start, v_end) in enumerate(preliminary_slices, start=1):
            # Assert Final OOS Guard
            assert_final_oos_locked(t_start, v_end)

            w_base = [t for t in base_trades if v_start <= t.entry_time <= v_end]
            w_cand = [t for t in c_trades if v_start <= t.entry_time <= v_end]

            prelim_base_trades.extend(w_base)
            prelim_cand_trades.extend(w_cand)

            w_n_base = len(w_base)
            w_n_cand = len(w_cand)
            w_reduc = round((w_n_base - w_n_cand) / w_n_base * 100.0, 1) if w_n_base > 0 else 0.0

            w_base_wins = sum(1 for t in w_base if t.r_multiple > 0)
            w_base_wr = round(w_base_wins / w_n_base * 100.0, 2) if w_n_base > 0 else 0.0
            w_base_net_r = sum(t.r_multiple for t in w_base)
            w_base_exp = round(w_base_net_r / w_n_base, 3) if w_n_base > 0 else 0.0
            w_base_gp = sum(t.r_multiple for t in w_base if t.r_multiple > 0)
            w_base_gl = sum(abs(t.r_multiple) for t in w_base if t.r_multiple < 0)
            w_base_pf = round(w_base_gp / w_base_gl, 2) if w_base_gl > 0 else 0.0

            w_cand_wins = sum(1 for t in w_cand if t.r_multiple > 0)
            w_cand_wr = round(w_cand_wins / w_n_cand * 100.0, 2) if w_n_cand > 0 else 0.0
            w_cand_net_r = round(sum(t.r_multiple for t in w_cand), 2)
            w_cand_exp = round(w_cand_net_r / w_n_cand, 3) if w_n_cand > 0 else 0.0
            w_cand_gp = sum(t.r_multiple for t in w_cand if t.r_multiple > 0)
            w_cand_gl = sum(abs(t.r_multiple) for t in w_cand if t.r_multiple < 0)
            w_cand_pf = round(w_cand_gp / w_cand_gl, 2) if w_cand_gl > 0 else 0.0
            w_cand_early_stops = sum(1 for t in w_cand if t.holding_minutes <= 3 and t.r_multiple < 0)
            w_cand_early_stop_rate = round(w_cand_early_stops / w_n_cand * 100.0, 2) if w_n_cand > 0 else 0.0

            delta_r = round(w_cand_net_r - w_base_net_r, 2)
            if w_cand_net_r > 0:
                positive_w += 1
            else:
                negative_w += 1
            window_exp_list.append(w_cand_exp)

            window_metrics_list.append(
                WindowTimingMetrics(
                    window_index=w_idx,
                    val_start_iso=datetime.fromtimestamp(v_start, tz=timezone.utc).isoformat(),
                    val_end_iso=datetime.fromtimestamp(v_end, tz=timezone.utc).isoformat(),
                    baseline_trades=w_n_base,
                    candidate_trades=w_n_cand,
                    trade_reduction_pct=w_reduc,
                    baseline_win_rate_pct=w_base_wr,
                    candidate_win_rate_pct=w_cand_wr,
                    baseline_expectancy_r=w_base_exp,
                    candidate_expectancy_r=w_cand_exp,
                    baseline_profit_factor=w_base_pf,
                    candidate_profit_factor=w_cand_pf,
                    candidate_net_r=w_cand_net_r,
                    delta_r=delta_r,
                    candidate_early_stop_rate_pct=w_cand_early_stop_rate,
                )
            )

        # Preliminary OOS Aggregates
        n_prelim_base = len(prelim_base_trades)
        n_prelim_cand = len(prelim_cand_trades)
        prelim_base_net_r = sum(t.r_multiple for t in prelim_base_trades)
        prelim_cand_net_r = round(sum(t.r_multiple for t in prelim_cand_trades), 2)
        prelim_delta_r = round(prelim_cand_net_r - prelim_base_net_r, 2)
        prelim_cand_wins = sum(1 for t in prelim_cand_trades if t.r_multiple > 0)
        prelim_cand_wr = round(prelim_cand_wins / n_prelim_cand * 100.0, 2) if n_prelim_cand > 0 else 0.0
        prelim_cand_exp = round(prelim_cand_net_r / n_prelim_cand, 3) if n_prelim_cand > 0 else 0.0
        prelim_gp = sum(t.r_multiple for t in prelim_cand_trades if t.r_multiple > 0)
        prelim_gl = sum(abs(t.r_multiple) for t in prelim_cand_trades if t.r_multiple < 0)
        prelim_cand_pf = round(prelim_gp / prelim_gl, 2) if prelim_gl > 0 else 0.0
        prelim_reduc = round((n_prelim_base - n_prelim_cand) / n_prelim_base * 100.0, 1) if n_prelim_base > 0 else 0.0

        # Price Quality and Excursions
        cand_mae_mean = round(float(np.mean([t.mae_r for t in c_trades])), 3) if c_trades else 0.0
        cand_mfe_mean = round(float(np.mean([t.mfe_r for t in c_trades])), 3) if c_trades else 0.0
        cand_early_stops = sum(1 for t in c_trades if t.holding_minutes <= 3 and t.r_multiple < 0)
        cand_early_stop_rate = round(cand_early_stops / len(c_trades) * 100.0, 2) if c_trades else 0.0
        cand_reach_1r = round(sum(1 for t in c_trades if t.mfe_r >= 1.0) / len(c_trades) * 100.0, 2) if c_trades else 0.0
        cand_reach_2r = round(sum(1 for t in c_trades if t.mfe_r >= 2.0) / len(c_trades) * 100.0, 2) if c_trades else 0.0

        # Map signal time to baseline vs candidate entry price
        base_price_map = {t.signal_time: (t.entry_price, max(0.50, abs(t.entry_price - t.stop_loss))) for t in base_trades}
        price_diffs_r = []
        price_diffs_atr = []
        for ct in c_trades:
            if ct.signal_time in base_price_map:
                bp, sl_d = base_price_map[ct.signal_time]
                if ct.direction == "LONG":
                    diff = bp - ct.entry_price  # positive means candidate bought lower
                else:
                    diff = ct.entry_price - bp  # positive means candidate sold higher
                c_sl_d = max(0.50, abs(ct.entry_price - ct.stop_loss))
                price_diffs_r.append(diff / sl_d)
                price_diffs_atr.append(diff / c_sl_d)

        avg_price_imp_r = round(float(np.mean(price_diffs_r)), 3) if price_diffs_r else 0.0
        med_price_imp_r = round(float(np.median(price_diffs_r)), 3) if price_diffs_r else 0.0
        atr_norm_imp = round(float(np.mean(price_diffs_atr)), 3) if price_diffs_atr else 0.0

        price_quality = EntryPriceQualityMetrics(
            average_price_improvement_r=avg_price_imp_r,
            median_price_improvement_r=med_price_imp_r,
            atr_normalized_improvement=atr_norm_imp,
            baseline_mean_mae_r=base_mae,
            candidate_mean_mae_r=cand_mae_mean,
            baseline_early_stop_rate_pct=base_early_stop_rate,
            candidate_early_stop_rate_pct=cand_early_stop_rate,
            baseline_mean_mfe_r=base_mfe,
            candidate_mean_mfe_r=cand_mfe_mean,
            baseline_reach_1r_pct=base_reach_1r,
            candidate_reach_1r_pct=cand_reach_1r,
            baseline_reach_2r_pct=base_reach_2r,
            candidate_reach_2r_pct=cand_reach_2r,
        )

        # Determine Decision
        # Rejection criteria:
        # 1. Negative preliminary OOS expectancy
        # 2. Profit factor < 1.0
        # 3. Excessive trade reduction > 85% or negative in majority of OOS windows
        is_promising = (
            prelim_cand_exp > 0.0 and
            prelim_cand_pf >= 1.0 and
            positive_w >= 5 and
            prelim_reduc <= 75.0
        )
        status = "PROMISING" if is_promising else "REJECTED"
        decision = status
        
        rationale_parts = []
        if prelim_cand_exp <= 0.0:
            rationale_parts.append(f"Negative preliminary OOS expectancy ({prelim_cand_exp:.3f}R).")
        if prelim_cand_pf < 1.0:
            rationale_parts.append(f"Profit factor below 1.0 ({prelim_cand_pf:.2f}).")
        if positive_w < 5:
            rationale_parts.append(f"Inconsistent across OOS windows ({positive_w}/8 positive windows).")
        if prelim_reduc > 75.0:
            rationale_parts.append(f"Excessive trade reduction ({prelim_reduc:.1f}%).")
        if not rationale_parts:
            rationale_parts.append("Positive OOS expectancy and defensible profit factor across majority of windows.")
            
        decision_rationale = " | ".join(rationale_parts)

        result_obj = CandidateTimingResult(
            candidate_id=c_id,
            title=c_title,
            hypothesis_type=c_type,
            rule_description=c_desc,
            same_candle_policy="stop_first",
            dev_trade_count=dev_n,
            dev_net_r=dev_net_r,
            dev_win_rate=dev_wr,
            dev_profit_factor=dev_pf,
            dev_expectancy=dev_exp,
            dev_trade_reduction_pct=dev_reduc,
            preliminary_oos_trade_count=n_prelim_cand,
            preliminary_oos_net_r=prelim_cand_net_r,
            preliminary_oos_delta_r=prelim_delta_r,
            preliminary_oos_win_rate=prelim_cand_wr,
            preliminary_oos_profit_factor=prelim_cand_pf,
            preliminary_oos_expectancy=prelim_cand_exp,
            preliminary_oos_trade_reduction_pct=prelim_reduc,
            positive_windows=positive_w,
            negative_windows=negative_w,
            mean_window_expectancy=round(float(np.mean(window_exp_list)), 3),
            median_window_expectancy=round(float(np.median(window_exp_list)), 3),
            worst_window_expectancy=round(float(min(window_exp_list)), 3),
            best_window_expectancy=round(float(max(window_exp_list)), 3),
            windows=window_metrics_list,
            conversion_metrics=c_conv,
            price_quality_metrics=price_quality,
            status=status,
            decision=decision,
            decision_rationale=decision_rationale,
            final_oos_locked=True,
            final_oos_evaluated=False,
            final_oos_date_range="2026-08-27 to 2026-09-25",
            provenance=get_provenance_list(),
        )

        # Save result JSON
        out_file = exp_dir / f"{c_id}_result.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result_obj.model_dump(), f, indent=2)

        logger.info(
            "Saved %s -> Status: %s | Dev Exp: %.3fR | Prelim OOS Exp: %.3fR (PF %.2f) | Reduc: %.1f%% | +Win: %d/8",
            c_id, status, dev_exp, prelim_cand_exp, prelim_cand_pf, prelim_reduc, positive_w
        )
        candidate_results.append(result_obj)

    logger.info("=== Phase 6F Research Execution Complete ===")


if __name__ == "__main__":
    main()
