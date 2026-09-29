"""
Phase 6D: Signal Engine V2 Hypothesis Testing across Dev and Preliminary OOS (Windows #1 to #8)
"""
import bisect
import gzip
import json
import math
import sys
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

sys.path.insert(0, "/home/bhoot/Desktop/tread/backend")

from app.backtest_models import BacktestConfig, BacktestTrade
from app.backtester import BacktestReplayEngine
from app.signal_models import MarketSignal
from app.validation.walk_forward import generate_walk_forward_slices

print("Loading historical data...")
with gzip.open("/home/bhoot/Desktop/tread/backend/data/XAUUSD_1m.json.gz", "rt") as f:
    candles_1m = json.load(f)
with gzip.open("/home/bhoot/Desktop/tread/backend/data/XAUUSD_5m.json.gz", "rt") as f:
    candles_5m = json.load(f)
with gzip.open("/home/bhoot/Desktop/tread/backend/data/signals_e9db340c4efa9e63_7.json.gz", "rt") as f:
    raw_signals = json.load(f)

candles_1m = sorted(candles_1m, key=lambda x: int(x["time"]))
candles_5m = sorted(candles_5m, key=lambda x: int(x["time"]))

c1_times = [int(c["time"]) for c in candles_1m]
c5_times = [int(c["time"]) for c in candles_5m]

# Baseline signal dict
precomputed_baseline = {}
for k, v in raw_signals.items():
    sig_dict, atr_val = v[0], v[1]
    sig_obj = MarketSignal(**sig_dict)
    precomputed_baseline[int(k)] = (sig_obj, float(atr_val))

# Load baseline validation result to get canonical windows
with open("/home/bhoot/Desktop/tread/backend/data/validation_phase5b_result.json") as f:
    val_res = json.load(f)

dev_start_iso = "2025-10-01T15:15:00+00:00"
dev_end_iso = "2025-12-30T15:15:00+00:00"

dev_start_ts = int(datetime.fromisoformat(dev_start_iso).timestamp())
dev_end_ts = int(datetime.fromisoformat(dev_end_iso).timestamp())

oos_windows = val_res["walk_forward"]
# Windows #1 to #8 are preliminary OOS. Window #9 is LOCKED FINAL OOS.

# Baseline execution config
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

# Helper function to run custom signal filter / V2 engine
def evaluate_hypothesis(
    hypo_id: str,
    hypo_name: str,
    signal_filter_fn: Callable[[int, MarketSignal, float, Dict[str, Any]], bool]
):
    print(f"\n=======================================================")
    print(f"Evaluating {hypo_id}: {hypo_name}")
    print(f"=======================================================")
    
    # Filter precomputed signals
    filtered_signals = {}
    for idx, (sig_obj, atr_val) in precomputed_baseline.items():
        sig_candle = candles_1m[idx]
        if signal_filter_fn(idx, sig_obj, atr_val, sig_candle):
            filtered_signals[idx] = (sig_obj, atr_val)

    # Run backtest
    engine = BacktestReplayEngine(cfg)
    res = engine.run_backtest(candles_1m, candles_5m, precomputed_signals=filtered_signals)
    all_trades = res.trades

    # Partition trades into Dev and Prelim OOS Windows #1 to #8
    dev_trades = [t for t in all_trades if dev_start_ts <= t.entry_time <= dev_end_ts]
    
    # Dev metrics
    dev_n = len(dev_trades)
    dev_net_r = sum(t.r_multiple for t in dev_trades)
    dev_wr = (sum(1 for t in dev_trades if t.r_multiple > 0) / dev_n * 100) if dev_n > 0 else 0.0
    dev_gp = sum(t.r_multiple for t in dev_trades if t.r_multiple > 0)
    dev_gl = sum(abs(t.r_multiple) for t in dev_trades if t.r_multiple < 0)
    dev_pf = (dev_gp / dev_gl) if dev_gl > 0 else 0.0
    dev_exp = (dev_net_r / dev_n) if dev_n > 0 else 0.0

    print(f"Dev (90d): Trades={dev_n} (Base=5995, Red={((5995-dev_n)/5995*100):.1f}%), Net R={dev_net_r:.2f}R (Base=-822.61R), WR={dev_wr:.2f}%, PF={dev_pf:.2f}, Exp={dev_exp:.3f}R")

    # Preliminary OOS Windows #1 to #8
    prelim_window_results = []
    prelim_trades_all = []

    for w_idx in range(8):  # 0 to 7 -> Windows 1 to 8
        w = oos_windows[w_idx]
        w_start = int(datetime.fromisoformat(w["validation_start_iso"]).timestamp())
        w_end = int(datetime.fromisoformat(w["validation_end_iso"]).timestamp())
        w_base_tr = w["validation_metrics"]["trades_count"]
        w_base_net_r = w["validation_metrics"]["total_r"]

        w_trades = [t for t in all_trades if w_start <= t.entry_time <= w_end]
        prelim_trades_all.extend(w_trades)

        w_n = len(w_trades)
        w_net_r = sum(t.r_multiple for t in w_trades)
        w_wr = (sum(1 for t in w_trades if t.r_multiple > 0) / w_n * 100) if w_n > 0 else 0.0
        w_gp = sum(t.r_multiple for t in w_trades if t.r_multiple > 0)
        w_gl = sum(abs(t.r_multiple) for t in w_trades if t.r_multiple < 0)
        w_pf = (w_gp / w_gl) if w_gl > 0 else 0.0
        w_exp = (w_net_r / w_n) if w_n > 0 else 0.0
        w_red = ((w_base_tr - w_n) / w_base_tr * 100) if w_base_tr > 0 else 0.0

        prelim_window_results.append({
            "window_index": w_idx + 1,
            "trades": w_n,
            "base_trades": w_base_tr,
            "trade_reduction_pct": round(w_red, 1),
            "net_r": round(w_net_r, 2),
            "base_net_r": round(w_base_net_r, 2),
            "delta_r": round(w_net_r - w_base_net_r, 2),
            "win_rate": round(w_wr, 2),
            "profit_factor": round(w_pf, 2),
            "expectancy": round(w_exp, 3)
        })

    # Prelim OOS Aggregate
    p_n = len(prelim_trades_all)
    p_net_r = sum(t.r_multiple for t in prelim_trades_all)
    p_wr = (sum(1 for t in prelim_trades_all if t.r_multiple > 0) / p_n * 100) if p_n > 0 else 0.0
    p_gp = sum(t.r_multiple for t in prelim_trades_all if t.r_multiple > 0)
    p_gl = sum(abs(t.r_multiple) for t in prelim_trades_all if t.r_multiple < 0)
    p_pf = (p_gp / p_gl) if p_gl > 0 else 0.0
    p_exp = (p_net_r / p_n) if p_n > 0 else 0.0
    p_red = ((15236 - p_n) / 15236 * 100)
    p_delta_r = p_net_r - (-1276.15)

    pos_windows = sum(1 for pw in prelim_window_results if pw["net_r"] > 0)
    neg_windows = 8 - pos_windows

    print(f"Prelim OOS (W#1–#8): Trades={p_n} (Base=15236, Red={p_red:.1f}%), Net R={p_net_r:.2f}R (Base=-1276.15R, dR={p_delta_r:+.2f}R), WR={p_wr:.2f}%, PF={p_pf:.2f}, Exp={p_exp:.3f}R")
    print(f"Window Distribution: {pos_windows} Positive / {neg_windows} Negative | Best W: {max(pw['net_r'] for pw in prelim_window_results):.2f}R | Worst W: {min(pw['net_r'] for pw in prelim_window_results):.2f}R")

    # Final OOS check - verify that NO trades from Window #9 were evaluated for decision
    w9_start = int(datetime.fromisoformat(oos_windows[8]["validation_start_iso"]).timestamp())
    w9_end = int(datetime.fromisoformat(oos_windows[8]["validation_end_iso"]).timestamp())
    print(f"Final OOS Window #9 ({oos_windows[8]['validation_start_iso'][:10]} to {oos_windows[8]['validation_end_iso'][:10]}): LOCKED & EXCLUDED FROM DECISION.")

    decision = "REJECTED"
    rationale = []
    if p_exp <= 0:
        decision = "REJECTED"
        rationale.append(f"Negative out-of-sample expectancy ({p_exp:.3f}R).")
    if p_pf <= 1.0:
        decision = "REJECTED"
        rationale.append(f"Profit factor below 1.0 ({p_pf:.2f}).")
    if p_red >= 90.0:
        rationale.append(f"Excessive trade reduction ({p_red:.1f}%).")
    if pos_windows == 0:
        rationale.append("0 / 8 profitable OOS windows.")

    print(f"Decision: {decision} ({' | '.join(rationale)})")

    return {
        "hypothesis_id": hypo_id,
        "title": hypo_name,
        "dev_trades": dev_n,
        "dev_net_r": round(dev_net_r, 2),
        "dev_wr": round(dev_wr, 2),
        "dev_pf": round(dev_pf, 2),
        "dev_exp": round(dev_exp, 3),
        "dev_trade_reduction_pct": round(((5995 - dev_n) / 5995 * 100), 1),
        "prelim_trades": p_n,
        "prelim_net_r": round(p_net_r, 2),
        "prelim_delta_r": round(p_delta_r, 2),
        "prelim_wr": round(p_wr, 2),
        "prelim_pf": round(p_pf, 2),
        "prelim_exp": round(p_exp, 3),
        "prelim_trade_reduction_pct": round(p_red, 1),
        "pos_windows": pos_windows,
        "neg_windows": neg_windows,
        "windows": prelim_window_results,
        "decision": decision,
        "decision_rationale": " | ".join(rationale),
        "final_oos_locked": True,
        "final_oos_evaluated": False
    }

# ----------------------------------------------------------------------
# Define Hypotheses
# ----------------------------------------------------------------------
results = []

# V2-H001: Pullback Confirmation Engine (Require price <= 0.6 ATR of 1m EMA21)
def filter_v2_h001(idx, sig, atr, candle):
    ind = sig.indicators
    c_close = float(candle["close"])
    ema21_1m = ind.ema21_1m or c_close
    direction = "LONG" if sig.type == "LONG_SETUP" else "SHORT"
    dist = (c_close - ema21_1m) if direction == "LONG" else (ema21_1m - c_close)
    return (dist / max(0.1, atr)) <= 0.60

results.append(evaluate_hypothesis("V2-H001", "Pullback Confirmation Engine (Dist 1m EMA21 <= 0.6 ATR)", filter_v2_h001))

# V2-H002: Opposing S/R Clearance Filter (Clearance >= 1.0 ATR)
def filter_v2_h002(idx, sig, atr, candle):
    c_close = float(candle["close"])
    direction = "LONG" if sig.type == "LONG_SETUP" else "SHORT"
    if direction == "LONG":
        clr = (sig.resistanceLevels[0].price - c_close) if sig.resistanceLevels else 999.0
    else:
        clr = (c_close - sig.supportLevels[0].price) if sig.supportLevels else 999.0
    return (clr / max(0.1, atr)) >= 1.0

results.append(evaluate_hypothesis("V2-H002", "Structural S/R Clearance (Opposing S/R >= 1.0 ATR)", filter_v2_h002))

# V2-H003: Directional Candle Body & Rejection Quality (Body Ratio >= 50% and aligned close)
def filter_v2_h003(idx, sig, atr, candle):
    c_close = float(candle["close"])
    c_open = float(candle["open"])
    c_high = float(candle["high"])
    c_low = float(candle["low"])
    direction = "LONG" if sig.type == "LONG_SETUP" else "SHORT"
    is_aligned = (c_close > c_open) if direction == "LONG" else (c_close < c_open)
    body = abs(c_close - c_open)
    rng = max(0.01, c_high - c_low)
    return is_aligned and (body / rng) >= 0.50

results.append(evaluate_hypothesis("V2-H003", "Directional Candle Confirmation (Body Ratio >= 50% & Aligned Close)", filter_v2_h003))

# V2-H004: Multi-Bar Signal Persistence (Signal strength >= 7 in previous bar as well)
def filter_v2_h004(idx, sig, atr, candle):
    prev_sig_data = precomputed_baseline.get(idx - 1)
    if not prev_sig_data:
        return False
    prev_sig, _ = prev_sig_data
    return prev_sig.type == sig.type and prev_sig.strength >= 7

results.append(evaluate_hypothesis("V2-H004", "Multi-Bar Signal Persistence (>= 2 Consecutive Setup Bars)", filter_v2_h004))

# V2-H005: Macro Trend & Volatility Expansion (1m ATR >= $1.50 and Strict 5m Trend)
def filter_v2_h005(idx, sig, atr, candle):
    return atr >= 1.50 and sig.trend_5m in ["BULLISH", "BEARISH"]

results.append(evaluate_hypothesis("V2-H005", "Macro Trend & Volatility Expansion (1m ATR >= $1.50)", filter_v2_h005))

# V2-H006: Composite Signal Engine V2 (Orthogonal Scoring: Pullback + S/R Clearance + Body + Trend + ATR)
def filter_v2_h006(idx, sig, atr, candle):
    c_close = float(candle["close"])
    c_open = float(candle["open"])
    c_high = float(candle["high"])
    c_low = float(candle["low"])
    direction = "LONG" if sig.type == "LONG_SETUP" else "SHORT"
    
    # 1. Pullback check
    ind = sig.indicators
    ema21_1m = ind.ema21_1m or c_close
    dist_ema21 = (c_close - ema21_1m) if direction == "LONG" else (ema21_1m - c_close)
    if (dist_ema21 / max(0.1, atr)) > 0.75:
        return False
        
    # 2. S/R clearance check
    if direction == "LONG":
        clr = (sig.resistanceLevels[0].price - c_close) if sig.resistanceLevels else 999.0
    else:
        clr = (c_close - sig.supportLevels[0].price) if sig.supportLevels else 999.0
    if (clr / max(0.1, atr)) < 0.75:
        return False

    # 3. Candle alignment
    is_aligned = (c_close > c_open) if direction == "LONG" else (c_close < c_open)
    if not is_aligned:
        return False

    # 4. ATR health
    if atr < 1.00:
        return False

    return True

results.append(evaluate_hypothesis("V2-H006", "Composite Signal Engine V2 (Pullback + Clearance + Body + Volatility)", filter_v2_h006))

# Save all results to backend/data/experiments/
for r in results:
    exp_file = f"/home/bhoot/Desktop/tread/backend/data/experiments/{r['hypothesis_id']}_result.json"
    with open(exp_file, "w") as f:
        json.dump(r, f, indent=2)
    print(f"Saved {exp_file}")

print("\nAll V2 hypotheses evaluated successfully.")
