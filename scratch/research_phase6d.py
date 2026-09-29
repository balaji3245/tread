"""
Phase 6D: Signal Engine V2 Research, Feature Redundancy, Regime Analysis & Hypothesis Validation
"""
import bisect
import gzip
import json
import math
import sys
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
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

print(f"Loaded {len(candles_1m)} 1m candles, {len(candles_5m)} 5m candles, {len(raw_signals)} baseline signals.")

# Reconstruct precomputed baseline signals
precomputed_baseline = {}
for k, v in raw_signals.items():
    sig_dict, atr_val = v[0], v[1]
    sig_obj = MarketSignal(**sig_dict)
    precomputed_baseline[int(k)] = (sig_obj, float(atr_val))

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
base_res = engine.run_backtest(candles_1m, candles_5m, precomputed_signals=precomputed_baseline)
trades = base_res.trades
print(f"Baseline trades: {len(trades)}, Net R: {base_res.statistics.total_r:.2f}R, WR: {base_res.statistics.win_rate:.2f}%, PF: {base_res.statistics.profit_factor:.2f}")

# ----------------------------------------------------------------------
# 1. Forensic Group Classification & Excursion Profiles
# ----------------------------------------------------------------------
group_a = []  # Clean Winners (Hit TP, MAE <= 0.5R)
group_b = []  # Early Stop Reversals (SL hit <= 3m, 60m MFE >= +1.0R)
group_c = []  # Directional Failures (Loss and 60m MFE < +1.0R)
group_other_win = []
group_other_loss = []

mae_1m_list = []
mae_2m_list = []
mae_3m_list = []
mfe_5m_list = []
mfe_10m_list = []
mfe_15m_list = []
mfe_30m_list = []
mfe_60m_list = []

trade_features = []

for idx, t in enumerate(trades):
    entry_time = t.entry_time
    e_idx = bisect.bisect_left(c1_times, entry_time)
    if e_idx >= len(candles_1m) or c1_times[e_idx] != entry_time:
        continue

    sig_idx = e_idx - 1
    if sig_idx < 30:
        continue

    sig_data = precomputed_baseline.get(sig_idx)
    if not sig_data:
        continue
    sig_obj, atr_val = sig_data

    direction = t.direction
    entry_price = t.entry_price
    sl_dist = max(0.50, atr_val * 1.0)

    forward_candles = candles_1m[e_idx: min(len(candles_1m), e_idx + 60)]
    
    cum_mae = 0.0
    cum_mfe = 0.0
    
    mae_1m = 0.0
    mae_2m = 0.0
    mae_3m = 0.0
    mfe_5m = 0.0
    mfe_10m = 0.0
    mfe_15m = 0.0
    mfe_30m = 0.0
    mfe_60m = 0.0

    for step, fc in enumerate(forward_candles):
        h = float(fc["high"])
        l = float(fc["low"])
        c = float(fc["close"])
        
        adv = max(0.0, entry_price - l) if direction == "LONG" else max(0.0, h - entry_price)
        fav = max(0.0, h - entry_price) if direction == "LONG" else max(0.0, entry_price - l)

        cum_mae = max(cum_mae, adv)
        cum_mfe = max(cum_mfe, fav)

        if step == 0: mae_1m = cum_mae / sl_dist
        if step == 1: mae_2m = cum_mae / sl_dist
        if step == 2: mae_3m = cum_mae / sl_dist
        if step == 4: mfe_5m = cum_mfe / sl_dist
        if step == 9: mfe_10m = cum_mfe / sl_dist
        if step == 14: mfe_15m = cum_mfe / sl_dist
        if step == 29: mfe_30m = cum_mfe / sl_dist
        if step == 59 or step == len(forward_candles) - 1: mfe_60m = cum_mfe / sl_dist

    mae_1m_list.append(mae_1m)
    mae_2m_list.append(mae_2m)
    mae_3m_list.append(mae_3m)
    mfe_5m_list.append(mfe_5m)
    mfe_10m_list.append(mfe_10m)
    mfe_15m_list.append(mfe_15m)
    mfe_30m_list.append(mfe_30m)
    mfe_60m_list.append(mfe_60m)

    full_mfe_r = cum_mfe / sl_dist
    full_mae_r = cum_mae / sl_dist

    ind = sig_obj.indicators
    sig_candle = candles_1m[sig_idx]
    c_close = float(sig_candle["close"])
    c_open = float(sig_candle["open"])
    c_high = float(sig_candle["high"])
    c_low = float(sig_candle["low"])
    
    c_body = abs(c_close - c_open)
    c_range = max(0.01, c_high - c_low)
    body_ratio = c_body / c_range
    is_candle_aligned = (c_close > c_open) if direction == "LONG" else (c_close < c_open)

    ema9_1m = ind.ema9_1m or c_close
    ema21_1m = ind.ema21_1m or c_close
    ema50_1m = ind.ema50_1m or c_close
    ema9_5m = ind.ema9_5m or c_close
    ema21_5m = ind.ema21_5m or c_close
    ema50_5m = ind.ema50_5m or c_close

    dist_ema9_1m = (c_close - ema9_1m) if direction == "LONG" else (ema9_1m - c_close)
    dist_ema21_1m = (c_close - ema21_1m) if direction == "LONG" else (ema21_1m - c_close)
    dist_ema50_1m = (c_close - ema50_1m) if direction == "LONG" else (ema50_1m - c_close)
    dist_ema50_5m = (c_close - ema50_5m) if direction == "LONG" else (ema50_5m - c_close)

    dist_ema50_5m_atr = dist_ema50_5m / max(0.1, atr_val)

    rsi_1m = ind.rsi_1m or 50.0
    rsi_5m = ind.rsi_5m or 50.0
    macd_hist_1m = ind.macdHist_1m or 0.0

    sups = sig_obj.supportLevels
    resis = sig_obj.resistanceLevels
    
    if direction == "LONG":
        opp_sr_dist = (resis[0].price - c_close) if resis else 999.0
    else:
        opp_sr_dist = (c_close - sups[0].price) if sups else 999.0
    opp_sr_clearance_atr = opp_sr_dist / max(0.1, atr_val)

    trend_5m = sig_obj.trend_5m
    struct_1m = sig_obj.structure_1m
    score = sig_obj.strength

    feat = {
        "trade_idx": idx,
        "entry_time": entry_time,
        "direction": direction,
        "result": t.result,
        "r_multiple": t.r_multiple,
        "holding_minutes": t.holding_minutes,
        "exit_reason": t.exit_reason,
        "atr_1m": atr_val,
        "score": score,
        "dist_ema9_1m_atr": dist_ema9_1m / atr_val,
        "dist_ema21_1m_atr": dist_ema21_1m / atr_val,
        "dist_ema50_1m_atr": dist_ema50_1m / atr_val,
        "dist_ema50_5m_atr": dist_ema50_5m_atr,
        "rsi_1m": rsi_1m,
        "rsi_5m": rsi_5m,
        "macd_hist_1m": macd_hist_1m,
        "opp_sr_clearance_atr": opp_sr_clearance_atr,
        "body_ratio": body_ratio,
        "is_candle_aligned": is_candle_aligned,
        "trend_5m": trend_5m,
        "struct_1m": struct_1m,
        "mae_1m": mae_1m,
        "mae_2m": mae_2m,
        "mae_3m": mae_3m,
        "mfe_5m": mfe_5m,
        "full_mfe_r": full_mfe_r,
        "full_mae_r": full_mae_r,
    }
    trade_features.append(feat)

    if t.r_multiple > 0 and full_mae_r <= 0.5:
        group_a.append(feat)
    elif t.r_multiple < 0 and t.holding_minutes <= 3 and full_mfe_r >= 1.0:
        group_b.append(feat)
    elif t.r_multiple < 0 and full_mfe_r < 1.0:
        group_c.append(feat)
    elif t.r_multiple > 0:
        group_other_win.append(feat)
    else:
        group_other_loss.append(feat)

print("\n" + "="*80)
print("1. TRADE GROUP DISTRIBUTION")
print("="*80)
print(f"Total Evaluated Trades: {len(trade_features)}")
print(f"Group A (Clean Immediate Winners, MAE <= 0.5R): {len(group_a)} ({len(group_a)/len(trade_features)*100:.2f}%)")
print(f"Group B (Early Stop-Out Reversals, Loss <= 3m, MFE >= +1.0R): {len(group_b)} ({len(group_b)/len(trade_features)*100:.2f}%)")
print(f"Group C (Directional Failures, Loss & MFE < +1.0R): {len(group_c)} ({len(group_c)/len(trade_features)*100:.2f}%)")
print(f"Other Winners (MAE > 0.5R): {len(group_other_win)} ({len(group_other_win)/len(trade_features)*100:.2f}%)")
print(f"Other Losses (> 3m or partial): {len(group_other_loss)} ({len(group_other_loss)/len(trade_features)*100:.2f}%)")

print("\n" + "="*80)
print("2. EXCURSION PROFILE & ADVERSE TRAJECTORY")
print("="*80)
print(f"Mean 1-min MAE: {np.mean(mae_1m_list):.3f}R | Median: {np.median(mae_1m_list):.3f}R")
print(f"Mean 2-min MAE: {np.mean(mae_2m_list):.3f}R | Median: {np.median(mae_2m_list):.3f}R")
print(f"Mean 3-min MAE: {np.mean(mae_3m_list):.3f}R | Median: {np.median(mae_3m_list):.3f}R")
print(f"Mean 5-min MFE: {np.mean(mfe_5m_list):.3f}R | Median: {np.median(mfe_5m_list):.3f}R")
print(f"Mean 15-min MFE: {np.mean(mfe_15m_list):.3f}R | Median: {np.median(mfe_15m_list):.3f}R")
print(f"Mean 60-min MFE: {np.mean(mfe_60m_list):.3f}R | Median: {np.median(mfe_60m_list):.3f}R")
print(f"Fraction with 1m MAE >= 0.50R: {np.mean(np.array(mae_1m_list) >= 0.5)*100:.2f}%")
print(f"Fraction with 1m MAE >= 1.00R (Instant SL): {np.mean(np.array(mae_1m_list) >= 1.0)*100:.2f}%")
print(f"Fraction with 3m MAE >= 1.00R: {np.mean(np.array(mae_3m_list) >= 1.0)*100:.2f}%")
total_losses = len(group_b) + len(group_c) + len(group_other_loss)
print(f"Total Losses: {total_losses}")
print(f"Fraction of ALL losses that were Early Stop Reversals (Group B): {len(group_b) / total_losses * 100:.2f}%")

# ----------------------------------------------------------------------
# 3. Feature Distribution Across Groups A, B, C
# ----------------------------------------------------------------------
features_to_compare = [
    ("Signal Confluence Score", "score"),
    ("Dist 1m EMA 9 (ATR)", "dist_ema9_1m_atr"),
    ("Dist 1m EMA 21 (ATR)", "dist_ema21_1m_atr"),
    ("Dist 1m EMA 50 (ATR)", "dist_ema50_1m_atr"),
    ("Dist 5m EMA 50 (ATR)", "dist_ema50_5m_atr"),
    ("1m RSI Level", "rsi_1m"),
    ("5m RSI Level", "rsi_5m"),
    ("1m MACD Histogram", "macd_hist_1m"),
    ("Opposing S/R Clearance (ATR)", "opp_sr_clearance_atr"),
    ("Candle Body Ratio", "body_ratio"),
    ("Directional Candle Close (%)", "is_candle_aligned"),
    ("1m ATR ($)", "atr_1m"),
]

print("\n" + "="*80)
print("3. FEATURE DISTRIBUTION COMPARISON (GROUP A vs B vs C)")
print("="*80)
print(f"{'Feature':<30} | {'Group A (Clean Win)':<20} | {'Group B (Early Stop-Rev)':<24} | {'Group C (Dir Failure)':<20}")
print("-" * 105)

for label, key in features_to_compare:
    vals_a = [f[key] for f in group_a]
    vals_b = [f[key] for f in group_b]
    vals_c = [f[key] for f in group_c]
    
    if key == "is_candle_aligned":
        mean_a = np.mean(vals_a) * 100
        mean_b = np.mean(vals_b) * 100
        mean_c = np.mean(vals_c) * 100
        print(f"{label:<30} | {mean_a:>6.2f}%              | {mean_b:>6.2f}%                 | {mean_c:>6.2f}%")
    else:
        mean_a, med_a = np.mean(vals_a), np.median(vals_a)
        mean_b, med_b = np.mean(vals_b), np.median(vals_b)
        mean_c, med_c = np.mean(vals_c), np.median(vals_c)
        print(f"{label:<30} | {mean_a:>6.3f} (med: {med_a:>6.3f}) | {mean_b:>6.3f} (med: {med_b:>6.3f})    | {mean_c:>6.3f} (med: {med_c:>6.3f})")

# ----------------------------------------------------------------------
# 4. Feature Redundancy & Correlation Matrix
# ----------------------------------------------------------------------
print("\n" + "="*80)
print("4. FEATURE CORRELATION & REDUNDANCY ANALYSIS")
print("="*80)

feature_keys = [
    "score", "dist_ema9_1m_atr", "dist_ema21_1m_atr", "dist_ema50_1m_atr",
    "dist_ema50_5m_atr", "rsi_1m", "macd_hist_1m", "opp_sr_clearance_atr", "body_ratio", "atr_1m"
]

feature_mat = np.array([[f[k] for k in feature_keys] for f in trade_features])
corr_mat = np.corrcoef(feature_mat, rowvar=False)

print(f"{'Feature':<20} | " + " | ".join([f"{k[:7]:<7}" for k in feature_keys]))
print("-" * 110)
for i, k in enumerate(feature_keys):
    row_str = f"{k:<20} | " + " | ".join([f"{corr_mat[i, j]:>7.2f}" for j in range(len(feature_keys))])
    print(row_str)

# ----------------------------------------------------------------------
# 5. Market Regime Analysis
# ----------------------------------------------------------------------
print("\n" + "="*80)
print("5. MARKET REGIME PERFORMANCE BREAKDOWN (WHOLE SAMPLE)")
print("="*80)

regime_buckets = {
    "Strong Trend (5m EMA9>21>50 + 5m Trend + Dist<=2ATR)": [],
    "Overextended Trend (Dist 5m EMA50 > 2.0 ATR)": [],
    "Pullback in Trend (Dist 1m EMA21 <= 0.5 ATR in 5m Trend)": [],
    "Tight Range / Low Vol (1m ATR < $0.75 or 5m Range)": [],
    "High Volatility / Expansion (1m ATR >= $2.00)": [],
    "Low Opposing S/R Clearance (Clearance <= 0.5 ATR)": [],
    "High Opposing S/R Clearance (Clearance > 1.5 ATR)": []
}

for f in trade_features:
    t_5m = f["trend_5m"]
    d_5m = f["dist_ema50_5m_atr"]
    d_1m_21 = f["dist_ema21_1m_atr"]
    atr = f["atr_1m"]
    clr = f["opp_sr_clearance_atr"]
    
    if t_5m in ["BULLISH", "BEARISH"] and d_5m <= 2.0:
        regime_buckets["Strong Trend (5m EMA9>21>50 + 5m Trend + Dist<=2ATR)"].append(f)
    if d_5m > 2.0:
        regime_buckets["Overextended Trend (Dist 5m EMA50 > 2.0 ATR)"].append(f)
    if t_5m in ["BULLISH", "BEARISH"] and abs(d_1m_21) <= 0.5:
        regime_buckets["Pullback in Trend (Dist 1m EMA21 <= 0.5 ATR in 5m Trend)"].append(f)
    if atr < 0.75 or t_5m == "RANGE":
        regime_buckets["Tight Range / Low Vol (1m ATR < $0.75 or 5m Range)"].append(f)
    if atr >= 2.00:
        regime_buckets["High Volatility / Expansion (1m ATR >= $2.00)"].append(f)
    if clr <= 0.5:
        regime_buckets["Low Opposing S/R Clearance (Clearance <= 0.5 ATR)"].append(f)
    if clr > 1.5:
        regime_buckets["High Opposing S/R Clearance (Clearance > 1.5 ATR)"].append(f)

print(f"{'Regime Bucket':<58} | {'Trades':<7} | {'Win Rate':<9} | {'Net R':<10} | {'Avg R':<8} | {'PF':<6}")
print("-" * 105)
for r_name, r_trades in regime_buckets.items():
    if not r_trades: continue
    r_n = len(r_trades)
    r_wins = sum(1 for tr in r_trades if tr["r_multiple"] > 0)
    r_wr = r_wins / r_n * 100
    r_net_r = sum(tr["r_multiple"] for tr in r_trades)
    r_avg_r = r_net_r / r_n
    r_gp = sum(tr["r_multiple"] for tr in r_trades if tr["r_multiple"] > 0)
    r_gl = sum(abs(tr["r_multiple"]) for tr in r_trades if tr["r_multiple"] < 0)
    r_pf = (r_gp / r_gl) if r_gl > 0 else 0.0
    print(f"{r_name:<58} | {r_n:<7} | {r_wr:>7.2f}% | {r_net_r:>9.2f}R | {r_avg_r:>7.3f}R | {r_pf:>5.2f}")

print("\nScript Part 1 Complete.")
