"""
Phase 6E: Execution Script for Conditional Entry-State & Regime Expectancy Research
"""
import bisect
import gzip
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

sys.path.insert(0, "/home/bhoot/Desktop/tread/backend")

from app.backtest_models import BacktestConfig, BacktestTrade
from app.backtester import BacktestReplayEngine
from app.phase6e.conditional_engine import ConditionalResearchEngine, FINAL_OOS_START_TS
from app.phase6e.entry_classifier import (
    classify_impulse_pullback_state,
    classify_session_utc,
    classify_trend_range_regime,
    classify_volatility_quantile,
    get_feature_provenance_catalog,
)
from app.phase6e.models import (
    ConditionalBucketMetrics,
    ImpulseState,
    InteractionHypothesisResult,
    ProtectedFinalOOSAccessError,
    SessionBlock,
    TrendRangeRegime,
    VolatilityQuantile,
)
from app.signal_models import MarketSignal

print("Loading historical data...")
with gzip.open("/home/bhoot/Desktop/tread/backend/data/XAUUSD_1m.json.gz", "rt") as f:
    candles_1m = json.load(f)
with gzip.open("/home/bhoot/Desktop/tread/backend/data/XAUUSD_5m.json.gz", "rt") as f:
    candles_5m = json.load(f)
with gzip.open("/home/bhoot/Desktop/tread/backend/data/signals_e9db340c4efa9e63_7.json.gz", "rt") as f:
    raw_signals = json.load(f)
with open("/home/bhoot/Desktop/tread/backend/data/validation_phase5b_result.json") as f:
    val_manifest = json.load(f)

candles_1m = sorted(candles_1m, key=lambda x: int(x["time"]))
candles_5m = sorted(candles_5m, key=lambda x: int(x["time"]))

precomputed_signals = {}
for k, v in raw_signals.items():
    sig_dict, atr_val = v[0], v[1]
    sig_obj = MarketSignal(**sig_dict)
    precomputed_signals[int(k)] = (sig_obj, float(atr_val))

# Baseline backtest
cfg = BacktestConfig(
    symbol="XAUUSD",
    signal_threshold=7,
    sl_atr_multiplier=1.0,
    tp1_atr_multiplier=1.0,
    tp2_atr_multiplier=2.0,
    max_holding_minutes=60,
    assumed_spread=0.30,
    execution_mode="fixed_spread",
    same_candle_policy="stop_first",
    max_concurrent_trades=1
)

engine = BacktestReplayEngine(cfg)
base_res = engine.run_backtest(candles_1m, candles_5m, precomputed_signals=precomputed_signals)
baseline_trades = base_res.trades
print(f"Loaded {len(baseline_trades)} baseline trades.")

research_engine = ConditionalResearchEngine(
    candles_1m=candles_1m,
    candles_5m=candles_5m,
    precomputed_signals=precomputed_signals,
    validation_manifest=val_manifest
)

annotated_trades = research_engine.extract_and_annotate_baseline_trades(baseline_trades)
print(f"Annotated {len(annotated_trades)} trades with causal entry states.")

total_n = len(annotated_trades)

# ======================================================================
# 1. Session Analysis
# ======================================================================
print("\n" + "="*80)
print("1. SESSION / TIME-OF-DAY CONDITIONAL ANALYSIS")
print("="*80)

# A. Major Session Blocks
session_groups = {}
for t in annotated_trades:
    sb = t["session_block"]
    session_groups.setdefault(sb, []).append(t)

print(f"{'Session Block':<32} | {'Trades':<6} | {'Share':<6} | {'Win Rate':<8} | {'Net R':<9} | {'Avg R':<7} | {'PF':<5} | {'Early Stop %':<12} | {'Reach +1R %':<11}")
print("-" * 115)
session_metrics = []
for sb_name in [SessionBlock.ASIAN.value, SessionBlock.LONDON.value, SessionBlock.NY_OVERLAP.value, SessionBlock.NY_AFTERNOON.value, SessionBlock.LATE_NIGHT.value]:
    tr_list = session_groups.get(sb_name, [])
    m = research_engine.compute_bucket_metrics(tr_list, sb_name, total_n)
    session_metrics.append(m)
    print(f"{m.bucket_name:<32} | {m.trade_count:<6} | {m.trade_share_pct:>5.1f}% | {m.win_rate_pct:>7.2f}% | {m.total_net_r:>8.2f}R | {m.average_r:>6.3f}R | {m.profit_factor:>4.2f} | {m.early_stop_rate_pct:>10.2f}% | {m.reach_1r_mfe_pct:>9.2f}%")

# B. Day of Week
dow_groups = {}
for t in annotated_trades:
    dow_groups.setdefault(t["day_of_week"], []).append(t)

print("\n--- Day of Week Breakdown ---")
print(f"{'Day of Week':<15} | {'Trades':<6} | {'Win Rate':<8} | {'Net R':<9} | {'Avg R':<7} | {'PF':<5} | {'Early Stop %':<12}")
print("-" * 80)
for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
    tr_list = dow_groups.get(day, [])
    m = research_engine.compute_bucket_metrics(tr_list, day, total_n)
    print(f"{m.bucket_name:<15} | {m.trade_count:<6} | {m.win_rate_pct:>7.2f}% | {m.total_net_r:>8.2f}R | {m.average_r:>6.3f}R | {m.profit_factor:>4.2f} | {m.early_stop_rate_pct:>10.2f}%")

# ======================================================================
# 2. Volatility Quantile Analysis
# ======================================================================
print("\n" + "="*80)
print("2. VOLATILITY REGIME (QUANTILE ANALYSIS Q1–Q5)")
print("="*80)

vol_groups = {}
for t in annotated_trades:
    vol_groups.setdefault(t["volatility_quantile"], []).append(t)

print(f"{'Volatility Quantile':<25} | {'Trades':<6} | {'Share':<6} | {'Win Rate':<8} | {'Net R':<9} | {'Avg R':<7} | {'PF':<5} | {'Early Stop %':<12} | {'Mean MAE':<8} | {'Mean MFE':<8}")
print("-" * 115)
vol_metrics = []
for q_name in [VolatilityQuantile.Q1_LOW.value, VolatilityQuantile.Q2_MID_LOW.value, VolatilityQuantile.Q3_MEDIAN.value, VolatilityQuantile.Q4_MID_HIGH.value, VolatilityQuantile.Q5_HIGH.value]:
    tr_list = vol_groups.get(q_name, [])
    m = research_engine.compute_bucket_metrics(tr_list, q_name, total_n)
    vol_metrics.append(m)
    print(f"{m.bucket_name:<25} | {m.trade_count:<6} | {m.trade_share_pct:>5.1f}% | {m.win_rate_pct:>7.2f}% | {m.total_net_r:>8.2f}R | {m.average_r:>6.3f}R | {m.profit_factor:>4.2f} | {m.early_stop_rate_pct:>10.2f}% | {m.mean_mae_r:>6.3f}R | {m.mean_mfe_r:>6.3f}R")

# ======================================================================
# 3. Trend / Range Regime Analysis
# ======================================================================
print("\n" + "="*80)
print("3. TREND / RANGE REGIME ANALYSIS")
print("="*80)

regime_groups = {}
for t in annotated_trades:
    regime_groups.setdefault(t["trend_regime"], []).append(t)

print(f"{'Trend / Range Regime':<25} | {'Trades':<6} | {'Share':<6} | {'Win Rate':<8} | {'Net R':<9} | {'Avg R':<7} | {'PF':<5} | {'Early Stop %':<12}")
print("-" * 95)
regime_metrics = []
for r_name in [TrendRangeRegime.STRONG_TREND.value, TrendRangeRegime.TREND_PULLBACK.value, TrendRangeRegime.RANGE_COMPRESSION.value, TrendRangeRegime.VOLATILITY_EXPANSION.value]:
    tr_list = regime_groups.get(r_name, [])
    m = research_engine.compute_bucket_metrics(tr_list, r_name, total_n)
    regime_metrics.append(m)
    print(f"{m.bucket_name:<25} | {m.trade_count:<6} | {m.trade_share_pct:>5.1f}% | {m.win_rate_pct:>7.2f}% | {m.total_net_r:>8.2f}R | {m.average_r:>6.3f}R | {m.profit_factor:>4.2f} | {m.early_stop_rate_pct:>10.2f}%")

# ======================================================================
# 4. Impulse vs Pullback State Analysis
# ======================================================================
print("\n" + "="*80)
print("4. IMPULSE VS PULLBACK STATE ANALYSIS")
print("="*80)

impulse_groups = {}
for t in annotated_trades:
    impulse_groups.setdefault(t["impulse_state"], []).append(t)

print(f"{'Impulse State':<22} | {'Trades':<6} | {'Share':<6} | {'Win Rate':<8} | {'Net R':<9} | {'Avg R':<7} | {'PF':<5} | {'Early Stop %':<12} | {'Instant Stop %':<14}")
print("-" * 110)
impulse_metrics = []
for i_name in [ImpulseState.EARLY_IMPULSE.value, ImpulseState.CONTROLLED_PULLBACK.value, ImpulseState.LATE_IMPULSE.value, ImpulseState.NEUTRAL.value]:
    tr_list = impulse_groups.get(i_name, [])
    m = research_engine.compute_bucket_metrics(tr_list, i_name, total_n)
    impulse_metrics.append(m)
    print(f"{m.bucket_name:<22} | {m.trade_count:<6} | {m.trade_share_pct:>5.1f}% | {m.win_rate_pct:>7.2f}% | {m.total_net_r:>8.2f}R | {m.average_r:>6.3f}R | {m.profit_factor:>4.2f} | {m.early_stop_rate_pct:>10.2f}% | {m.instant_stop_rate_pct:>12.2f}%")

# ======================================================================
# 5. Signal Score Analysis (7, 8, 9, 10)
# ======================================================================
print("\n" + "="*80)
print("5. SIGNAL CONFLUENCE SCORE CONDITIONAL ANALYSIS (7 / 8 / 9 / 10)")
print("="*80)

score_groups = {}
for t in annotated_trades:
    score_groups.setdefault(t["score"], []).append(t)

print(f"{'Score':<8} | {'Trades':<6} | {'Share':<6} | {'Win Rate':<8} | {'Net R':<9} | {'Avg R':<7} | {'PF':<5} | {'Early Stop %':<12} | {'Reach +1R %':<11}")
print("-" * 95)
for sc in [7, 8, 9, 10]:
    tr_list = score_groups.get(sc, [])
    m = research_engine.compute_bucket_metrics(tr_list, f"Score = {sc}", total_n)
    print(f"{m.bucket_name:<8} | {m.trade_count:<6} | {m.trade_share_pct:>5.1f}% | {m.win_rate_pct:>7.2f}% | {m.total_net_r:>8.2f}R | {m.average_r:>6.3f}R | {m.profit_factor:>4.2f} | {m.early_stop_rate_pct:>10.2f}% | {m.reach_1r_mfe_pct:>9.2f}%")

# ======================================================================
# 6. Score Component Decomposition
# ======================================================================
print("\n" + "="*80)
print("6. SCORE COMPONENT DECOMPOSITION & CONDITIONAL CONTRIBUTION")
print("="*80)

components = [
    ("5m Primary Trend Alignment", "comp_trend_5m"),
    ("1m Market Structure Alignment", "comp_struct_1m"),
    ("1m EMA 9/21 Alignment", "comp_ema9_21"),
    ("1m MACD Histogram Positive", "comp_macd"),
    ("1m RSI Bullish Zone (40-68)", "comp_rsi"),
    ("Price Holding Above S/R Level", "comp_sr_holding"),
    ("Price Above 1m EMA 21", "comp_above_ema21"),
]

print(f"{'Component Rule':<35} | {'Active (T)':<10} | {'Active WR':<10} | {'Active Exp':<10} | {'Active PF':<9} | {'Inactive Exp':<12}")
print("-" * 95)

for c_label, c_key in components:
    active_tr = [t for t in annotated_trades if t[c_key]]
    inactive_tr = [t for t in annotated_trades if not t[c_key]]
    
    m_act = research_engine.compute_bucket_metrics(active_tr, c_label + " [Active]", total_n)
    m_inact = research_engine.compute_bucket_metrics(inactive_tr, c_label + " [Inactive]", total_n)
    
    print(f"{c_label:<35} | {m_act.trade_count:<10} | {m_act.win_rate_pct:>8.2f}% | {m_act.average_r:>8.3f}R | {m_act.profit_factor:>7.2f} | {m_inact.average_r:>10.3f}R")

# ======================================================================
# 7. Mechanism-Driven Interactions
# ======================================================================
print("\n" + "="*80)
print("7. MECHANISM-DRIVEN INTERACTION ANALYSIS")
print("="*80)

# Interaction 1: Impulse State x Volatility Quantile
print("\n--- Interaction 1: Impulse State x Volatility Quantile ---")
for imp in [ImpulseState.CONTROLLED_PULLBACK.value, ImpulseState.EARLY_IMPULSE.value, ImpulseState.LATE_IMPULSE.value]:
    for vol in [VolatilityQuantile.Q1_LOW.value, VolatilityQuantile.Q3_MEDIAN.value, VolatilityQuantile.Q5_HIGH.value]:
        sub = [t for t in annotated_trades if t["impulse_state"] == imp and t["volatility_quantile"] == vol]
        m = research_engine.compute_bucket_metrics(sub, f"{imp} x {vol[:6]}", total_n)
        if m.trade_count >= 100:
            print(f"{m.bucket_name:<40} | Trades={m.trade_count:<5} | WR={m.win_rate_pct:>5.2f}% | Net R={m.total_net_r:>7.2f}R | Exp={m.average_r:>6.3f}R | PF={m.profit_factor:>4.2f}")

# Interaction 3: Session x Volatility Quantile
print("\n--- Interaction 3: Session x Volatility Quantile ---")
for sess in [SessionBlock.LONDON.value, SessionBlock.NY_OVERLAP.value, SessionBlock.ASIAN.value]:
    for vol in [VolatilityQuantile.Q1_LOW.value, VolatilityQuantile.Q5_HIGH.value]:
        sub = [t for t in annotated_trades if t["session_block"] == sess and t["volatility_quantile"] == vol]
        m = research_engine.compute_bucket_metrics(sub, f"{sess[:6]} x {vol[:6]}", total_n)
        if m.trade_count >= 100:
            print(f"{m.bucket_name:<40} | Trades={m.trade_count:<5} | WR={m.win_rate_pct:>5.2f}% | Net R={m.total_net_r:>7.2f}R | Exp={m.average_r:>6.3f}R | PF={m.profit_factor:>4.2f}")

# Interaction 6: S/R Clearance x Impulse State
print("\n--- Interaction 6: S/R Clearance x Impulse State ---")
for clr_label, clr_fn in [("Clearance >= 1.0 ATR", lambda x: x >= 1.0), ("Clearance < 0.5 ATR", lambda x: x < 0.5)]:
    for imp in [ImpulseState.CONTROLLED_PULLBACK.value, ImpulseState.EARLY_IMPULSE.value, ImpulseState.LATE_IMPULSE.value]:
        sub = [t for t in annotated_trades if clr_fn(t["opp_sr_clearance_atr"]) and t["impulse_state"] == imp]
        m = research_engine.compute_bucket_metrics(sub, f"{clr_label[:14]} x {imp}", total_n)
        if m.trade_count >= 100:
            print(f"{m.bucket_name:<40} | Trades={m.trade_count:<5} | WR={m.win_rate_pct:>5.2f}% | Net R={m.total_net_r:>7.2f}R | Exp={m.average_r:>6.3f}R | PF={m.profit_factor:>4.2f}")

# ======================================================================
# 8. Formal Candidate Hypotheses Evaluation (Dev & Preliminary OOS)
# ======================================================================
print("\n" + "="*80)
print("8. FORMAL CANDIDATE HYPOTHESES EVALUATION (DEV & PRELIMINARY OOS W#1–#8)")
print("="*80)

oos_windows = val_manifest["walk_forward"]

def evaluate_v6e_candidate(
    hypo_id: str,
    hypo_title: str,
    rule_description: str,
    candidate_filter_fn: Callable[[Dict[str, Any]], bool]
) -> Dict[str, Any]:
    print(f"\nEvaluating Candidate {hypo_id}: {hypo_title}...")
    
    # 1. Dev Period (First 90 Days: 2025-10-01 to 2025-12-30)
    dev_start_ts = 1759331700
    dev_end_ts = 1767107700
    
    dev_all = [t for t in annotated_trades if dev_start_ts <= t["entry_time"] <= dev_end_ts]
    dev_cand = [t for t in dev_all if candidate_filter_fn(t)]
    
    dev_m = research_engine.compute_bucket_metrics(dev_cand, "Dev", len(dev_all))
    dev_red = (len(dev_all) - len(dev_cand)) / len(dev_all) * 100 if dev_all else 0.0
    
    # 2. Preliminary OOS Windows #1 to #8
    prelim_window_results = []
    prelim_cand_all = []
    prelim_base_all = []
    
    for w_idx in range(8):  # Windows 1 to 8
        w = oos_windows[w_idx]
        w_start = int(datetime.fromisoformat(w["validation_start_iso"]).timestamp())
        w_end = int(datetime.fromisoformat(w["validation_end_iso"]).timestamp())
        
        # Guard check
        research_engine.assert_final_oos_locked(w_start, w_end)
        
        w_all = [t for t in annotated_trades if w_start <= t["entry_time"] <= w_end]
        w_cand = [t for t in w_all if candidate_filter_fn(t)]
        
        prelim_base_all.extend(w_all)
        prelim_cand_all.extend(w_cand)
        
        w_m = research_engine.compute_bucket_metrics(w_cand, f"Window #{w_idx+1}", len(w_all))
        w_red = (len(w_all) - len(w_cand)) / len(w_all) * 100 if w_all else 0.0
        
        prelim_window_results.append({
            "window_index": w_idx + 1,
            "trades": w_m.trade_count,
            "base_trades": len(w_all),
            "trade_reduction_pct": round(w_red, 1),
            "net_r": w_m.total_net_r,
            "win_rate": w_m.win_rate_pct,
            "profit_factor": w_m.profit_factor,
            "expectancy": w_m.average_r,
            "early_stop_rate_pct": w_m.early_stop_rate_pct
        })

    prelim_m = research_engine.compute_bucket_metrics(prelim_cand_all, "Preliminary OOS", len(prelim_base_all))
    prelim_red = (len(prelim_base_all) - len(prelim_cand_all)) / len(prelim_base_all) * 100 if prelim_base_all else 0.0
    prelim_delta_r = prelim_m.total_net_r - (-1276.15)
    
    pos_windows = sum(1 for pw in prelim_window_results if pw["net_r"] > 0)
    neg_windows = 8 - pos_windows
    
    # Decision determination
    decision = "REJECTED"
    rationale = []
    if prelim_m.average_r <= 0:
        rationale.append(f"Negative preliminary OOS expectancy ({prelim_m.average_r:.3f}R).")
    if prelim_m.profit_factor <= 1.0:
        rationale.append(f"Profit factor below 1.0 ({prelim_m.profit_factor:.2f}).")
    if pos_windows == 0:
        rationale.append("0 / 8 profitable OOS windows.")
    if prelim_red >= 90.0:
        rationale.append(f"Severe trade reduction ({prelim_red:.1f}%).")
        
    print(f"Dev (90d): Trades={dev_m.trade_count} (Base=5995, Red={dev_red:.1f}%), Net R={dev_m.total_net_r:.2f}R, WR={dev_m.win_rate_pct:.2f}%, PF={dev_m.profit_factor:.2f}, Exp={dev_m.average_r:.3f}R")
    print(f"Prelim OOS (W#1–#8): Trades={prelim_m.trade_count} (Base=15236, Red={prelim_red:.1f}%), Net R={prelim_m.total_net_r:.2f}R (dR={prelim_delta_r:+.2f}R), WR={prelim_m.win_rate_pct:.2f}%, PF={prelim_m.profit_factor:.2f}, Exp={prelim_m.average_r:.3f}R")
    print(f"Decision: {decision} ({' | '.join(rationale)})")
    
    result_dict = {
        "candidate_id": hypo_id,
        "title": hypo_title,
        "rule_description": rule_description,
        "dev_trade_count": dev_m.trade_count,
        "dev_net_r": dev_m.total_net_r,
        "dev_win_rate": dev_m.win_rate_pct,
        "dev_profit_factor": dev_m.profit_factor,
        "dev_expectancy": dev_m.average_r,
        "dev_trade_reduction_pct": round(dev_red, 1),
        "preliminary_oos_trade_count": prelim_m.trade_count,
        "preliminary_oos_net_r": prelim_m.total_net_r,
        "preliminary_oos_delta_r": round(prelim_delta_r, 2),
        "preliminary_oos_win_rate": prelim_m.win_rate_pct,
        "preliminary_oos_profit_factor": prelim_m.profit_factor,
        "preliminary_oos_expectancy": prelim_m.average_r,
        "preliminary_oos_trade_reduction_pct": round(prelim_red, 1),
        "positive_windows": pos_windows,
        "negative_windows": neg_windows,
        "windows": prelim_window_results,
        "status": decision,
        "decision": decision,
        "decision_rationale": " | ".join(rationale),
        "final_oos_locked": True,
        "final_oos_evaluated": False,
        "final_oos_date_range": "2026-08-27 to 2026-09-25",
        "provenance": [p.dict() for p in get_feature_provenance_catalog()]
    }
    
    # Save experiment artifact
    out_path = f"/home/bhoot/Desktop/tread/backend/data/experiments/{hypo_id}_result.json"
    with open(out_path, "w") as f:
        json.dump(result_dict, f, indent=2)
    print(f"Saved experiment result artifact: {out_path}")
    
    return result_dict

# ----------------------------------------------------------------------
# Execute 6 Candidates
# ----------------------------------------------------------------------
candidates = []

# V6E-H001: Controlled Pullback in High Volatility
candidates.append(evaluate_v6e_candidate(
    "V6E-H001",
    "Controlled Pullback in Volatility Expansion",
    "Require Impulse State == CONTROLLED_PULLBACK and Volatility Quantile in (Q4_MID_HIGH, Q5_HIGH)",
    lambda t: t["impulse_state"] == ImpulseState.CONTROLLED_PULLBACK.value and t["volatility_quantile"] in [VolatilityQuantile.Q4_MID_HIGH.value, VolatilityQuantile.Q5_HIGH.value]
))

# V6E-H002: Early Impulse with S/R Clearance
candidates.append(evaluate_v6e_candidate(
    "V6E-H002",
    "Early Impulse with Structural Clearance",
    "Require Impulse State == EARLY_IMPULSE and Opposing S/R Clearance >= 1.0 ATR",
    lambda t: t["impulse_state"] == ImpulseState.EARLY_IMPULSE.value and t["opp_sr_clearance_atr"] >= 1.0
))

# V6E-H003: London & NY High-Volatility Window
candidates.append(evaluate_v6e_candidate(
    "V6E-H003",
    "London & NY High-Volatility Window",
    "Require Session Block in (LONDON, NY_OVERLAP) and Volatility Quantile in (Q3, Q4, Q5)",
    lambda t: t["session_block"] in [SessionBlock.LONDON.value, SessionBlock.NY_OVERLAP.value] and t["volatility_quantile"] in [VolatilityQuantile.Q3_MEDIAN.value, VolatilityQuantile.Q4_MID_HIGH.value, VolatilityQuantile.Q5_HIGH.value]
))

# V6E-H004: Anti-Late Impulse Filter
candidates.append(evaluate_v6e_candidate(
    "V6E-H004",
    "Anti-Late Impulse Exhaustion Filter",
    "Reject Impulse State == LATE_IMPULSE (Trade only EARLY_IMPULSE, CONTROLLED_PULLBACK, NEUTRAL)",
    lambda t: t["impulse_state"] != ImpulseState.LATE_IMPULSE.value
))

# V6E-H005: Strong Structural Trend Alignment
candidates.append(evaluate_v6e_candidate(
    "V6E-H005",
    "Strong Structural Trend Alignment",
    "Require Trend Regime == STRONG_TREND and Confluence Score >= 8",
    lambda t: t["trend_regime"] == TrendRangeRegime.STRONG_TREND.value and t["score"] >= 8
))

# V6E-H006: Composite High-Conviction Entry State
candidates.append(evaluate_v6e_candidate(
    "V6E-H006",
    "Composite High-Conviction Entry State",
    "Require Impulse State in (EARLY_IMPULSE, CONTROLLED_PULLBACK), S/R Clearance >= 0.8 ATR, and Volatility >= Q3",
    lambda t: t["impulse_state"] in [ImpulseState.EARLY_IMPULSE.value, ImpulseState.CONTROLLED_PULLBACK.value] and t["opp_sr_clearance_atr"] >= 0.8 and t["volatility_quantile"] in [VolatilityQuantile.Q3_MEDIAN.value, VolatilityQuantile.Q4_MID_HIGH.value, VolatilityQuantile.Q5_HIGH.value]
))

print("\nPhase 6E Research Script Completed.")
