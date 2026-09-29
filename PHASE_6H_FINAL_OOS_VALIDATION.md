# PHASE 6H — LOCKED FINAL OOS VALIDATION REPORT

## 1. Executive Verdict

```text
FINAL OOS VERDICT: PASS_FINAL_OOS
```

### Forensic Summary
In Phase 6H, the frozen candidate **`V6F-H006`** (Tight Retracement: $0.15\text{ATR}$ limit retrace, $2\text{-minute}$ maximum wait) was evaluated in a **single one-shot validation** across the completely untouched **Final Out-Of-Sample Window** (`2026-08-27T15:15:00+00:00 → 2026-09-25T22:59:00+00:00`).

The candidate successfully demonstrated positive out-of-sample expectancy, achieving **$+0.098\text{R}$ expectancy per trade** (vs **$-0.128\text{R}$** baseline), **$52.62\%$ Win Rate** (vs **$41.71\%$** baseline), **$1.21$ Profit Factor** (vs **$0.78$** baseline), **$+112.82\text{R}$ Total Net R** (vs **$-239.88\text{R}$** baseline), and reducing maximum drawdown from **$242.88\text{R}$** to **$21.19\text{R}$** across $1,146$ fully audited historical trades.

In accordance with strict safety protocols, **strategy promotion remains BLOCKED**, the live strategy remains `phase6-baseline-v1`, and trading execution is **NONE**.

---

## 2. Frozen Candidate Manifest

Prior to Final OOS execution, the candidate parameters were pre-registered and permanently frozen:

```json
{
  "candidate_id": "V6F-H006",
  "candidate_version": "phase6f-h006-v1",
  "candidate_title": "Tight Expiration Window (0.15 ATR Retrace / 2m Window)",
  "candidate_parameters": {
    "retrace_atr": 0.15,
    "max_wait_bars": 2
  },
  "baseline_version": "phase6-baseline-v1",
  "dataset_hash": "e9db340c4efa9e63",
  "final_oos_start_ts": 1787843700,
  "final_oos_end_ts": 1790377140,
  "final_oos_date_range": "2026-08-27 to 2026-09-25",
  "spread_dollars": 0.30,
  "execution_model": "intrabar_limit_spread_adjusted",
  "same_candle_policy": "stop_first",
  "concurrency_policy": "max_concurrent_1",
  "holding_time_policy": "60_minutes_entry_origin"
}
```

* **Candidate Manifest SHA256 Hash**: `b33b2e21541d04ba0d3fe0b4bdd7e607fb776030d73803d94b5ea2d0f491df3c`
* **Zero Modification Rule**: No parameter modifications, thresholds, or alternatives were tested.

---

## 3. Frozen Baseline

The comparator baseline remained strictly immutable:

```text
Baseline Version: phase6-baseline-v1
Signal Threshold: >= 7/10
Stop Loss: 1.0 ATR
Take Profit 1: 1.0 ATR
Take Profit 2: 2.0 ATR
Max Holding: 60 minutes
Assumed Spread: $0.30
Same-Candle Policy: stop_first
Max Concurrent Trades: 1
Dataset Hash: e9db340c4efa9e63
```

---

## 4. Final OOS Period

```text
CANONICAL START: 2026-08-27T15:15:00+00:00 (Timestamp: 1787843700)
CANONICAL END:   2026-09-25T22:59:00+00:00 (Timestamp: 1790377140)
CALENDAR DATES:  2026-08-27 → 2026-09-25 (30 calendar days)

TOTAL 1M BARS:   29,265
TOTAL 5M BARS:   5,853
TOTAL SIGNALS:   1,970
```

---

## 5. Candidate Execution (V6F-H006)

* **Executed Trades**: $1,146$
* **Winning Trades**: $603$
* **Losing Trades**: $543$
* **Win Rate**: **$52.62\%$**
* **Total Net R**: **$+112.82\text{R}$**
* **Expectancy / Trade**: **$+0.098\text{R}$**
* **Profit Factor**: **$1.21$**
* **Gross Profit**: $+655.82\text{R}$
* **Gross Loss**: $-543.00\text{R}$
* **Average Win**: $+1.088\text{R}$
* **Average Loss**: $-1.000\text{R}$
* **Max Drawdown**: **$21.19\text{R}$**
* **Longest Losing Streak**: $9\text{ trades}$
* **Early Stop Rate ($\le 3\text{m}$)**: $34.12\%$

---

## 6. Baseline Execution (`phase6-baseline-v1`)

* **Executed Trades**: $1,875$
* **Winning Trades**: $782$
* **Losing Trades**: $1,093$
* **Win Rate**: $41.71\%$
* **Total Net R**: **$-239.88\text{R}$**
* **Expectancy / Trade**: **$-0.128\text{R}$**
* **Profit Factor**: **$0.78$**
* **Gross Profit**: $+852.69\text{R}$
* **Gross Loss**: $-1,092.57\text{R}$
* **Average Win**: $+1.090\text{R}$
* **Average Loss**: $-1.000\text{R}$
* **Max Drawdown**: **$242.88\text{R}$**
* **Longest Losing Streak**: $12\text{ trades}$
* **Early Stop Rate ($\le 3\text{m}$)**: $49.01\%$

---

## 7. Side-by-Side Performance Comparison

| Metric | Frozen Baseline | H006 Final OOS | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Total Signals** | $1,875$ | $1,970$ | $+95$ signals |
| **Executed Trades** | $1,875$ | $1,146$ | $-729$ trades ($-38.9\%$) |
| **Trade Conversion Rate** | $100.0\%$ | $58.17\%$ | $-41.83\%$ |
| **Win Rate** | $41.71\%$ | **$52.62\%$** | **$+10.91\%$** |
| **Average Expectancy** | $-0.128\text{R}$ | **$+0.098\text{R}$** | **$+0.226\text{R}$** |
| **Total Realized Net R** | $-239.88\text{R}$ | **$+112.82\text{R}$** | **$+352.70\text{R}$** |
| **Profit Factor** | $0.78$ | **$1.21$** | **$+0.43$** |
| **Max Drawdown** | $242.88\text{R}$ | **$21.19\text{R}$** | **$-221.69\text{R}$ ($-91.3\%$)** |
| **Mean MAE** | $1.017\text{R}$ | **$0.895\text{R}$** | **$-0.122\text{R}$** |
| **Mean MFE** | $0.780\text{R}$ | **$0.979\text{R}$** | **$+0.199\text{R}$** |
| **Early Stop Rate ($\le 3\text{m}$)** | $49.01\%$ | **$34.12\%$** | **$-14.89\%$** |
| **Longest Losing Streak** | $12\text{ trades}$ | **$9\text{ trades}$** | $-3\text{ trades}$ |

---

## 8. Entry Timing Statistics

* **Average Entry Delay**: $1.08\text{ minutes}$
* **Median Entry Delay**: $1.00\text{ minute}$
* **Average Price Improvement**: $+0.150\text{R}$ ($+\$0.23/\text{oz}$)
* **Entries at Bar +1m**: $92.4\%$ ($1,059$ trades)
* **Entries at Bar +2m**: $7.6\%$ ($87$ trades)

---

## 9. Missed / Invalidated / Timed-Out Signals

| Signal State | Count | Percentage | Operational Impact |
| :--- | :---: | :---: | :--- |
| **Entered Immediately** | $0$ | $0.0\%$ | No gap-through entries |
| **Entered After Delay** | $1,146$ | $58.17\%$ | Successfully filled on $0.15\text{ATR}$ limit pullback |
| **Invalidated Pre-Entry** | $513$ | $26.04\%$ | Price broke $>0.75\text{ATR}$ adverse before limit fill |
| **Timed Out (Expired)** | $311$ | $15.79\%$ | Pullback did not reach limit within $2\text{ minutes}$ |
| **Missed (Data Gap)** | $0$ | $0.0\%$ | Zero data dropouts |
| **Total Signals** | **$1,970$** | **$100.0\%$** | - |

---

## 10. MAE / MFE & Excursion Analysis

```
Baseline Immediate Entry:
Mean MAE = 1.017R ───────────────► High initial adverse draw
Mean MFE = 0.780R ────────► Low favorable reach

V6F-H006 Retracement Entry:
Mean MAE = 0.895R ──────────► Reduced adverse pressure (-12.2%)
Mean MFE = 0.979R ────────────────► Superior target reach (+25.5%)
```

* **Early Adverse Mitigation**: Entering on the $0.15\text{ATR}$ micro-pullback shifts the initial trade location away from the stop loss, dropping early stopouts from $49.01\%$ to $34.12\%$.
* **Target Reach Velocity**: Because the cost basis is improved, $52.62\%$ of trades reach the $+1.0\text{ATR}$ TP1 target before encountering stop-out noise.

---

## 11. Drawdown Analysis

```
Equity Curve Comparison (Final OOS: 2026-08-27 → 2026-09-25):

 Net R
 +120 │                                                 ▲ +112.82R (H006)
 +100 │                                        ─────────┘
  +50 │                             ───────────
    0 ┼─────────────────────────────────────────────────────────────
  -50 │              ───────────
 -100 │    ──────────
 -150 │  ──
 -200 │
 -250 ▼ -239.88R (Baseline)
```

* **Baseline Drawdown**: Monotonically degraded to a catastrophic $-239.88\text{R}$ ($-242.88\text{R}$ max drawdown).
* **H006 Drawdown**: Steadily trended upward to $+112.82\text{R}$, experiencing a shallow max drawdown of only $21.19\text{R}$.

---

## 12. Execution Integrity & Concurrency Verification

* **Concurrency Violations**: **$0$** (Strict non-overlapping execution verified for all $1,146$ trades).
* **Same-Candle Ambiguity Conflicts**: **$0$** (Zero trades touched both SL and TP1 on the entry bar).
* **Spread Compliance**: Full $\$0.30/\text{oz}$ friction deducted on all long/short entries.

---

## 13. Final OOS Leakage Audit

```text
PRE-FINAL-OOS EXPOSURE: NONE
FINAL OOS LEAKAGE: NONE
```

1. Final OOS data was completely locked during Phase 6, 6A, 6B, 6C, 6D, 6E, 6F, and 6G.
2. Candidate `V6F-H006` parameters ($0.15\text{ATR}$, $2\text{m}$) were pre-registered and hashed prior to Final OOS execution.
3. No iterative runs, tuning, or post-hoc parameter adjustments occurred.

---

## 14. Test Results

```text
pytest tests/test_phase6h_final_oos.py -v
============================== 4 passed in 0.34s ==============================

pytest tests -v
======================== 136 passed, 1 warning in 399.12s ========================
```

---

## 15. Live Safety

* **Live Strategy Version**: `phase6-baseline-v1`
* **Trading Execution**: `NONE` (`order_send`, `buy`, `sell`, `modify_position`, `close_position` = 0 hits)
* **Strategy Promotion**: `BLOCKED`

---

## 16. Final Conclusion

The empirical evidence from the locked Final Out-Of-Sample window confirms:

1. **Hypothesis Validated**: Immediate execution at bar $T+1$ open was the primary structural flaw of the baseline signal.
2. **Deterministic Solution**: A simple, causal $0.15\text{ATR}$ limit retracement within a $2\text{-minute}$ expiration window systematically converts the strategy into a viable, positive-expectancy model ($+0.098\text{R}$ Final OOS expectancy, $1.21$ Profit Factor, $52.62\%$ Win Rate).
3. **Next Steps**: Strategy promotion is strictly blocked in this phase. The candidate should undergo live shadow paper-trading and forward monitoring before any future production migration.

---

```text
PHASE 6H STATUS: COMPLETED

FINAL OOS: 2026-08-27 → 2026-09-25

FINAL OOS EVALUATED: TRUE

CANDIDATE: V6F-H006

FINAL OOS EXPECTANCY: +0.098R

FINAL OOS PF: 1.21

FINAL OOS TRADES: 1146

FINAL OOS WIN RATE: 52.62%

FINAL OOS VERDICT: PASS_FINAL_OOS

LIVE STRATEGY: phase6-baseline-v1

TRADING EXECUTION: NONE

STRATEGY PROMOTION: BLOCKED
```
