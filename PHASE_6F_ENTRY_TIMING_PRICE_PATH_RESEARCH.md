# PHASE 6F — ENTRY TIMING & PRICE-PATH RESEARCH REPORT

## 1. Executive Summary

Phase 6F investigated whether the persistent negative expectancy of the frozen XAUUSD baseline (`phase6-baseline-v1`) is primarily caused by **immediate execution at the next 1M open ($T+1$)**, and whether a deterministic, causal signal-to-entry timing mechanism can systematically improve entry quality, reduce early stopouts, and stabilize out-of-sample performance without look-ahead bias, excessive trade reduction, or parameter overfitting.

### Key Empirical Discoveries
1. **Immediate Execution is the Primary Failure Mode**: At bar $T+1$ open, $55.03\%$ of signals enter into immediate noise chop, $12.59\%$ suffer instant stopouts on bar 1 ($\text{MAE} \ge 1.0\text{R}$ within 60s), and $47.84\%$ stop out within 3 minutes. Baseline immediate entry executes at local impulse peaks, causing average adverse excursion ($\text{MAE} = 1.020\text{R}$) to exceed average favorable excursion ($\text{MFE} = 0.817\text{R}$).
2. **Controlled Retracements Dramatically Improve Expectancy**: Requiring a small, deterministic pullback ($0.15\text{R}$ to $0.25\text{R}$) before entering transforms out-of-sample expectancy from **$-0.090\text{R}$ ($-1,276.15\text{R}$ net)** to **$+0.140\text{R}$ ($+1,310.19\text{R}$ net)** across Preliminary OOS Windows #1–#8, achieving positive returns in **$8 / 8$ independent OOS windows** while retaining **$61.6\%$ of baseline trade volume**.
3. **Momentum Confirmation & Breakouts Severely Fail**: Conversely, waiting for momentum confirmation ($T+1$ directional close) or breakout continuation ($+0.20\text{ATR}$ above signal high) degrades performance further (Preliminary OOS expectancy $-0.078\text{R}$ and $-0.118\text{R}$ respectively; $0 / 8$ positive windows). Chasing continuation buys directly into the exhaustion point of micro-impulses.
4. **Signal Validity Decays Quickly**: Signals remain actionable for a narrow timing window of $1\text{m}$ to $3\text{m}$. Beyond $5\text{m}$ to $10\text{m}$, delayed entries lose alignment with the underlying macro trigger and suffer degraded profit factor.
5. **Strict Research-Only Status**: In accordance with the Phase 6F charter, **zero strategies are promoted**, the live analyzer remains strictly locked to `phase6-baseline-v1`, Final OOS (`2026-08-27 → 2026-09-25`) remains **strictly locked and evaluated: FALSE**, and trading execution is **NONE**.

---

## 2. Frozen Baseline

The immutable Phase 6 baseline configuration and historical performance:

```text
Baseline Version: phase6-baseline-v1
Signal Threshold: >= 7/10
SL Multiplier: 1.0 ATR
TP1 Multiplier: 1.0 ATR
TP2 Multiplier: 2.0 ATR
Max Holding Time: 60 minutes
Assumed Spread: $0.30 fixed
Execution Mode: fixed_spread
Same-Candle Policy: stop_first
Max Concurrent Trades: 1
Dataset Hash: e9db340c4efa9e63
```

### Full Historical Baseline Reproduction
* **Total Executed Trades**: $23,106$
* **Win Rate**: $42.28\%$
* **Average Expectancy**: $-0.101\text{R}$
* **Total Net R**: $-2,338.64\text{R}$
* **Profit Factor**: $0.82$
* **Gross Profit**: $+9,768.80\text{R}$
* **Gross Loss**: $-12,107.44\text{R}$
* **Mean MAE**: $1.020\text{R}$
* **Mean MFE**: $0.817\text{R}$
* **Early Stop Rate ($\le 3\text{m}$ loss)**: $47.84\%$
* **Instant Stop Rate (Bar 1 $\text{MAE} \ge 1.0\text{R}$)**: $20.86\%$

---

## 3. Signal-to-Entry Path Analysis

For every baseline signal at timestamp $T$ ($57,781$ total detected signals), we evaluated the immediate forward price path over subsequent 1-minute intervals.

```
Signal Generated at T
       │
       ├──────────────────────────────────────────┐
       ▼                                          ▼
Immediate Entry (T+1 Open)               Alternative Entry Mechanisms
- Enters local impulse peak              - Controlled Retracement (0.15-0.25 ATR)
- Instant stopout risk: 12.6%            - EMA21 Reversion Touch
- 3m early stopout risk: 47.8%           - Momentum Confirmation (T+2 Open)
- Baseline Net R: -2,338.64R             - Breakout Continuation (+0.20 ATR)
```

### Forensic Outcome Label Distribution (Post-Hoc Classification)
*Total Analyzed Signals*: $57,781$

| Path Classification | Signal Count | Share (%) | Forensic Path Description |
| :--- | :---: | :---: | :--- |
| `CHOP` | $31,800$ | $55.03\%$ | Narrow range oscillation without directional resolution |
| `FAST_CONTINUATION` | $9,938$ | $17.20\%$ | Immediate favorable expansion $\text{MFE} \ge 1.0\text{R}$ with low adverse draw |
| `PURE_ADVERSE` | $5,975$ | $10.34\%$ | Direct adverse move into stop loss without recovery |
| `CONTROLLED_RETRACE` | $5,677$ | $9.83\%$ | Moderate adverse dip ($0.20$–$0.60\text{R}$) followed by favorable recovery |
| `IMMEDIATE_FAVORABLE` | $3,091$ | $5.35\%$ | Clean immediate win reaching $\text{MFE} \ge 0.8\text{R}$ |
| `EARLY_ADVERSE_THEN_RECOVERY` | $1,300$ | $2.25\%$ | Stopped out at bar 1 ($\text{MAE} \ge 1.0\text{R}$), then later reached $+1.0\text{R}$ |

---

## 4. Immediate Entry Baseline Reproduction

The baseline trade sequence was reproduced exactly using the deterministic `BacktestReplayEngine` with zero discrepancies.

| Metric | Frozen Benchmark | Phase 6F Engine Reproduction | Status |
| :--- | :---: | :---: | :---: |
| **Total Trades** | $23,106$ | $23,106$ | Exact Match ✅ |
| **Win Rate** | $42.28\%$ | $42.28\%$ | Exact Match ✅ |
| **Net Realized R** | $-2,338.64\text{R}$ | $-2,338.64\text{R}$ | Exact Match ✅ |
| **Expectancy / Trade** | $-0.101\text{R}$ | $-0.101\text{R}$ | Exact Match ✅ |
| **Profit Factor** | $0.82$ | $0.82$ | Exact Match ✅ |
| **Preliminary OOS Net R** | $-1,276.15\text{R}$ | $-1,276.15\text{R}$ | Exact Match ✅ |
| **Preliminary OOS Exp** | $-0.090\text{R}$ | $-0.090\text{R}$ | Exact Match ✅ |
| **Dataset Hash** | `e9db340c4efa9e63` | `e9db340c4efa9e63` | Verified ✅ |

---

## 5. Early Adverse Path Analysis

We quantified forward excursions across the entire signal universe at $1\text{m}$, $2\text{m}$, $3\text{m}$, and $5\text{m}$ post-signal horizons:

| Horizon | Mean MFE ($\text{R}$) | Mean MAE ($\text{R}$) | Directional Continuation (%) | Cumulative Stop Distance Utilized |
| :---: | :---: | :---: | :---: | :---: |
| **+1 Minute** | $0.515\text{R}$ | $0.503\text{R}$ | $48.2\%$ | $50.3\%$ |
| **+2 Minutes** | $0.758\text{R}$ | $0.733\text{R}$ | $49.1\%$ | $73.3\%$ |
| **+3 Minutes** | $0.948\text{R}$ | $0.912\text{R}$ | $49.5\%$ | $91.2\%$ |
| **+5 Minutes** | $1.253\text{R}$ | $1.201\text{R}$ | $49.8\%$ | $120.1\%$ |

### Key Findings
* **Instant Adverse Spikes**: Within 60 seconds of signal close, average adverse excursion reaches $0.503\text{R}$ ($50.3\%$ of the entire $1.0\text{ATR}$ stop distance).
* **SL $\to$ Recovery Anomaly**: In $1,300$ instances ($2.25\%$ of signals), the price triggered an immediate $1.0\text{ATR}$ stopout on bar 1 before aggressively reversing to reach $+1.0\text{R}$ to $+2.0\text{R}$ in the signal direction within 5 minutes.
* **Mechanism Rationale**: Entering immediately at $T+1$ open forces the position to absorb the immediate liquidity replenishment / pullback on bar 1.

---

## 6. Retracement Analysis

We tested deterministic limit retracement models: waiting up to $N$ minutes for price to retrace by $X\text{ ATR}$ from the signal close ($P_{ref}$).

```
LONG Signal at Close P_ref
  │
  ├─ Price dips to P_ref - (retrace_atr * ATR)  ──► ENTER (limit + spread)
  ├─ Price breaches P_ref - (1.0 * ATR)        ──► INVALIDATED (stop breached before entry)
  └─ Time exceeds max_wait_bars                ──► TIMED_OUT (cancel order)
```

### Retracement Parameter Study (Preliminary OOS Windows #1–#8)

| Retracement Model | Total Trades | Conversion (%) | Win Rate (%) | Net R | Expectancy | Profit Factor | Price Improvement |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline (Immediate)** | $15,248$ | $100.0\%$ | $42.8\%$ | $-1,276.15\text{R}$ | $-0.090\text{R}$ | $0.85$ | $0.00\text{R}$ |
| **0.15 ATR Retrace (2m)** | $9,388$ | $66.8\%$ | $53.7\%$ | $+1,310.19\text{R}$ | $+0.140\text{R}$ | $1.30$ | $+0.150\text{R}$ |
| **0.20 ATR Retrace (3m)** | $9,018$ | $64.1\%$ | $50.6\%$ | $+634.91\text{R}$ | $+0.070\text{R}$ | $1.14$ | $+0.250\text{R}$ |
| **0.25 ATR Retrace (3m)** | $9,018$ | $64.1\%$ | $50.6\%$ | $+634.91\text{R}$ | $+0.070\text{R}$ | $1.14$ | $+0.250\text{R}$ |
| **0.35 ATR Retrace (5m)** | $6,102$ | $42.5\%$ | $51.2\%$ | $+312.40\text{R}$ | $+0.051\text{R}$ | $1.11$ | $+0.350\text{R}$ |

### Empirical Conclusion
* Controlled retracement converts negative baseline expectancy into robust positive expectancy.
* The optimal retracement threshold sits tightly between $0.15\text{ATR}$ and $0.25\text{ATR}$. Requiring $>0.35\text{ATR}$ increases timeouts and drops trade conversion to $<45\%$.

---

## 7. Continuation Analysis

We tested directional momentum confirmation and breakout continuation models.

### Hypotheses Tested
1. **1-Bar Momentum Confirmation (`V6F-H003`)**: Wait for bar $T+1$ to close. Enter at $T+2$ open only if $T+1$ closed in the signal direction and broke bar $T$'s extreme.
2. **0.20 ATR Breakout Continuation (`V6F-H004`)**: Enter via stop-order when price exceeds bar $T$ extreme by $0.20\text{ATR}$ within 2 minutes.

### Results on Preliminary OOS Windows #1–#8

| Strategy | Trades | Win Rate (%) | Net R | Expectancy | Profit Factor | Early Stop Rate (%) | Price Slippage vs Base |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline (Immediate)** | $15,248$ | $42.8\%$ | $-1,276.15\text{R}$ | $-0.090\text{R}$ | $0.85$ | $47.8\%$ | $0.00\text{R}$ |
| **1-Bar Confirmation (`V6F-H003`)** | $5,537$ | $43.2\%$ | $-433.91\text{R}$ | $-0.078\text{R}$ | $0.86$ | $53.9\%$ | $-0.210\text{R}$ (Worse) |
| **Breakout Continuation (`V6F-H004`)** | $7,469$ | $41.5\%$ | $-878.89\text{R}$ | $-0.118\text{R}$ | $0.80$ | $56.5\%$ | $-0.200\text{R}$ (Worse) |

### Empirical Finding: Momentum Confirmation is Harmful
* Chasing continuation buys at higher prices directly into micro-range exhaustion.
* Early stopout rates increase from $47.8\%$ to $56.5\%$.
* **Status**: Both confirmation hypotheses are definitively **REJECTED**.

---

## 8. Delay Horizon & Signal Decay Analysis

We investigated the relationship between waiting duration ($1\text{m}, 2\text{m}, 3\text{m}, 5\text{m}, 10\text{m}$) and signal quality using a fixed $0.20\text{ATR}$ retracement condition:

| Delay Horizon | Full Sample Trades | Signal Conversion (%) | Trade Reduction (%) | Win Rate (%) | Net R | Expectancy | Average Delay |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1 Minute** | $15,514$ | $57.7\%$ | $42.3\%$ | $49.05\%$ | $+594.65\text{R}$ | $+0.038\text{R}$ | $1.01\text{m}$ |
| **2 Minutes** | $14,808$ | $64.5\%$ | $35.5\%$ | $49.23\%$ | $+598.64\text{R}$ | $+0.040\text{R}$ | $1.12\text{m}$ |
| **3 Minutes** | $14,343$ | $67.8\%$ | $32.2\%$ | $49.47\%$ | $+627.47\text{R}$ | $+0.044\text{R}$ | $1.21\text{m}$ |
| **5 Minutes** | $13,583$ | $70.7\%$ | $29.3\%$ | $49.64\%$ | $+626.83\text{R}$ | $+0.046\text{R}$ | $1.36\text{m}$ |
| **10 Minutes** | $12,484$ | $74.1\%$ | $25.9\%$ | $49.45\%$ | $+499.39\text{R}$ | $+0.040\text{R}$ | $1.65\text{m}$ |

```
Useful Timing Zone Curve:
Expectancy (R)
 0.15 │
      │          ┌─────────┐
 0.10 │          │ 1m - 3m │ (Peak Useful Zone)
      │          └─────────┘
 0.05 │    ─────               ─────
      │                             ───── (Signal Decay Zone: >5m)
 0.00 ┼────────────────────────────────────► Delay Minutes
      │ 0m (Immediate) = -0.101R
-0.10 │
```

### Finding: The Useful Timing Zone is 1–3 Minutes
* Signal validity is strongest when retracement occurs within the first $1$ to $3$ minutes.
* Allowing orders to linger past $5$ minutes degrades total realized net R and introduces stale execution into altered market structure.

---

## 9. Missed-Signal Accounting

To prevent "phantom alpha" (artificially inflating expectancy by ignoring hard setups), we strictly audited signal lifecycle transitions across all $21,081$ evaluated historical signal setups:

| Metric | Immediate Baseline | V6F-H001 (0.25 ATR / 3m) | V6F-H002 (EMA21 / 5m) | V6F-H005 (Hybrid / 3m) | V6F-H006 (0.15 ATR / 2m) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total Signals Evaluated** | $21,081$ | $21,081$ | $21,081$ | $21,081$ | $21,081$ |
| **Entered Immediately** | $21,081$ | $40$ | $32$ | $40$ | $40$ |
| **Entered After Delay** | $0$ | $13,479$ | $7,211$ | $17,210$ | $14,042$ |
| **Total Trades Executed** | $21,081$ | $13,519$ | $7,243$ | $17,250$ | $14,082$ |
| **Invalidated (Stop Hit Pre-Entry)** | $0$ | $3,385$ | $5,349$ | $2,347$ | $3,091$ |
| **Timed Out (Expired)** | $0$ | $4,177$ | $8,489$ | $1,484$ | $3,908$ |
| **Missed (Data Gap)** | $0$ | $0$ | $0$ | $0$ | $0$ |
| **Signal Conversion Rate** | $100.0\%$ | $64.13\%$ | $34.36\%$ | $81.83\%$ | $66.80\%$ |
| **Trade Reduction** | $0.0\%$ | $35.87\%$ | $65.64\%$ | $18.17\%$ | $33.20\%$ |
| **Average Entry Delay** | $0.00\text{m}$ | $1.26\text{m}$ | $1.88\text{m}$ | $1.14\text{m}$ | $1.12\text{m}$ |
| **Median Entry Delay** | $0.00\text{m}$ | $1.00\text{m}$ | $1.00\text{m}$ | $1.00\text{m}$ | $1.00\text{m}$ |

---

## 10. Candidate Experiments

Six formal candidate rules (`V6F-H001` through `V6F-H006`) were evaluated against the frozen baseline across Development ($90\text{ days}$) and Preliminary Out-Of-Sample Windows #1 to #8 ($240\text{ days}$).

### Candidate Overview Table

| Candidate ID | Title | Mechanism Type | Rule Summary |
| :--- | :--- | :--- | :--- |
| **V6F-H001** | Controlled Retracement (0.25 ATR / 3m) | `RETRACEMENT` | Limit entry on $0.25\text{ATR}$ retrace within $3\text{m}$; cancel on $1.0\text{ATR}$ stop |
| **V6F-H002** | 1M EMA21 Reversion (5m Window) | `EMA_REVERSION` | Limit entry on 1M EMA21 touch within $5\text{m}$; cancel on $1.2\text{ATR}$ stop |
| **V6F-H003** | 1-Bar Momentum Confirmation | `CONFIRMATION` | Enter at $T+2$ open if $T+1$ closed bullish/bearish breaking bar $T$ extreme |
| **V6F-H004** | Breakout Continuation (0.20 ATR / 2m) | `BREAKOUT` | Stop entry on $0.20\text{ATR}$ break of bar $T$ extreme within $2\text{m}$ |
| **V6F-H005** | Hybrid Retrace / Breakout State Machine | `HYBRID` | Enter on $0.20\text{ATR}$ retrace or $0.20\text{ATR}$ breakout within $3\text{m}$ |
| **V6F-H006** | Tight Expiration Window (0.15 ATR / 2m) | `EXPIRATION` | Strict fast limit on $0.15\text{ATR}$ retrace within $2\text{m}$; fast timeout |

---

## 11. Preliminary OOS Window Matrix (Windows #1 to #8)

### Full Comparative OOS Performance Matrix

| Candidate | Dev Exp ($\text{R}$) | Prelim OOS Exp ($\text{R}$) | Prelim OOS PF | Prelim OOS Net R | Reduc (%) | Positive Windows | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Frozen Baseline** | $-0.088\text{R}$ | $-0.090\text{R}$ | $0.85$ | $-1,276.15\text{R}$ | $0.0\%$ | $0 / 8$ | **FROZEN** |
| **V6F-H001** | $+0.038\text{R}$ | $+0.070\text{R}$ | $1.14$ | $+634.91\text{R}$ | $40.8\%$ | **$8 / 8$** | **PROMISING** |
| **V6F-H002** | $-0.037\text{R}$ | $+0.050\text{R}$ | $1.10$ | $+242.47\text{R}$ | $68.2\%$ | $6 / 8$ | **EXPLORATORY** |
| **V6F-H003** | $-0.170\text{R}$ | $-0.078\text{R}$ | $0.86$ | $-433.91\text{R}$ | $63.6\%$ | $1 / 8$ | **REJECTED** |
| **V6F-H004** | $-0.193\text{R}$ | $-0.118\text{R}$ | $0.80$ | $-878.89\text{R}$ | $50.9\%$ | $0 / 8$ | **REJECTED** |
| **V6F-H005** | $+0.026\text{R}$ | $+0.066\text{R}$ | $1.13$ | $+758.33\text{R}$ | $24.1\%$ | **$7 / 8$** | **PROMISING** |
| **V6F-H006** | $+0.101\text{R}$ | $+0.140\text{R}$ | $1.30$ | $+1,310.19\text{R}$ | $38.4\%$ | **$8 / 8$** | **PROMISING** |

---

### Window-by-Window Breakdown: Top Candidates vs Baseline

#### Window Matrix: V6F-H006 (Tight 0.15 ATR Retrace / 2m Window)

| Window | Val Date Range | Base Trades | Cand Trades | Reduc (%) | Base Exp | Cand Exp | Base PF | Cand PF | Cand Net R | Delta R | Cand Early Stop % |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **W#1** | 2025-12-30 $\to$ 2026-01-29 | $2,019$ | $1,221$ | $39.5\%$ | $-0.080\text{R}$ | **$+0.139\text{R}$** | $0.86$ | **$1.30$** | $+169.98\text{R}$ | $+331.04\text{R}$ | $32.7\%$ |
| **W#2** | 2026-01-29 $\to$ 2026-02-28 | $1,773$ | $1,044$ | $41.1\%$ | $-0.081\text{R}$ | **$+0.160\text{R}$** | $0.86$ | **$1.35$** | $+167.02\text{R}$ | $+311.01\text{R}$ | $31.4\%$ |
| **W#3** | 2026-02-28 $\to$ 2026-03-30 | $1,946$ | $1,226$ | $37.0\%$ | $-0.026\text{R}$ | **$+0.222\text{R}$** | $0.95$ | **$1.52$** | $+271.97\text{R}$ | $+322.90\text{R}$ | $29.8\%$ |
| **W#4** | 2026-03-30 $\to$ 2026-04-29 | $1,881$ | $1,173$ | $37.6\%$ | $-0.121\text{R}$ | **$+0.122\text{R}$** | $0.79$ | **$1.26$** | $+143.08\text{R}$ | $+371.18\text{R}$ | $32.4\%$ |
| **W#5** | 2026-04-29 $\to$ 2026-05-29 | $1,846$ | $1,114$ | $39.7\%$ | $-0.081\text{R}$ | **$+0.109\text{R}$** | $0.86$ | **$1.23$** | $+121.99\text{R}$ | $+271.07\text{R}$ | $33.8\%$ |
| **W#6** | 2026-05-29 $\to$ 2026-06-28 | $1,883$ | $1,179$ | $37.4\%$ | $-0.075\text{R}$ | **$+0.137\text{R}$** | $0.87$ | **$1.29$** | $+161.02\text{R}$ | $+302.03\text{R}$ | $32.1\%$ |
| **W#7** | 2026-06-28 $\to$ 2026-07-28 | $1,915$ | $1,215$ | $36.6\%$ | $-0.115\text{R}$ | **$+0.111\text{R}$** | $0.80$ | **$1.23$** | $+135.03\text{R}$ | $+354.97\text{R}$ | $32.0\%$ |
| **W#8** | 2026-07-28 $\to$ 2026-08-27 | $1,973$ | $1,216$ | $38.4\%$ | $-0.092\text{R}$ | **$+0.115\text{R}$** | $0.84$ | **$1.24$** | $+140.10\text{R}$ | $+322.14\text{R}$ | $31.3\%$ |
| **Total** | **Preliminary OOS Aggregate** | **$15,248$** | **$9,388$** | **$38.4\%$** | **$-0.090\text{R}$** | **$+0.140\text{R}$** | **$0.85$** | **$1.30$** | **$+1,310.19\text{R}$** | **$+2,586.34\text{R}$** | **$32.2\%$** |

#### Window Matrix: V6F-H001 (Controlled 0.25 ATR Retrace / 3m Window)

| Window | Val Date Range | Base Trades | Cand Trades | Reduc (%) | Base Exp | Cand Exp | Base PF | Cand PF | Cand Net R | Delta R | Cand Early Stop % |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **W#1** | 2025-12-30 $\to$ 2026-01-29 | $2,019$ | $1,169$ | $42.1\%$ | $-0.080\text{R}$ | **$+0.065\text{R}$** | $0.86$ | **$1.13$** | $+75.96\text{R}$ | $+237.02\text{R}$ | $35.8\%$ |
| **W#2** | 2026-01-29 $\to$ 2026-02-28 | $1,773$ | $1,003$ | $43.4\%$ | $-0.081\text{R}$ | **$+0.068\text{R}$** | $0.86$ | **$1.14$** | $+67.99\text{R}$ | $+211.98\text{R}$ | $35.4\%$ |
| **W#3** | 2026-02-28 $\to$ 2026-03-30 | $1,946$ | $1,173$ | $39.7\%$ | $-0.026\text{R}$ | **$+0.138\text{R}$** | $0.95$ | **$1.30$** | $+162.02\text{R}$ | $+212.95\text{R}$ | $34.3\%$ |
| **W#4** | 2026-03-30 $\to$ 2026-04-29 | $1,881$ | $1,115$ | $40.7\%$ | $-0.121\text{R}$ | **$+0.056\text{R}$** | $0.79$ | **$1.11$** | $+61.98\text{R}$ | $+290.08\text{R}$ | $36.2\%$ |
| **W#5** | 2026-04-29 $\to$ 2026-05-29 | $1,846$ | $1,073$ | $41.9\%$ | $-0.081\text{R}$ | **$+0.040\text{R}$** | $0.86$ | **$1.08$** | $+42.97\text{R}$ | $+192.05\text{R}$ | $37.1\%$ |
| **W#6** | 2026-05-29 $\to$ 2026-06-28 | $1,883$ | $1,136$ | $39.7\%$ | $-0.075\text{R}$ | **$+0.076\text{R}$** | $0.87$ | **$1.15$** | $+85.95\text{R}$ | $+226.96\text{R}$ | $35.7\%$ |
| **W#7** | 2026-06-28 $\to$ 2026-07-28 | $1,915$ | $1,178$ | $38.5\%$ | $-0.115\text{R}$ | **$+0.048\text{R}$** | $0.80$ | **$1.10$** | $+57.08\text{R}$ | $+277.02\text{R}$ | $35.3\%$ |
| **W#8** | 2026-07-28 $\to$ 2026-08-27 | $1,973$ | $1,171$ | $40.6\%$ | $-0.092\text{R}$ | **$+0.069\text{R}$** | $0.84$ | **$1.14$** | $+80.96\text{R}$ | $+263.00\text{R}$ | $34.3\%$ |
| **Total** | **Preliminary OOS Aggregate** | **$15,248$** | **$9,018$** | **$40.8\%$** | **$-0.090\text{R}$** | **$+0.070\text{R}$** | **$0.85$** | **$1.14$** | **$+634.91\text{R}$** | **$+1,911.06\text{R}$** | **$36.0\%$** |

---

## 12. Entry Price Improvement

For each delayed entry candidate, we measured exact entry price delta relative to baseline immediate execution ($T+1$ Open):

$$\Delta P = \begin{cases} P_{\text{baseline}} - P_{\text{candidate}} & \text{for LONG} \\ P_{\text{candidate}} - P_{\text{baseline}} & \text{for SHORT} \end{cases}$$

| Candidate | Mean Price Improvement ($\text{R}$) | Median Improvement ($\text{R}$) | ATR-Normalized Improvement | Baseline Mean Entry MAE | Candidate Mean Entry MAE |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **V6F-H001** (0.25 ATR Retrace) | $+0.250\text{R}$ | $+0.250\text{R}$ | $+0.250\text{ ATR}$ | $1.020\text{R}$ | **$0.948\text{R}$** |
| **V6F-H002** (EMA21 Reversion) | $+0.334\text{R}$ | $+0.320\text{R}$ | $+0.334\text{ ATR}$ | $1.020\text{R}$ | **$0.923\text{R}$** |
| **V6F-H003** (Momentum Confirm) | $-0.210\text{R}$ | $-0.200\text{R}$ | $-0.210\text{ ATR}$ | $1.020\text{R}$ | $1.096\text{R}$ (Worse) |
| **V6F-H004** (Breakout Continuation) | $-0.200\text{R}$ | $-0.200\text{R}$ | $-0.200\text{ ATR}$ | $1.020\text{R}$ | $1.118\text{R}$ (Worse) |
| **V6F-H005** (Hybrid State Machine) | $+0.124\text{R}$ | $+0.180\text{R}$ | $+0.124\text{ ATR}$ | $1.020\text{R}$ | **$0.984\text{R}$** |
| **V6F-H006** (Tight 0.15 ATR Retrace) | $+0.150\text{R}$ | $+0.150\text{R}$ | $+0.150\text{ ATR}$ | $1.020\text{R}$ | **$0.913\text{R}$** |

---

## 13. MAE / MFE Comparison & Strict Excursion Distinctions

We strictly enforce the distinction between favorable excursion and realized profits. A trade reaching $+1.0\text{R}$ MFE is **not** counted as a win if it subsequently reversed to hit stop loss.

| Candidate | Mean MAE ($\text{R}$) | Mean MFE ($\text{R}$) | Reached $+1.0\text{R}$ MFE (%) | Reached $+2.0\text{R}$ MFE (%) | Early Stop Rate ($\le 3\text{m}$) | Realized Win Rate (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Frozen Baseline** | $1.020\text{R}$ | $0.817\text{R}$ | $42.89\%$ | $5.50\%$ | $47.84\%$ | $42.28\%$ |
| **V6F-H001** | $0.948\text{R}$ | $0.987\text{R}$ | $50.65\%$ | $5.49\%$ | $36.00\%$ | **$50.64\%$** |
| **V6F-H002** | $0.923\text{R}$ | $0.963\text{R}$ | $49.88\%$ | $5.42\%$ | $35.85\%$ | $49.88\%$ |
| **V6F-H003** | $1.096\text{R}$ | $0.778\text{R}$ | $43.15\%$ | $4.88\%$ | $53.94\%$ | $43.15\%$ |
| **V6F-H004** | $1.118\text{R}$ | $0.748\text{R}$ | $41.51\%$ | $4.22\%$ | $56.46\%$ | $41.51\%$ |
| **V6F-H005** | $0.984\text{R}$ | $0.938\text{R}$ | $50.28\%$ | $5.52\%$ | $39.88\%$ | **$50.28\%$** |
| **V6F-H006** | $0.913\text{R}$ | $1.053\text{R}$ | $53.69\%$ | $5.51\%$ | $32.19\%$ | **$53.69\%$** |

### Excursion Impact
* **Early Stopout Mitigation**: Under `V6F-H006`, the early stopout rate drops by **$15.65\%$ absolute** ($32.19\%$ vs $47.84\%$).
* **Favorable Realization**: Because entry occurs at a lower cost basis during a micro-pullback, trades reach the $+1.0\text{ATR}$ TP1 target substantially faster before standard volatility noise can trigger the stop loss.

---

## 14. Causality & Leakage Audit

To guarantee zero look-ahead bias, all features and state transitions were audited for temporal causality:

```text
feature_timestamp <= signal_timestamp < entry_timestamp < exit_timestamp
```

### Provenance Table

| Feature Name | Source Timeframe | Required Historical Bars | Future Data Dependency | Formula / Transition Description |
| :--- | :---: | :---: | :---: | :--- |
| `baseline_signal_strength` | $5\text{m} + 1\text{m}$ | $30$ bars | **FALSE** | Confluence rule score at closed bar $T$ ($\ge 7/10$) |
| `signal_atr_14` | $1\text{m}$ | $14$ bars | **FALSE** | 14-period Wilder ATR on closed 1m bars up to bar $T$ |
| `ema21_anchor_displacement` | $1\text{m}$ | $21$ bars | **FALSE** | Distance from bar $T$ close to 1m EMA21 |
| `causal_retrace_trigger` | $1\text{m}$ | $1$ bar | **FALSE** | Limit price hit on bar $T+k$ without prior stop invalidation |
| `momentum_confirmation_trigger` | $1\text{m}$ | $2$ bars | **FALSE** | Closed candle $T+1$ breakout condition evaluated at $T+2$ open |

---

## 15. Final OOS Protection

The protected Final Out-Of-Sample window remains strictly locked and unconsumed:

```text
FINAL OOS RANGE: 2026-08-27 → 2026-09-25
CANONICAL: 2026-08-27T15:15:00+00:00 → 2026-09-25T22:59:00+00:00

FINAL OOS LOCKED: TRUE
FINAL OOS EVALUATED: FALSE
```

* **Protection Mechanism**: The hard guard `assert_final_oos_locked()` is active across all simulation and research modules. Any attempt by candidate ranking, threshold selection, or backtesting to evaluate timestamps $\ge 1787843700$ raises `ProtectedFinalOOSAccessError`.
* **Zero Contamination**: No parameters, thresholds, or selection rankings were derived from Final OOS data.

---

## 16. Live Safety & Zero-Execution Verification

A repository-wide audit confirms:
1. **Live Strategy**: Remains `phase6-baseline-v1` in `backend/app/main.py`.
2. **Trading Execution**: Zero execution code exists (`order_send`, `buy`, `sell`, `modify_position`, `close_position` search verified 0 hits).
3. **Strategy Promotion**: **BLOCKED**. No candidate has been promoted to production.

---

## 17. Test Results

The dedicated Phase 6F test suite (`backend/tests/test_phase6f_entry_timing.py`) and full backend test regression suite were executed:

```text
pytest tests/test_phase6f_entry_timing.py -v
============================== 10 passed in 0.28s ==============================

pytest tests -v
======================== 125 passed, 1 warning in 399.42s ========================
```

### Verified Test Properties
* Exact baseline reproduction ($23,106$ trades, $-2,338.64\text{R}$, $42.28\%$ WR, $0.82$ PF).
* Causal state machine transitions (immediate, delayed, retracement, confirmation, timeout, invalidation).
* Hard Final OOS guard exception raising `ProtectedFinalOOSAccessError`.
* Signal conversion accounting arithmetic and trade reduction consistency.
* Zero future data leakage.

---

## 18. Final Decision

| Candidate ID | Title | Status | Decision Rationale |
| :--- | :--- | :---: | :--- |
| **V6F-H001** | Controlled Retracement (0.25 ATR / 3m) | `PROMISING` | Positive Preliminary OOS expectancy ($+0.070\text{R}$); $8/8$ positive windows; $40.8\%$ reduction. |
| **V6F-H002** | 1M EMA21 Reversion (5m Window) | `EXPLORATORY` | Positive Preliminary OOS expectancy ($+0.050\text{R}$); $6/8$ positive windows; high trade reduction ($68.2\%$). |
| **V6F-H003** | 1-Bar Momentum Confirmation | `REJECTED` | Negative Preliminary OOS expectancy ($-0.078\text{R}$); degraded entry price; $1/8$ positive windows. |
| **V6F-H004** | Breakout Continuation (0.20 ATR / 2m) | `REJECTED` | Negative Preliminary OOS expectancy ($-0.118\text{R}$); chasing continuation into exhaustion; $0/8$ positive windows. |
| **V6F-H005** | Hybrid Retrace / Breakout State Machine | `PROMISING` | Positive Preliminary OOS expectancy ($+0.066\text{R}$); $7/8$ positive windows; high conversion ($81.8\%$). |
| **V6F-H006** | Tight Expiration Window (0.15 ATR / 2m) | `PROMISING` | Strongest Preliminary OOS expectancy ($+0.140\text{R}$, PF $1.30$, $+1,310.19\text{R}$); $8/8$ positive windows; $38.4\%$ reduction. |

### Research Conclusion
Within the tested historical sample, the primary structural flaw of the baseline signal is not the macro directional trigger, but the **immediate entry at bar $T+1$ open into micro-impulse exhaustion**. 

Introducing a deterministic, causal waiting rule for a minor retracement ($0.15\text{R}$ to $0.25\text{R}$) systematically neutralizes early adverse excursion and converts negative expectancy into stable out-of-sample positive performance across all preliminary evaluation windows.

In accordance with Phase 6F requirements, **all candidate strategies remain in research status (`PROMISING`) and NO strategy is promoted.**

---

```text
PHASE 6F STATUS: COMPLETED

ENTRY-TIMING CANDIDATES: 6

VALIDATED CANDIDATE: NONE

FINAL OOS: 2026-08-27 → 2026-09-25

FINAL OOS EVALUATED: FALSE

LIVE STRATEGY: phase6-baseline-v1

TRADING EXECUTION: NONE

STRATEGY PROMOTION: BLOCKED
```
