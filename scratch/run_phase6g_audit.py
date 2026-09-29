"""
Phase 6G: Entry Execution Realism & Robustness Audit Script
Executes full independent reconstruction and audits across all Phase 6G dimensions.
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

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.historical_data_quality import compute_dataset_hash
from app.phase6f.entry_timing_engine import (
    ControlledRetracementPolicy,
    HybridRetraceOrConfirmPolicy,
    ImmediateEntryPolicy,
    TightExpirationPolicy,
    assert_final_oos_locked,
)
from app.phase6f.models import (
    FINAL_OOS_END_TS,
    FINAL_OOS_START_TS,
    ProtectedFinalOOSAccessError,
)
from app.phase6g.execution_audit_engine import (
    ExecutionRealismAuditEngine,
    NegativeControlDelayPolicy,
)
from app.phase6g.models import (
    AuditVerdict,
    CandidateReconstructionSummary,
)
from app.signal_models import MarketSignal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phase6g_audit_runner")


def load_candles_and_signals():
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


def main():
    candles_1m, candles_5m, precomputed_signals = load_candles_and_signals()
    engine = ExecutionRealismAuditEngine(candles_1m, candles_5m, precomputed_signals)

    # 1. Baseline Exact Reproduction
    logger.info("=== 1. BASELINE EXACT REPRODUCTION ===")
    base_res = engine.audit_baseline_reproduction()
    logger.info(
        "Baseline: %d trades, WR %.2f%%, Net R %.2fR, Exp %.3fR, PF %.2f | Exact Match: %s",
        base_res["trade_count"], base_res["win_rate_pct"], base_res["net_r"],
        base_res["expectancy_r"], base_res["profit_factor"], base_res["is_exact_match"]
    )
    if not base_res["is_exact_match"]:
        logger.error("FATAL: Baseline reproduction mismatch. Halting Phase 6G.")
        sys.exit(1)

    # 2. Candidate Reconstructions
    logger.info("=== 2. CANDIDATE RECONSTRUCTIONS ===")
    candidates_to_audit = [
        ("V6F-H001", "Controlled Retracement (0.25 ATR / 3m)", ControlledRetracementPolicy(retrace_atr=0.25, max_wait_bars=3)),
        ("V6F-H005", "Hybrid Retrace-or-Confirm State Machine (3m)", HybridRetraceOrConfirmPolicy(retrace_atr=0.20, breakout_atr=0.20, max_wait_bars=3)),
        ("V6F-H006", "Tight Expiration Window (0.15 ATR / 2m)", TightExpirationPolicy(retrace_atr=0.15, max_wait_bars=2)),
    ]

    exp_dir = backend_dir / "data" / "experiments"

    for c_id, c_title, policy in candidates_to_audit:
        trades, conv, _ = engine.timing_engine.run_timing_simulation(policy)
        
        # Dev metrics
        dev_start_ts, dev_end_ts, _, _ = engine.dev_slice
        dev_trades = [t for t in trades if dev_start_ts <= t.entry_time <= dev_end_ts]
        dev_n = len(dev_trades)
        dev_net = sum(t.r_multiple for t in dev_trades)
        dev_exp = dev_net / dev_n if dev_n > 0 else 0.0
        dev_wins = sum(1 for t in dev_trades if t.r_multiple > 0)
        dev_wr = dev_wins / dev_n * 100 if dev_n > 0 else 0.0
        dev_gp = sum(t.r_multiple for t in dev_trades if t.r_multiple > 0)
        dev_gl = sum(abs(t.r_multiple) for t in dev_trades if t.r_multiple < 0)
        dev_pf = dev_gp / dev_gl if dev_gl > 0 else 0.0

        # Prelim OOS metrics
        prelim_trades = []
        pos_w = 0
        for w_idx, (t_start, t_end, v_start, v_end) in enumerate(engine.preliminary_slices, start=1):
            assert_final_oos_locked(t_start, v_end)
            w_t = [t for t in trades if v_start <= t.entry_time <= v_end]
            prelim_trades.extend(w_t)
            if sum(t.r_multiple for t in w_t) > 0:
                pos_w += 1

        p_n = len(prelim_trades)
        p_net = sum(t.r_multiple for t in prelim_trades)
        p_exp = p_net / p_n if p_n > 0 else 0.0
        p_wins = sum(1 for t in prelim_trades if t.r_multiple > 0)
        p_wr = p_wins / p_n * 100 if p_n > 0 else 0.0
        p_gp = sum(t.r_multiple for t in prelim_trades if t.r_multiple > 0)
        p_gl = sum(abs(t.r_multiple) for t in prelim_trades if t.r_multiple < 0)
        p_pf = p_gp / p_gl if p_gl > 0 else 0.0
        p_reduc = (15248 - p_n) / 15248 * 100

        # Load stored JSON
        with open(exp_dir / f"{c_id}_result.json") as f:
            stored_data = json.load(f)

        stored_exp = stored_data["preliminary_oos_expectancy"]
        stored_net = stored_data["preliminary_oos_net_r"]
        is_exact = (abs(round(p_exp, 3) - stored_exp) < 0.001 and abs(round(p_net, 2) - stored_net) < 0.05)

        logger.info(
            "Reconstructed %s: Dev Exp %.3fR (PF %.2f) | Prelim OOS Exp %.3fR, Net %.2fR (PF %.2f), Trades %d (Reduc %.1f%%), +Win: %d/8 | Stored Match: %s",
            c_id, dev_exp, dev_pf, p_exp, p_net, p_pf, p_n, p_reduc, pos_w, is_exact
        )

    # 3. Same-Candle & Intrabar Audit for H006
    logger.info("=== 3. SAME-CANDLE & INTRABAR AUDIT (H006) ===")
    sc_audit = engine.audit_same_candle_and_intrabar(TightExpirationPolicy(retrace_atr=0.15, max_wait_bars=2))
    logger.info(
        "H006 Same-Candle: Total %d trades, %d entry-bar exits (%.2f%%) [SL: %d, TP1: %d, Conflicts: %d], Delta Net R: %.2fR",
        sc_audit.total_trades, sc_audit.entry_bar_exits_count, sc_audit.entry_bar_exits_pct,
        sc_audit.entry_bar_sl_count, sc_audit.entry_bar_tp1_count, sc_audit.entry_bar_conflict_count, sc_audit.delta_net_r
    )

    # 4. Concurrency Audit for H006
    logger.info("=== 4. CONCURRENCY AUDIT (H006) ===")
    conc_audit = engine.audit_concurrency(TightExpirationPolicy(retrace_atr=0.15, max_wait_bars=2))
    logger.info(
        "H006 Concurrency: %d total signals, %d executed trades, %d cancelled (pending wait / timeouts), Concurrency Violations: %d",
        conc_audit.total_signals, conc_audit.executed_trades, conc_audit.cancelled_by_concurrency, conc_audit.concurrency_violation_count
    )

    # 5. Holding-Time Convention Audit for H006
    logger.info("=== 5. HOLDING-TIME CONVENTION AUDIT (H006) ===")
    ht_entry, ht_sig = engine.audit_holding_time_convention(TightExpirationPolicy(retrace_atr=0.15, max_wait_bars=2))
    logger.info(
        "Holding Time Origin: Entry Time Origin -> Net %.2fR, Exp %.3fR, PF %.2f, Expired: %d | Signal Time Origin -> Net %.2fR, Exp %.3fR, PF %.2f, Expired: %d (Delta: %.2fR)",
        ht_entry.net_r, ht_entry.expectancy_r, ht_entry.profit_factor, ht_entry.expired_count,
        ht_sig.net_r, ht_sig.expectancy_r, ht_sig.profit_factor, ht_sig.expired_count, ht_sig.delta_r_vs_entry_time
    )

    # 6. Negative Control Test
    logger.info("=== 6. NEGATIVE CONTROL TEST ===")
    neg_control = engine.run_negative_control_test()
    logger.info(
        "Negative Control (%s): %d trades, WR %.2f%%, Net %.2fR, Exp %.3fR, PF %.2f, +Win: %d/8 | H006 Outperformance: +%.2fR",
        neg_control.control_name, neg_control.trade_count, neg_control.win_rate_pct, neg_control.net_r,
        neg_control.expectancy_r, neg_control.profit_factor, neg_control.positive_windows, neg_control.h006_outperformance_r
    )

    # 7. Timing Perturbation Grid around H006
    logger.info("=== 7. TIMING PERTURBATION GRID (H006) ===")
    pert_grid = engine.run_timing_perturbation_grid()
    for cell in pert_grid:
        logger.info(
            "Perturbation [Retrace %.2f ATR | Wait %dm]: Prelim Trades %d (Reduc %.1f%%), Exp %.3fR, PF %.2f, Net %.2fR, +Win: %d/8",
            cell.retrace_atr, cell.max_wait_minutes, cell.prelim_trades, cell.trade_reduction_pct,
            cell.prelim_expectancy_r, cell.prelim_pf, cell.prelim_net_r, cell.positive_windows
        )

    # 8. Price Degradation / Slippage Sensitivity
    logger.info("=== 8. PRICE DEGRADATION / SLIPPAGE SENSITIVITY ===")
    slip_sens = engine.run_price_degradation_sensitivity()
    for cell in slip_sens:
        logger.info(
            "Slippage Penalty [%.2f ATR ($%.2f)]: Prelim Exp %.3fR, PF %.2f, Net %.2fR (Delta %.2fR), +Win: %d/8",
            cell.adverse_slippage_atr, cell.adverse_slippage_dollars, cell.prelim_expectancy_r,
            cell.prelim_profit_factor, cell.prelim_net_r, cell.delta_net_r, cell.positive_windows
        )

    # 9. Spread Sensitivity
    logger.info("=== 9. SPREAD SENSITIVITY ===")
    spread_sens = engine.run_spread_sensitivity_grid()
    for cell in spread_sens:
        logger.info(
            "Spread Sensitivity [$%.2f]: Prelim Exp %.3fR, PF %.2f, Net %.2fR (Delta %.2fR), +Win: %d/8",
            cell.spread_dollars, cell.prelim_expectancy_r, cell.prelim_profit_factor,
            cell.prelim_net_r, cell.delta_net_r, cell.positive_windows
        )

    logger.info("=== Phase 6G Execution Realism & Robustness Audit Complete ===")


if __name__ == "__main__":
    main()
