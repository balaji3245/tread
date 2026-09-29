"""
Phase 6E: Conditional Entry-State Research Engine
Runs forensic evaluation across sessions, volatility quantiles, impulse states,
score decomposition, and mechanism-driven interactions across Development & Preliminary OOS.
"""
import bisect
import gzip
import json
import logging
import math
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

from app.backtest_models import BacktestConfig, BacktestTrade
from app.backtester import BacktestReplayEngine
from app.phase6e.entry_classifier import (
    classify_impulse_pullback_state,
    classify_session_utc,
    classify_trend_range_regime,
    classify_volatility_quantile,
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

logger = logging.getLogger(__name__)

FINAL_OOS_START_TS = 1787843700  # 2026-08-27T15:15:00+00:00
FINAL_OOS_END_TS = 1790377140    # 2026-09-25T22:59:00+00:00


class ConditionalResearchEngine:
    """
    Forensic engine for Phase 6E conditional entry-state and regime expectancy analysis.
    """

    def __init__(
        self,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]],
        precomputed_signals: Dict[int, Tuple[MarketSignal, float]],
        validation_manifest: Dict[str, Any],
    ):
        self.candles_1m = candles_1m
        self.candles_5m = candles_5m
        self.precomputed_signals = precomputed_signals
        self.validation_manifest = validation_manifest
        self.c1_times = [int(c["time"]) for c in candles_1m]
        self.c5_times = [int(c["time"]) for c in candles_5m]
        self.annotated_trades: List[Dict[str, Any]] = []

    def assert_final_oos_locked(self, start_ts: int, end_ts: int):
        """Hard guard ensuring candidate evaluation never consumes Final OOS."""
        if start_ts >= FINAL_OOS_START_TS or end_ts > FINAL_OOS_START_TS:
            raise ProtectedFinalOOSAccessError(
                f"FATAL: Attempted access to protected Final OOS window ({start_ts} >= {FINAL_OOS_START_TS} or {end_ts} > {FINAL_OOS_START_TS}). Candidate evaluation is strictly blocked."
            )

    def extract_and_annotate_baseline_trades(self, baseline_trades: List[BacktestTrade]) -> List[Dict[str, Any]]:
        """
        Annotate every baseline trade with its exact causal entry state at timestamp T.
        """
        annotated = []
        
        # Precompute rolling ATRs for quantile ranking
        rolling_atrs = []
        for i in range(len(self.candles_1m)):
            if i in self.precomputed_signals:
                rolling_atrs.append(self.precomputed_signals[i][1])
            elif rolling_atrs:
                rolling_atrs.append(rolling_atrs[-1])
            else:
                rolling_atrs.append(1.50)

        for idx, t in enumerate(baseline_trades):
            e_time = t.entry_time
            e_idx = bisect.bisect_left(self.c1_times, e_time)
            if e_idx >= len(self.candles_1m) or self.c1_times[e_idx] != e_time:
                continue

            sig_idx = e_idx - 1
            if sig_idx < 30 or sig_idx not in self.precomputed_signals:
                continue

            sig_obj, atr_val = self.precomputed_signals[sig_idx]
            sig_candle = self.candles_1m[sig_idx]
            direction = t.direction
            entry_price = t.entry_price
            sl_dist = max(0.50, atr_val * 1.0)

            # 1. Session classification
            sess_block, block_2h, hour_str, dow = classify_session_utc(e_time)

            # 2. Volatility quantile (using past 120 bars rolling)
            past_atrs = rolling_atrs[max(0, sig_idx - 120):sig_idx + 1]
            vol_quantile = classify_volatility_quantile(atr_val, past_atrs)

            # 3. Indicators at T
            ind = sig_obj.indicators
            c_close = float(sig_candle["close"])
            c_open = float(sig_candle["open"])
            c_high = float(sig_candle["high"])
            c_low = float(sig_candle["low"])
            c_body = abs(c_close - c_open)
            c_range = max(0.01, c_high - c_low)
            body_ratio = c_body / c_range

            ema21_1m = ind.ema21_1m or c_close
            ema50_1m = ind.ema50_1m or c_close
            ema50_5m = ind.ema50_5m or c_close

            # 4. Impulse state classification
            impulse_state = classify_impulse_pullback_state(
                self.candles_1m, sig_idx, direction, atr_val, ema21_1m, ema50_1m
            )

            # 5. Trend/Range regime
            dist_5m_ema50_atr = abs(c_close - ema50_5m) / max(0.1, atr_val)
            trend_regime = classify_trend_range_regime(
                sig_obj.trend_5m, sig_obj.structure_1m, dist_5m_ema50_atr, atr_val
            )

            # 6. S/R clearance
            sups = sig_obj.supportLevels
            resis = sig_obj.resistanceLevels
            if direction == "LONG":
                opp_sr = (resis[0].price - c_close) if resis else 999.0
            else:
                opp_sr = (c_close - sups[0].price) if sups else 999.0
            opp_sr_clearance_atr = opp_sr / max(0.1, atr_val)

            # 7. Excursions & outcome group
            forward_candles = self.candles_1m[e_idx: min(len(self.candles_1m), e_idx + 60)]
            cum_mae = 0.0
            cum_mfe = 0.0
            mae_1m = 0.0
            mae_3m = 0.0

            for step, fc in enumerate(forward_candles):
                h = float(fc["high"])
                l = float(fc["low"])
                adv = max(0.0, entry_price - l) if direction == "LONG" else max(0.0, h - entry_price)
                fav = max(0.0, h - entry_price) if direction == "LONG" else max(0.0, entry_price - l)
                cum_mae = max(cum_mae, adv)
                cum_mfe = max(cum_mfe, fav)
                if step == 0: mae_1m = cum_mae / sl_dist
                if step == 2: mae_3m = cum_mae / sl_dist

            full_mfe_r = cum_mfe / sl_dist
            full_mae_r = cum_mae / sl_dist

            # Grouping
            if t.r_multiple > 0 and full_mae_r <= 0.5:
                forensic_group = "GROUP_A_CLEAN_WIN"
            elif t.r_multiple < 0 and t.holding_minutes <= 3 and full_mfe_r >= 1.0:
                forensic_group = "GROUP_B_EARLY_REV"
            elif t.r_multiple < 0 and full_mfe_r < 1.0:
                forensic_group = "GROUP_C_FAILURE"
            elif t.r_multiple > 0:
                forensic_group = "OTHER_WIN"
            else:
                forensic_group = "OTHER_LOSS"

            # 8. Score component breakdown (Boolean flags)
            comp_trend_5m = bool(sig_obj.trend_5m == ("BULLISH" if direction == "LONG" else "BEARISH"))
            comp_struct_1m = bool(sig_obj.structure_1m == ("BULLISH" if direction == "LONG" else "BEARISH"))
            comp_ema9_21 = bool(
                (ind.ema9_1m > ind.ema21_1m) if direction == "LONG" and ind.ema9_1m and ind.ema21_1m
                else (ind.ema9_1m < ind.ema21_1m if ind.ema9_1m and ind.ema21_1m else False)
            )
            comp_macd = bool(
                (ind.macdHist_1m > 0) if direction == "LONG" and ind.macdHist_1m is not None
                else (ind.macdHist_1m < 0 if ind.macdHist_1m is not None else False)
            )
            comp_rsi = bool(
                (40.0 <= ind.rsi_1m <= 68.0) if direction == "LONG" and ind.rsi_1m is not None
                else (32.0 <= ind.rsi_1m <= 60.0 if ind.rsi_1m is not None else False)
            )
            comp_sr_holding = bool(
                (c_close - sups[0].price <= atr_val * 1.5) if direction == "LONG" and sups
                else ((resis[0].price - c_close <= atr_val * 1.5) if direction == "SHORT" and resis else False)
            )
            comp_above_ema21 = bool(
                (c_close >= ema21_1m) if direction == "LONG" else (c_close <= ema21_1m)
            )

            record = {
                "trade_idx": idx,
                "entry_time": e_time,
                "direction": direction,
                "r_multiple": t.r_multiple,
                "holding_minutes": t.holding_minutes,
                "exit_reason": t.exit_reason,
                "atr_val": atr_val,
                "score": sig_obj.strength,
                "session_block": sess_block.value,
                "block_2h": block_2h,
                "hour_str": hour_str,
                "day_of_week": dow,
                "volatility_quantile": vol_quantile.value,
                "impulse_state": impulse_state.value,
                "trend_regime": trend_regime.value,
                "opp_sr_clearance_atr": opp_sr_clearance_atr,
                "body_ratio": body_ratio,
                "mae_1m": mae_1m,
                "mae_3m": mae_3m,
                "full_mae_r": full_mae_r,
                "full_mfe_r": full_mfe_r,
                "forensic_group": forensic_group,
                "comp_trend_5m": comp_trend_5m,
                "comp_struct_1m": comp_struct_1m,
                "comp_ema9_21": comp_ema9_21,
                "comp_macd": comp_macd,
                "comp_rsi": comp_rsi,
                "comp_sr_holding": comp_sr_holding,
                "comp_above_ema21": comp_above_ema21,
            }
            annotated.append(record)

        self.annotated_trades = annotated
        return annotated

    def compute_bucket_metrics(self, trades: List[Dict[str, Any]], bucket_name: str, total_universe: int) -> ConditionalBucketMetrics:
        """Compute complete forensic metrics for a given subset of trades."""
        n = len(trades)
        if n == 0:
            return ConditionalBucketMetrics(
                bucket_name=bucket_name,
                trade_count=0,
                trade_share_pct=0.0,
                win_count=0,
                loss_count=0,
                win_rate_pct=0.0,
                total_net_r=0.0,
                average_r=0.0,
                median_r=0.0,
                profit_factor=0.0,
                gross_profit_r=0.0,
                gross_loss_r=0.0,
                mean_mae_r=0.0,
                mean_mfe_r=0.0,
                early_stop_rate_pct=0.0,
                reach_1r_mfe_pct=0.0,
                instant_stop_rate_pct=0.0,
            )

        wins = sum(1 for t in trades if t["r_multiple"] > 0)
        losses = sum(1 for t in trades if t["r_multiple"] < 0)
        net_r = sum(t["r_multiple"] for t in trades)
        gp = sum(t["r_multiple"] for t in trades if t["r_multiple"] > 0)
        gl = sum(abs(t["r_multiple"]) for t in trades if t["r_multiple"] < 0)
        pf = (gp / gl) if gl > 0 else 0.0

        r_vals = [t["r_multiple"] for t in trades]
        mae_vals = [t["full_mae_r"] for t in trades]
        mfe_vals = [t["full_mfe_r"] for t in trades]

        early_stops = sum(1 for t in trades if t["holding_minutes"] <= 3 and t["r_multiple"] < 0)
        instant_stops = sum(1 for t in trades if t["mae_1m"] >= 1.0)
        reach_1r = sum(1 for t in trades if t["full_mfe_r"] >= 1.0)

        return ConditionalBucketMetrics(
            bucket_name=bucket_name,
            trade_count=n,
            trade_share_pct=round(n / total_universe * 100, 2),
            win_count=wins,
            loss_count=losses,
            win_rate_pct=round(wins / n * 100, 2),
            total_net_r=round(net_r, 2),
            average_r=round(net_r / n, 3),
            median_r=round(float(np.median(r_vals)), 3),
            profit_factor=round(pf, 2),
            gross_profit_r=round(gp, 2),
            gross_loss_r=round(gl, 2),
            mean_mae_r=round(float(np.mean(mae_vals)), 3),
            mean_mfe_r=round(float(np.mean(mfe_vals)), 3),
            early_stop_rate_pct=round(early_stops / n * 100, 2),
            reach_1r_mfe_pct=round(reach_1r / n * 100, 2),
            instant_stop_rate_pct=round(instant_stops / n * 100, 2),
        )
