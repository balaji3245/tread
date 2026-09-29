# PHASE 6D — SIGNAL ENGINE V2 RESEARCH & DEVELOPMENT REPORT

**Research Date:** 2026-09-27  
**Engine Version:** `phase6d-signal-v2` (Research Boundary)  
**Baseline Version:** `phase6-baseline-v1` (Frozen Production Analyzer)  
**Historical Dataset:** XAUUSD M1 (340,729 bars) & M5 (68,221 bars) — ~359 Days  
**Scope:** Signal-generation quality redesign, feature redundancy analysis, market regime modeling, entry-timing forensics, and candidate hypothesis evaluation.

---

## 1. EXECUTIVE SUMMARY

Phase 6D investigated the core question established by previous forensic phases:
> **Why do baseline signals persistently lose, why do early stop-outs dominate, and can a redesigned signal-generation layer with orthogonal scoring and regime awareness produce positive out-of-sample expectancy?**

### Key Investigation Outcomes
1. **The Core Mechanism of Baseline Failure:**
   * Forensic excursion profiling across all **23,106 historical trades** revealed that the baseline signal engine systematically triggers at the **peak exhaustion point of 1-minute impulses**.
   * **$55.08\%$** of trades suffer $\ge 0.50\text{R}$ adverse excursion within **60 seconds** of entry.
   * **$55.94\%$ of all losing trades ($7,460$ trades)** are **Early Stop-Out Reversals (Group B)**: they hit the $-1.0\text{R}$ stop loss within $\le 3$ minutes, but subsequently move $\ge +1.0\text{R}$ in the intended signal direction within the 60-minute horizon.
2. **Feature Redundancy Unmasked:**
   * Multi-collinearity analysis revealed that `1m EMA 9/21 distance`, `1m EMA 21/50 distance`, `1m MACD histogram`, and `1m RSI` share high mutual correlation ($r = 0.53$ to $0.93$). The baseline 0–10 score was artificially compounding collinear momentum indicators, granting 4–5 points simultaneously during transient 1-minute spikes without structural confirmation.
3. **Hypothesis Testing Results (V2-H001 to V2-H006):**
   * Six evidence-backed signal hypotheses were evaluated across **90 days Development** and **Windows #1–#8 Preliminary OOS (240 days)**.
   * While individual quality rules (pullback confirmation, S/R clearance, multi-bar persistence) slightly mitigated per-trade loss magnitude, **none of the candidate models achieved positive Preliminary OOS expectancy or a profit factor $> 1.00$**.
   * In strict accordance with scientific integrity rules, **all 6 V2 hypotheses are formally `REJECTED`**. No candidate qualified for Final OOS evaluation.

---

## 2. BASELINE REFERENCE (FROZEN PRODUCTION)

The baseline configuration remains 100% frozen, immutable, and operational in the live analyzer:

```text
Baseline Version:      phase6-baseline-v1
Signal Threshold:      >= 7/10
Stop Loss:             1.0 ATR
Take Profit 1:         1.0 ATR
Take Profit 2:         2.0 ATR
Max Holding Time:      60 minutes
Spread Cost:           $0.30 (Fixed)
Same-Candle Policy:    stop_first
Max Concurrent Trades: 1
```

### Full Sample Historical Performance (359 Days)
* **Total Executed Trades:** `23,106`
* **Win Rate:** `42.28%`
* **Average R:** `-0.101R`
* **Total Net R:** `-2,338.64R`
* **Profit Factor:** `0.82`
* **Development Period (90d):** `5,995 trades`, `-822.61R`, `40.73% WR`, `PF 0.77`, `-0.14R/trade`
* **Preliminary OOS (Windows #1–#8, 240d):** `15,236 trades`, `-1,276.15R`, `42.96% WR`, `PF 0.85`, `-0.084R/trade`
* **Final OOS (Window #9, 29d):** `1,875 trades`, `-239.88R` (**LOCKED & PROTECTED**)

---

## 3. FORENSIC FINDINGS: TRADE GROUP & EXCURSION PROFILES

To identify why trades fail, the entire 23,106 baseline trade universe was partitioned into distinct forensic categories:

### Trade Group Distribution

| Group | Category Definition | Trade Count | Percentage |
| :--- | :--- | :---: | :---: |
| **Group A** | **Clean Immediate Winners** (Hit TP with $\text{MAE} \le 0.5\text{R}$) | `1,379` | `5.97%` |
| **Group B** | **Early Stop Reversals** (Stopped $\le 3$m at $-1.0\text{R}$, then reached $\text{MFE} \ge +1.0\text{R}$) | `7,460` | `32.29%` |
| **Group C** | **Directional Failures** (Losing trades where $\text{MFE} < +1.0\text{R}$) | `4,460` | `19.30%` |
| **Other Wins** | Winning trades experiencing $\text{MAE} > 0.5\text{R}$ prior to TP | `8,391` | `36.32%` |
| **Other Losses**| Losses holding $> 3$m or expiring at 60m | `1,416` | `6.13%` |
| **Total** | Whole Sample Trade Universe | **`23,106`** | **`100.00%`** |

### Critical Trajectory Metrics
* **Total Losses:** `13,336`
* **Early Reversal Proportion:** **`55.94%`** ($7,460 / 13,336$) of all losses were directionally correct over 60 minutes but were stopped out prematurely by 1-minute entry noise.
* **1-Minute Adverse Excursion:** Mean `0.668R` (Median `0.552R`). **$55.08\%$** of all entries experience $\ge 0.50\text{R}$ adverse movement on the very first bar!
* **1-Minute Instant Stopouts:** **$19.62\%$** of trades hit the full $-1.0\text{R}$ stop loss within 60 seconds of entry.
* **3-Minute Cumulative Stopouts:** **$44.12\%$** of trades reach $-1.0\text{R}$ within 3 minutes.
* **Forward Favorable Excursion Potential:** Mean 5-min MFE = `1.154R`, Mean 15-min MFE = `2.194R`, Mean 60-min MFE = `4.733R`.

---

## 4. FEATURE CONTRIBUTION & REDUNDANCY ANALYSIS

### Feature Distribution Comparison Across Groups

| Feature / Metric | Group A (Clean Win) | Group B (Early Stop-Rev) | Group C (Dir Failure) | Discriminative Value |
| :--- | :---: | :---: | :---: | :--- |
| **Signal Confluence Score** | `8.026` | `8.047` | `8.088` | **None** (Scores are identical) |
| **Dist to 1m EMA 9 (ATR)** | `0.402` | `0.489` | `0.426` | **High** (Group B overextended at entry) |
| **Dist to 1m EMA 21 (ATR)** | `1.016` | `1.067` | `1.013` | **High** (Chasing extended moves) |
| **Dist to 5m EMA 50 (ATR)** | `6.726` | `6.876` | `6.717` | **Moderate** (Macro exhaustion) |
| **1m RSI Level** | `51.37` | `50.78` | `50.49` | **Low / Noise** |
| **1m MACD Histogram** | `+0.023` | `-0.040` | `-0.044` | **Moderate** (Winners have positive momentum) |
| **Opposing S/R Clearance** | `82.98` (Med `0.72`) | `92.85` (Med `0.69`) | `80.41` (Med `0.70`) | **Moderate** |
| **Directional Candle Close** | `50.69%` | `53.18%` | `52.22%` | **Weak** |
| **1m ATR ($)** | `$2.99` | `$2.58` | `$2.88` | **Moderate** (Clean wins occur in higher volatility) |

### Feature Correlation Matrix

```text
Feature              | score   | dist_9  | dist_21 | dist_50 | d_5m50  | rsi_1m  | macd_h  | sr_clr  | body_r  | atr_1m 
-------------------------------------------------------------------------------------------------------------------------
score                |    1.00 |    0.02 |    0.08 |    0.07 |    0.01 |   -0.04 |   -0.01 |    0.02 |    0.02 |    0.00
dist_ema9_1m_atr     |    0.02 |    1.00 |    0.93 |    0.72 |    0.31 |    0.05 |   -0.04 |    0.48 |    0.03 |    0.06
dist_ema21_1m_atr    |    0.08 |    0.93 |    1.00 |    0.91 |    0.41 |    0.08 |   -0.04 |    0.52 |    0.03 |    0.10
dist_ema50_1m_atr    |    0.07 |    0.72 |    0.91 |    1.00 |    0.55 |    0.13 |   -0.04 |    0.50 |    0.03 |    0.12
dist_ema50_5m_atr    |    0.01 |    0.31 |    0.41 |    0.55 |    1.00 |    0.18 |    0.01 |    0.26 |    0.03 |    0.02
rsi_1m               |   -0.04 |    0.05 |    0.08 |    0.13 |    0.18 |    1.00 |    0.53 |    0.15 |    0.01 |   -0.15
macd_hist_1m         |   -0.01 |   -0.04 |   -0.04 |   -0.04 |    0.01 |    0.53 |    1.00 |    0.04 |    0.01 |   -0.15
opp_sr_clearance_atr |    0.02 |    0.48 |    0.52 |    0.50 |    0.26 |    0.15 |    0.04 |    1.00 |    0.07 |   -0.11
body_ratio           |    0.02 |    0.03 |    0.03 |    0.03 |    0.03 |    0.01 |    0.01 |    0.07 |    1.00 |    0.02
atr_1m               |    0.00 |    0.06 |    0.10 |    0.12 |    0.02 |   -0.15 |   -0.15 |   -0.11 |    0.02 |    1.00
```

### Classification of Baseline Features

| Feature | Correlation Redundancy | Incremental Information | Classification | Rationale |
| :--- | :--- | :--- | :---: | :--- |
| **1m EMA 9 & EMA 21** | $r = 0.93$ with each other | Low when combined | **`REDUNDANT`** | Granting separate score points for EMA9 and EMA21 double-counts short-term impulse. |
| **1m EMA 50** | $r = 0.91$ with EMA21 | Moderate (medium baseline) | **`CONTEXT-DEPENDENT`** | Useful for measuring extension, not as a standalone binary score. |
| **1m RSI (14)** | $r = 0.53$ with MACD Hist | Low | **`WEAK`** | Static 40–68 thresholds fail to discriminate winners from losers ($51.37$ vs $50.78$). |
| **1m MACD Histogram** | $r = 0.53$ with RSI | Moderate | **`USEFUL`** | Positive histogram aligns with clean winners; negative indicates counter-momentum. |
| **Opposing S/R Clearance** | $r = 0.02$ with Score | High | **`USEFUL`** | Completely orthogonal to score; entering $< 0.5\text{ATR}$ from S/R produces severe losses. |
| **1m ATR ($)** | $r = 0.00$ with Score | High | **`USEFUL`** | Low-ATR compression environments ($\text{ATR} < \$0.75$) produce disastrous PF ($0.54$). |
| **Candle Body Ratio** | $r = 0.02$ with Score | Low | **`WEAK`** | Candle body ratio alone does not filter whipsaws in 1-minute noise. |

---

## 5. MARKET REGIME PERFORMANCE BREAKDOWN

Evaluating baseline trades across distinct deterministic market regimes:

| Regime Bucket | Trade Count | Win Rate | Net R | Expectancy | Profit Factor | Assessment |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Strong Trend** (5m Trend + Dist $\le 2\text{ATR}$) | `1,012` | `42.19%` | `-129.00R` | `-0.127R` | `0.78` | Negative expectancy; trend filter alone insufficient. |
| **Overextended Trend** (5m EMA50 dist $> 2\text{ATR}$) | `22,094` | `42.29%` | `-2,209.64R` | `-0.100R` | `0.83` | Baseline operates almost entirely in overextension. |
| **Pullback in Trend** (1m EMA21 dist $\le 0.5\text{ATR}$) | `5,911` | `42.12%` | `-669.94R` | `-0.113R` | `0.80` | Reduced loss count, but per-trade expectancy remains negative. |
| **Tight Range / Low Vol** (ATR $< \$0.75$) | `74` | `31.08%` | `-23.66R` | `-0.320R` | `0.54` | **Severe failure mode**; spreads consume small ranges. |
| **High Volatility / Expansion** (ATR $\ge \$2.00$) | `13,752` | `44.39%` | `-817.45R` | `-0.059R` | `0.89` | Higher win rate and best PF, but still negative edge. |
| **Low Opposing S/R Clearance** ($\le 0.5\text{ATR}$) | `8,251` | `41.46%` | `-1,022.71R` | `-0.124R` | `0.79` | Immediate barrier collisions. |
| **High Opposing S/R Clearance** ($> 1.5\text{ATR}$) | `6,354` | `42.87%` | `-481.48R` | `-0.076R` | `0.87` | Significant loss reduction. |

---

## 6. SIGNAL ENGINE V2 ARCHITECTURE & SCORING MODEL

To eliminate collinearity, `app/signal_engine_v2.py` was constructed using **orthogonal scoring components**:

| Component | Meaning & Market Mechanism | Weight | Evidence / Justification |
| :--- | :--- | :---: | :--- |
| **1. 5M Macro Trend** | 5m EMA 9/21/50 alignment + 5m Higher-High / Higher-Low structure. | `2.5 pts` | Establishes higher-timeframe order flow direction. |
| **2. 1M Market Structure** | Strict swing high/low progression on 1m timeframe. | `2.0 pts` | Confirms local order flow agrees with 5m trend. |
| **3. Pullback Quality** | Distance from price to 1m EMA21 $\le 0.75\text{ATR}$. | `2.0 pts` | Prevents entering at the climax of 1m impulses. |
| **4. Opposing S/R Clearance** | Minimum $0.75\text{ATR}$ clearance to nearest opposing support/resistance. | `1.5 pts` | Prevents immediate collisions into structural boundaries. |
| **5. Directional Candle Body** | Signal candle closed in trade direction with body ratio $\ge 50\%$. | `1.0 pts` | Ensures entry candle is not an indecision doji or wick rejection. |
| **6. Volatility Regime** | 1m ATR $\ge \$1.00$. | `1.0 pts` | Filters out compressed, spread-dominated flat sessions. |
| **Overextension Penalty** | Distance to 5m EMA50 $> 2.0\text{ATR}$. | `-2.0 pts` | Penalizes late, exhausted trend breakouts. |

---

## 7. HYPOTHESIS EXPERIMENT RESULTS (DEV & PRELIMINARY OOS)

Six hypotheses were evaluated across **Development (90d)** and **Preliminary OOS Windows #1–#8 (240d)**:

| ID | Hypothesis & Rule Change | Dev Trades (Base=5995) | Dev Net R (Base=-822.61R) | Dev Exp | Prelim Trades (Base=15236) | Prelim Trade Red % | Prelim Net R (Base=-1276.15R) | Prelim Delta Net R | Prelim WR (Base=42.96%) | Prelim PF (Base=0.85) | Prelim Exp (Base=-0.084R) | Status | Decision Rationale |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **V2-H001** | **Pullback Confirmation** (`EMA21 dist <= 0.6 ATR`) | 2,711 | -517.33R | -0.191R | 6,945 | 54.4% | -568.04R | **+708.11R** | 43.66% | 0.85 | -0.082R | **`REJECTED`** | Negative OOS expectancy (-0.082R), PF 0.85 fails to exceed baseline. 0/8 profitable windows. |
| **V2-H002** | **S/R Clearance** (`Opposing S/R >= 1.0 ATR`) | 2,750 | -252.29R | -0.092R | 6,865 | 54.9% | -512.98R | **+763.17R** | 43.07% | 0.87 | -0.075R | **`REJECTED`** | Negative OOS expectancy (-0.075R), PF 0.87. 0/8 profitable windows. |
| **V2-H003** | **Directional Body** (`Body >= 50% & Aligned`) | 3,016 | -350.01R | -0.116R | 7,698 | 49.5% | -742.06R | **+534.09R** | 41.97% | 0.83 | -0.096R | **`REJECTED`** | Worsened OOS expectancy (-0.096R vs -0.084R), PF fell to 0.83. |
| **V2-H004** | **Signal Persistence** (`>= 2 Consecutive Bars`) | 4,999 | -690.31R | -0.138R | 12,830 | 15.8% | -1003.97R | **+272.18R** | 43.17% | 0.86 | -0.078R | **`REJECTED`** | Negative OOS expectancy (-0.078R), PF 0.86. 0/8 profitable windows. |
| **V2-H005** | **Volatility Expansion** (`1m ATR >= $1.50`) | 4,127 | -398.91R | -0.097R | 13,212 | 13.3% | -951.00R | **+325.15R** | 43.59% | 0.87 | -0.072R | **`REJECTED`** | Negative OOS expectancy (-0.072R), PF 0.87. 0/8 profitable windows. |
| **V2-H006** | **Composite Engine V2** (Pullback+Clearance+ATR) | 566 | -121.98R | -0.216R | 1,608 | 89.4% | -135.06R | **+1141.09R** | 43.91% | 0.85 | -0.084R | **`REJECTED`** | Severe trade reduction (89.4%), expectancy remains negative (-0.084R), PF 0.85. |

---

## 8. PRELIMINARY OOS WINDOW-BY-WINDOW MATRIX

Performance across each of the 8 individual Preliminary OOS windows for all hypotheses:

### Window Breakdown Table (Net R / Win Rate)

| Hypothesis | W#1 (12/30-01/29) | W#2 (01/29-02/28) | W#3 (02/28-03/30) | W#4 (03/30-04/29) | W#5 (04/29-05/29) | W#6 (05/29-06/28) | W#7 (06/28-07/28) | W#8 (07/28-08/27) | Profitable Windows |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline** | `-161.06R` (43.3%) | `-143.99R` (43.0%) | `-50.93R` (45.4%) | `-228.10R` (41.5%) | `-149.08R` (43.0%) | `-141.01R` (43.2%) | `-219.94R` (41.4%) | `-182.04R` (42.8%) | **0 / 8** |
| **V2-H001** | `-72.01R` (44.1%) | `-58.00R` (43.8%) | `-36.00R` (45.1%) | `-89.02R` (42.1%) | `-64.00R` (43.9%) | `-82.01R` (42.7%) | `-89.00R` (42.9%) | `-78.00R` (44.6%) | **0 / 8** |
| **V2-H002** | `-54.98R` (43.9%) | `-48.00R` (43.2%) | `-10.98R` (46.1%) | `-144.03R` (40.9%) | `-52.00R` (44.1%) | `-58.00R` (43.1%) | `-78.00R` (42.6%) | `-67.99R` (43.5%) | **0 / 8** |
| **V2-H003** | `-92.00R` (42.1%) | `-96.00R` (41.8%) | `+25.10R` (46.2%) | `-140.05R` (40.2%) | `-98.01R` (41.9%) | `-78.05R` (42.8%) | `-125.04R` (41.1%) | `-138.01R` (41.4%) | **1 / 8** |
| **V2-H004** | `-115.00R` (43.6%) | `-122.98R` (43.0%) | `-48.80R` (45.2%) | `-196.97R` (41.8%) | `-114.02R` (43.1%) | `-112.20R` (43.7%) | `-154.00R` (42.1%) | `-140.00R` (43.1%) | **0 / 8** |
| **V2-H005** | `-125.00R` (43.8%) | `-112.00R` (43.5%) | `-46.91R` (45.8%) | `-178.03R` (42.1%) | `-105.00R` (43.9%) | `-114.00R` (43.7%) | `-190.06R` (42.0%) | `-80.00R` (44.9%) | **0 / 8** |
| **V2-H006** | `-16.00R` (44.5%) | `-12.00R` (44.1%) | `-3.00R` (46.8%) | `-48.00R` (41.8%) | `-14.00R` (44.2%) | `-15.00R` (43.9%) | `-15.06R` (44.0%) | `-12.00R` (44.8%) | **0 / 8** |

---

## 9. DATA LEAKAGE & INTEGRITY AUDIT

1. **Information Timestamp Principle:**  
   * Every feature in `SignalEngineV2` depends strictly on candles $\le T$.
   * Slices use historical indicators computed only on past closes.
   * Entry executes at candle $T+1$ open with fixed $\$0.30$ spread.
2. **Zero Look-Ahead Tests:**  
   * Validated in `tests/test_phase6d_signal_engine_v2.py`: appending or removing future candles has zero effect on past signals or feature vectors.
3. **No Brute-Force Fitting:**  
   * No automated parameter grid search, genetic algorithms, or random sweeps were performed.

---

## 10. FINAL OOS PROTECTION ASSERTION

* **Protected Final OOS Window #9:** `2026-08-27T15:15:00+00:00 → 2026-09-25T22:59:00+00:00` (28,091 M1 bars).
* **Final OOS Status:** **`VERIFIED UNTOUCHED`**
* **Assertions Verified:**
  * `final_oos_locked = true` in all V2 experiment artifacts.
  * `final_oos_evaluated = false` in all V2 experiment artifacts.
  * Zero metrics from Window #9 were used for hypothesis screening, ranking, or candidate decisions.

---

## 11. LIVE SYSTEM ISOLATION & SAFETY AUDIT

* **Live Analyzer Strategy:** Frozen on `phase6-baseline-v1` in `app/main.py` and `app/routes/market.py`.
* **Execution Safety:** Zero live execution code exists. No `order_send`, `buy`, `sell`, `modify_position`, or `close_position` methods exist.
* **Strategy Promotion:** **`BLOCKED`**. No strategy candidate met the shortlist criteria (positive OOS expectancy, PF $> 1.0$, multi-window stability).

---

## 12. TEST SUITE VERIFICATION

* **Total Backend Tests:** **108 / 108 Passed (100%)**
* **Phase 6D Specific Tests:** 6 passed (`test_phase6d_signal_engine_v2.py`)
* **Validation & Integrity Tests:** 102 passed

```text
======================= 108 passed, 1 warning in 83.50s =======================
```

---

## 13. SCIENTIFIC CONCLUSION & DECISION

Phase 6D has conclusively demonstrated that **the negative performance of the XAUUSD strategy is structural to the combined 1m/5m momentum indicator framework**:
1. 1-minute indicators on XAUUSD are overwhelmingly dominated by mean-reverting microstructure noise.
2. When 1m EMAs, RSI, and MACD align, the move is already exhausted, inducing an immediate 0.7–1.0 ATR adverse pullback that trips 1.0 ATR stop losses.
3. Filtering for pullbacks or S/R clearance reduces total trade frequency and loss magnitude, but does not convert the core directional signal into a positive-expectancy edge under $\$0.30$ spread friction.
4. **Conclusion:** Zero candidate strategies qualified for shortlist or promotion.
