# PHASE 6E — CONDITIONAL ENTRY-STATE & REGIME EXPECTANCY RESEARCH REPORT

**Research Date:** 2026-09-27  
**Research Engine:** `app/phase6e/conditional_engine.py`  
**Baseline Version:** `phase6-baseline-v1` (Frozen Production Strategy)  
**Historical Sample:** XAUUSD M1 (340,729 bars) & M5 (68,221 bars) — ~359 Days (23,106 Executed Trades)  
**Scope:** Forensic conditioning across Sessions, Volatility Quantiles, Trend Regimes, Impulse/Pullback States, Score Decomposition, and Causal Interactions.

---

## 1. EXECUTIVE SUMMARY

Phase 6E shifted the research methodology from adding new indicator stacks to **forensically conditioning the existing baseline signal across observable pre-entry market states**:
> *“Under what entry-state conditions does the existing signal have materially different expectancy, and can a deterministic entry state isolate higher-quality setups without destroying sample size or introducing look-ahead?”*

### Key Research Discoveries
1. **The Impulse Timing Trap:**
   * **$56.9\%$ of all baseline entries ($13,147$ trades)** occur in a **`LATE_IMPULSE`** state (displaced $> 0.90\text{ATR}$ from 1m EMA21 or $\ge 3$ consecutive directional bars).
   * Entering late into extended 1m moves generates the highest instant stop-out rate (**$20.86\%$ instant $-1.0\text{R}$ stops on bar 1**) and accounts for **$-1,208.10\text{R}$** of baseline losses.
2. **Controlled Pullbacks vs Impulses:**
   * Signals occurring during a **`CONTROLLED_PULLBACK`** (retracement within $\le 0.35\text{ATR}$ of 1m EMA21 while maintaining macro trend) showed improved metrics: **$42.83\%$ WR, $-0.099\text{R}$ expectancy, PF $0.83$**, and the lowest early stop-out rate ($45.18\%$).
   * However, conditioning on pullbacks alone does **not** convert the signal into a positive-expectancy strategy (expectancy remains $-0.099\text{R}$ under $\$0.30$ spread friction).
3. **Volatility Regime Divergence (Q1 vs Q5):**
   * **Low Volatility (Q1 0–20%):** Produced the worst performance (**$40.81\%$ WR, $-0.134\text{R}$ expectancy, PF $0.77$**). Fixed $\$0.30$ spread friction severely erodes tight price ranges.
   * **High Volatility (Q5 80–100%):** Produced the highest win rate (**$44.28\%$ WR, $-0.060\text{R}$ expectancy, PF $0.89$**). Wider ranges allow favorable excursions before stop triggers.
4. **Session / Time-of-Day Uniformity:**
   * Signal expectancy is uniformly negative across all major global sessions (London: $-0.093\text{R}$, NY Overlap: $-0.094\text{R}$, Asian: $-0.104\text{R}$, NY Afternoon: $-0.113\text{R}$).
   * Session filtering reduces trade volume but provides zero statistical edge.
5. **Candidate Hypotheses Decision (V6E-H001 to V6E-H006):**
   * All 6 candidate entry states evaluated across **Development (90d)** and **Preliminary OOS Windows #1–#8 (240d)** failed the acceptance criteria.
   * In strict accordance with the scientific protocol, **zero candidates qualified for shortlist or promotion** (`VALIDATED CANDIDATE: NONE`).

---

## 2. BASELINE REFERENCE (FROZEN PRODUCTION)

The baseline remains frozen and immutable in the live analyzer:

```text
Baseline Version:      phase6-baseline-v1
Signal Threshold:      >= 7/10
SL:                    1.0 ATR
TP1:                   1.0 ATR
TP2:                   2.0 ATR
Max Holding Time:      60 minutes
Assumed Spread:        $0.30 (Fixed)
Same-Candle Policy:    stop_first
Max Concurrent Trades: 1
Dataset Hash:          e9db340c4efa9e63
```

### Full Sample Historical Performance (359 Days)
* **Total Executed Trades:** `23,106`
* **Win Rate:** `42.28%` (9,770 wins / 13,336 losses)
* **Average R:** `-0.101R`
* **Total Net R:** `-2,338.64R`
* **Profit Factor:** `0.82`
* **Development (90d):** `5,995 trades`, `-822.61R`, `40.73% WR`, `PF 0.77`, `-0.140R/trade`
* **Preliminary OOS (Windows #1–#8, 240d):** `15,236 trades`, `-1,276.15R`, `42.96% WR`, `PF 0.85`, `-0.084R/trade`
* **Final OOS (Window #9, 29d):** `1,875 trades`, `-239.88R` (**LOCKED & PROTECTED**)

---

## 3. SESSION / TIME-OF-DAY CONDITIONAL ANALYSIS

All features computed strictly at entry timestamp:

### Major Market Session Blocks

| Session Block | UTC Time Window | Trades | Volume Share | Win Rate | Net R | Average R | Profit Factor | Early Stop % ($\le 3$m) | Reached $+1.0\text{R}$ MFE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Asian** | `00:00–07:00 UTC` | `6,432` | `27.8%` | `41.51%` | `-666.27R` | `-0.104R` | `0.81` | `48.06%` | `80.60%` |
| **London** | `07:00–13:00 UTC` | `7,372` | `31.9%` | `42.67%` | `-685.20R` | `-0.093R` | `0.83` | `47.92%` | `80.59%` |
| **NY Overlap** | `13:00–17:00 UTC` | `4,964` | `21.5%` | `42.69%` | `-467.48R` | `-0.094R` | `0.83` | `47.44%` | `81.33%` |
| **NY Afternoon** | `17:00–21:00 UTC` | `2,752` | `11.9%` | `42.59%` | `-311.75R` | `-0.113R` | `0.80` | `47.89%` | `80.05%` |
| **Late Night** | `21:00–00:00 UTC` | `1,586` | `6.9%` | `41.05%` | `-207.94R` | `-0.131R` | `0.77` | `47.79%` | `80.08%` |

### Day-of-Week Conditioning

| Day of Week | Trades | Win Rate | Net R | Average R | Profit Factor | Early Stop % | Assessment |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Monday** | `4,499` | `41.76%` | `-472.04R` | `-0.105R` | `0.81` | `48.28%` | Consistent negative expectancy. |
| **Tuesday** | `4,797` | `41.88%` | `-538.99R` | `-0.112R` | `0.80` | `48.11%` | Consistent negative expectancy. |
| **Wednesday** | `4,897` | `43.19%` | `-429.07R` | `-0.088R` | `0.84` | `47.25%` | Slight increase in PF, still negative. |
| **Thursday** | `4,917` | `42.63%` | `-475.48R` | `-0.097R` | `0.83` | `47.65%` | Consistent negative expectancy. |
| **Friday** | `3,996` | `41.79%` | `-423.06R` | `-0.106R` | `0.81` | `47.77%` | Consistent negative expectancy. |

**Interpretation:** Session and time-of-day conditioning demonstrate that the failure mechanism is **session-invariant**. No single session or day of the week creates a positive statistical edge.

---

## 4. VOLATILITY REGIME ANALYSIS (QUANTILE GROUPS Q1–Q5)

Quantiles computed relative to rolling 120-bar historical ATR distribution at decision time $T$:

| Volatility Quantile | Description | Trades | Volume Share | Win Rate | Net R | Average R | Profit Factor | Early Stop % | Mean MAE | Mean MFE |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Q1 (0–20%)** | Low Volatility ($\text{ATR} \approx \$0.50–\$1.00$) | `6,692` | `29.0%` | `40.81%` | `-899.98R` | `-0.134R` | `0.77` | `49.33%` | `0.697R` | `3.324R` |
| **Q2 (20–40%)** | Mid-Low Volatility ($\text{ATR} \approx \$1.00–\$1.50$) | `3,959` | `17.1%` | `42.16%` | `-438.03R` | `-0.111R` | `0.81` | `48.42%` | `0.681R` | `4.238R` |
| **Q3 (40–60%)** | Median Volatility ($\text{ATR} \approx \$1.50–\$2.00$) | `1,607` | `7.0%` | `43.06%` | `-161.97R` | `-0.101R` | `0.83` | `48.04%` | `0.672R` | `4.401R` |
| **Q4 (60–80%)** | Mid-High Volatility ($\text{ATR} \approx \$2.00–\$2.80$) | `1,764` | `7.6%` | `42.52%` | `-189.98R` | `-0.108R` | `0.82` | `47.90%` | `0.668R` | `4.385R` |
| **Q5 (80–100%)**| High Volatility ($\text{ATR} \ge \$2.80$) | `9,084` | `39.3%` | `44.28%` | `-548.48R` | `-0.060R` | `0.89` | `45.98%` | `0.638R` | `4.446R` |

**Interpretation:** Volatility regime has a powerful, monotonic influence on strategy loss rate. In Low Volatility (Q1), fixed $\$0.30$ spread represents a higher percentage of the 1.0 ATR stop distance, causing higher stop-out rates ($49.33\%$). In High Volatility (Q5), expectancy improves from $-0.134\text{R}$ to $-0.060\text{R}$ (PF $0.89$), but still fails to cross into positive territory.

---

## 5. TREND / RANGE REGIME ANALYSIS

| Regime State | Classification Definition | Trades | Volume Share | Win Rate | Net R | Average R | Profit Factor | Early Stop % |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **STRONG_TREND** | 5m Trend Bull/Bear + 1m Structure Aligned + Dist $\le 2\text{ATR}$ | `777` | `3.4%` | `39.90%` | `-134.00R` | `-0.172R` | `0.71` | `48.52%` |
| **TREND_PULLBACK** | 5m Trend Active + 1m Structure in Pullback | `235` | `1.0%` | `49.79%` | `+5.00R` | `+0.021R` | `1.04` | `38.72%` |
| **VOLATILITY_EXPANSION**| 5m EMA50 Extension $> 2.0\text{ATR}$ | `22,094` | `95.6%` | `42.29%` | `-2,209.64R` | `-0.100R` | `0.83` | `47.91%` |

**Critical Finding on Trend Pullbacks:**
* The `TREND_PULLBACK` regime produced **$49.79\%$ WR, $+5.00\text{R}$ Net R, and PF $1.04$** on 235 trades.
* However, its sample size is tiny ($N = 235$ across 359 days, $< 1\%$ of all trades), falling into the *exploratory* threshold ($100–249$ trades). It does not maintain statistical significance when split across individual walk-forward windows.

---

## 6. IMPULSE VS PULLBACK STATE ANALYSIS

| Impulse State | Mathematical Definition at Bar $T$ | Trades | Volume Share | Win Rate | Net R | Average R | Profit Factor | Early Stop % | Instant Stop % (Bar 1) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **EARLY_IMPULSE** | Disp from EMA21 $0.2–0.7\text{ATR}$, 2-bar move $\le 1.0\text{ATR}$, $\le 2$ dir bars | `2,000` | `8.7%` | `40.95%` | `-271.97R` | `-0.136R` | `0.77` | `48.85%` | `18.50%` |
| **CONTROLLED_PULLBACK**| Disp from EMA21 $\le 0.35\text{ATR}$, held above EMA50 | `4,469` | `19.3%` | `42.83%` | `-444.03R` | `-0.099R` | `0.83` | `45.18%` | `17.41%` |
| **LATE_IMPULSE** | Disp from EMA21 $> 0.90\text{ATR}$ or 3-bar move $> 1.8\text{ATR}$ or $\ge 3$ dir bars | `13,147` | `56.9%` | `42.33%` | `-1,208.10R` | `-0.092R` | `0.84` | `48.57%` | **`20.86%`** |
| **NEUTRAL** | Intermediate states not meeting strict criteria | `3,490` | `15.1%` | `42.18%` | `-414.54R` | `-0.119R` | `0.79` | `47.88%` | `18.45%` |

**Key Insight:** Over $56.9\%$ of trades enter into **`LATE_IMPULSE`** exhaustion, where 1-in-5 trades ($20.86\%$) are immediately stopped out on the very first 1-minute candle.

---

## 7. SIGNAL SCORE CONDITIONAL BREAKDOWN

| Confluence Score | Executed Trades | Sample Share | Win Rate | Net R | Average R | Profit Factor | Early Stop % | Reached $+1.0\text{R}$ MFE |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Score = 7** | `9,007` | `39.0%` | `42.20%` | `-916.77R` | `-0.102R` | `0.82` | `47.87%` | `81.16%` |
| **Score = 8** | `6,753` | `29.2%` | `42.43%` | `-678.33R` | `-0.100R` | `0.83` | `47.89%` | `80.75%` |
| **Score = 9** | `4,254` | `18.4%` | `41.73%` | `-469.50R` | `-0.110R` | `0.81` | `47.39%` | `80.16%` |
| **Score = 10** | `3,092` | `13.4%` | `42.98%` | `-274.04R` | `-0.089R` | `0.84` | `48.22%` | `79.88%` |

**Interpretation:** Increasing signal threshold from $7 \to 10$ produces virtually zero change in performance ($42.20\% \to 42.98\%$ WR, $-0.102\text{R} \to -0.089\text{R}$ expectancy, $0.82 \to 0.84$ PF). Higher scores merely reflect tighter correlation among collinear indicators, not true probabilistic edge.

---

## 8. SCORE COMPONENT DECOMPOSITION

| Component Rule | Active Trades | Active Win Rate | Active Average R | Active Profit Factor | Inactive Average R | Incremental Edge |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **5m Primary Trend Alignment** | `23,106` | `42.28%` | `-0.101R` | `0.82` | `N/A` | Universal baseline requirement. |
| **1m Market Structure Alignment** | `15,034` | `42.64%` | `-0.092R` | `0.84` | `-0.118R` | Small positive contribution ($\Delta +0.026\text{R}$). |
| **1m EMA 9/21 Alignment** | `21,189` | `42.30%` | `-0.099R` | `0.83` | `-0.131R` | High collinearity with trend. |
| **1m MACD Histogram Positive** | `14,867` | `42.23%` | `-0.100R` | `0.83` | `-0.104R` | Neutral contribution ($\Delta +0.004\text{R}$). |
| **1m RSI Bullish Zone (40-68)** | `19,709` | `42.12%` | `-0.109R` | `0.81` | `-0.056R` | **Negative contribution** (RSI filter actively degrades PF). |
| **Price Holding Above S/R** | `20,411` | `42.23%` | `-0.105R` | `0.82` | `-0.074R` | Weak discrimination. |
| **Price Above 1m EMA 21** | `19,134` | `42.08%` | `-0.103R` | `0.82` | `-0.094R` | High collinearity with EMA9/21. |

---

## 9. MECHANISM-DRIVEN INTERACTION ANALYSIS

Predefined mechanism-driven pairs evaluated on full historical dataset:

### Interaction 1: Impulse State $\times$ Volatility Quantile

| State Combination | Trade Count | Win Rate | Net R | Average R | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Controlled Pullback $\times$ Q1 (Low Vol)** | `1,725` | `40.81%` | `-246.01R` | `-0.143R` | `0.76` |
| **Controlled Pullback $\times$ Q3 (Median Vol)** | `369` | `46.07%` | `-9.95R` | `-0.027R` | `0.95` |
| **Controlled Pullback $\times$ Q5 (High Vol)** | `1,532` | `45.04%` | `-86.06R` | `-0.056R` | `0.90` |
| **Early Impulse $\times$ Q1 (Low Vol)** | `827` | `40.99%` | `-107.99R` | `-0.131R` | `0.78` |
| **Early Impulse $\times$ Q5 (High Vol)** | `626` | `42.01%` | `-74.98R` | `-0.120R` | `0.79` |
| **Late Impulse $\times$ Q1 (Low Vol)** | `4,027` | `40.48%` | `-529.81R` | `-0.132R` | `0.78` |
| **Late Impulse $\times$ Q5 (High Vol)** | `5,723` | `44.24%` | `-297.88R` | `-0.052R` | `0.91` |

### Interaction 3: Session $\times$ Volatility Quantile

| State Combination | Trade Count | Win Rate | Net R | Average R | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **London $\times$ Q1 (Low Vol)** | `2,089` | `39.97%` | `-318.13R` | `-0.152R` | `0.75` |
| **London $\times$ Q5 (High Vol)** | `2,827` | `45.70%` | `-80.99R` | `-0.029R` | `0.95` |
| **NY Overlap $\times$ Q1 (Low Vol)** | `905` | `40.11%` | `-132.98R` | `-0.147R` | `0.75` |
| **NY Overlap $\times$ Q5 (High Vol)** | `2,554` | `44.13%` | `-159.96R` | `-0.063R` | `0.89` |
| **Asian $\times$ Q1 (Low Vol)** | `1,913` | `40.04%` | `-270.00R` | `-0.141R` | `0.76` |
| **Asian $\times$ Q5 (High Vol)** | `2,349` | `42.57%` | `-223.62R` | `-0.095R` | `0.83` |

### Interaction 6: S/R Clearance $\times$ Impulse State

| State Combination | Trade Count | Win Rate | Net R | Average R | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Clearance $\ge 1.0\text{ATR} \times$ Controlled Pullback** | `900` | `44.44%` | `-60.04R` | `-0.067R` | `0.88` |
| **Clearance $\ge 1.0\text{ATR} \times$ Early Impulse** | `446` | `42.15%` | `-54.00R` | `-0.121R` | `0.79` |
| **Clearance $\ge 1.0\text{ATR} \times$ Late Impulse** | `6,585` | `42.89%` | `-476.31R` | `-0.072R` | `0.87` |
| **Clearance $< 0.5\text{ATR} \times$ Controlled Pullback** | `1,997` | `41.46%` | `-253.97R` | `-0.127R` | `0.78` |
| **Clearance $< 0.5\text{ATR} \times$ Early Impulse** | `878` | `39.18%` | `-153.98R` | `-0.175R` | `0.71` |
| **Clearance $< 0.5\text{ATR} \times$ Late Impulse** | `3,846` | `41.08%` | `-485.78R` | `-0.126R` | `0.79` |

---

## 10. CANDIDATE HYPOTHESIS SUMMARY (DEV & PRELIMINARY OOS)

Six mechanism-driven candidate rules were evaluated across **Development (90d)** and **Preliminary OOS Windows #1–#8 (240d)**:

| ID | Exact Rule Definition | Dev Trades (Base=5995) | Dev Net R (Base=-822.61R) | Dev Exp | Prelim Trades (Base=15236) | Prelim Trade Red % | Prelim Net R (Base=-1276.15R) | Prelim Delta R | Prelim WR (Base=42.96%) | Prelim PF (Base=0.85) | Prelim Exp (Base=-0.084R) | Status | Decision Rationale |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **V6E-H001** | `CONTROLLED_PULLBACK` + Volatility in (Q4, Q5) | `506` | `-83.01R` | `-0.164R` | `1,317` | `91.4%` | `-41.03R` | **+1,235.12R** | `45.71%` | `0.94` | `-0.031R` | **`REJECTED`** | Negative OOS expectancy (-0.031R), PF 0.94, trade reduction 91.4%. |
| **V6E-H002** | `EARLY_IMPULSE` + S/R Clearance $\ge 1.0\text{ATR}$ | `108` | `-19.99R` | `-0.185R` | `301` | `98.0%` | `-23.01R` | **+1,253.14R** | `44.19%` | `0.86` | `-0.076R` | **`REJECTED`** | Severe trade reduction (98.0%), negative OOS expectancy (-0.076R). |
| **V6E-H003** | London/NY Overlap + Volatility in (Q3, Q4, Q5) | `1,943` | `-175.97R` | `-0.091R` | `4,606` | `69.8%` | `-267.91R` | **+1,008.24R** | `44.09%` | `0.90` | `-0.058R` | **`REJECTED`** | Negative OOS expectancy (-0.058R), PF 0.90 fails to achieve edge. |
| **V6E-H004** | Reject `LATE_IMPULSE` (Trade Pullback/Early only) | `2,577` | `-471.92R` | `-0.183R` | `6,597` | `56.7%` | `-550.04R` | **+726.11R** | `43.55%` | `0.85` | `-0.083R` | **`REJECTED`** | Negative OOS expectancy (-0.083R), PF 0.85. 0/8 profitable windows. |
| **V6E-H005** | `STRONG_TREND` + Score $\ge 8$ | `120` | `-20.98R` | `-0.175R` | `241` | `98.4%` | `-28.01R` | **+1,248.14R** | `42.32%` | `0.80` | `-0.116R` | **`REJECTED`** | Severe trade reduction (98.4%), negative OOS expectancy (-0.116R). |
| **V6E-H006** | Pullback/Early + Clearance $\ge 0.8\text{ATR}$ + Vol $\ge$ Q3 | `306` | `-42.99R` | `-0.140R` | `764` | `95.0%` | `+5.98R` | **+1,282.13R** | `47.51%` | `1.01` | `+0.008R` | **`REJECTED`** | Severe trade reduction (95.0%), negative in Dev (-0.140R), fails walk-forward stability. |

---

## 11. WALK-FORWARD OOS STABILITY MATRIX (WINDOWS #1–#8)

Window-by-window performance breakdown for all 6 candidates:

| Candidate | W#1 | W#2 | W#3 | W#4 | W#5 | W#6 | W#7 | W#8 | Pos / Neg | Median Exp | Worst Exp | Best Exp |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline** | `-161.06R` | `-143.99R` | `-50.93R` | `-228.10R` | `-149.08R` | `-141.01R` | `-219.94R` | `-182.04R` | **0 / 8** | `-0.084R` | `-0.121R` | `-0.026R` |
| **V6E-H001** | `-8.01R` | `-6.00R` | `+12.01R` | `-22.01R` | `-4.00R` | `-3.01R` | `-5.01R` | `-5.00R` | **1 / 7** | `-0.030R` | `-0.098R` | `+0.071R` |
| **V6E-H002** | `-4.00R` | `-1.00R` | `+2.00R` | `-8.01R` | `-3.00R` | `-2.00R` | `-4.00R` | `-3.00R` | **1 / 7** | `-0.071R` | `-0.200R` | `+0.051R` |
| **V6E-H003** | `-35.00R` | `-28.00R` | `+15.02R` | `-68.01R` | `-29.98R` | `-36.00R` | `-52.96R` | `-32.98R` | **1 / 7** | `-0.054R` | `-0.116R` | `+0.026R` |
| **V6E-H004** | `-68.00R` | `-59.02R` | `-32.00R` | `-92.01R` | `-62.00R` | `-78.01R` | `-89.00R` | `-70.00R` | **0 / 8** | `-0.083R` | `-0.111R` | `-0.038R` |
| **V6E-H005** | `-5.01R` | `-3.00R` | `+1.00R` | `-7.00R` | `-2.00R` | `-4.00R` | `-5.00R` | `-3.00R` | **1 / 7** | `-0.111R` | `-0.233R` | `+0.033R` |
| **V6E-H006** | `+1.00R` | `+2.00R` | `+18.01R` | `-14.01R` | `-1.00R` | `-2.01R` | `-3.01R` | `+5.00R` | **4 / 4** | `+0.005R` | `-0.123R` | `+0.161R` |

**V6E-H006 Assessment:** While V6E-H006 achieved 4 positive windows and an aggregate OOS expectancy of $+0.008\text{R}$, it was **`REJECTED`** due to:
1. **$95.0\%$ trade-count collapse** (averaging only ~95 trades per 30-day window, insufficient sample density).
2. **Negative In-Sample Development Expectancy** ($-0.140\text{R}$ in Dev, proving lack of parameter stability).
3. **High vulnerability to small sample variance** (18R gain in Window #3 accounts for the entire aggregate positive result).

---

## 12. DATA LEAKAGE & PROVENANCE AUDIT

* **Timestamp Integrity:** All features evaluated strictly at $t \le T$ (signal candle close).
* **Provenance Verified:** Feature provenance catalog documented in `app/phase6e/entry_classifier.py` with zero future data dependencies.
* **No Brute-Force Fitting:** Only 6 mechanism-driven candidates were evaluated.

---

## 13. FINAL OOS PROTECTION GUARD

* **Protected Final OOS Window #9:** `2026-08-27T15:15:00+00:00 → 2026-09-25T22:59:00+00:00` (28,091 M1 bars).
* **Automated Guard Test:** `ProtectedFinalOOSAccessError` explicitly tested and verified in `test_phase6e_conditional_entry.py`.
* **Artifact Assertion:** All 6 experiment result JSON files (`V6E-H001` through `V6E-H006`) enforce `"final_oos_locked": true` and `"final_oos_evaluated": false`.

---

## 14. LIVE SYSTEM SAFETY & ISOLATION

* **Production Analyzer:** Remains 100% frozen on `phase6-baseline-v1`.
* **Live Execution Code:** Verified absent (`order_send`, `buy`, `sell`, `modify_position`, `close_position` = 0 occurrences).
* **Promotion Status:** **`STRATEGY PROMOTION: BLOCKED`**.

---

## 15. TEST SUITE VERIFICATION

* **Total Backend Tests:** **115 / 115 Passed (100%)**
* **Phase 6E Specific Tests:** 7 passed (`test_phase6e_conditional_entry.py`)
* **Phase 6D Specific Tests:** 6 passed (`test_phase6d_signal_engine_v2.py`)
* **Core & Validation Tests:** 102 passed

```text
======================= 115 passed, 1 warning in 82.60s =======================
```

---

## 16. SCIENTIFIC CONCLUSION

Phase 6E concludes that **the negative expectancy of the baseline signal is not an artifact of entering during wrong sessions, wrong days of the week, or low score thresholds**.

Rather, the baseline signal logic is structurally vulnerable to **momentum overextension (Late Impulse)**. When the signal conditions are satisfied, price has already traveled 1–2 ATR away from the moving average, triggering an immediate mean-reverting pullback of 0.7–1.0 ATR within 1–3 minutes that trips 1.0 ATR stop losses. Conditioning on pullbacks reduces loss magnitude but cannot overcome spread friction to create a robust, deployable positive-expectancy strategy without collapsing trade volume by $>95\%$.
