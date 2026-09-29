import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.backtest_models import BacktestConfig, BacktestTrade
from app.backtester import BacktestReplayEngine
from app.validation.validation_models import (
    PeriodMetricSummary,
    WalkForwardWindowResult,
)
from app.validation.validation_statistics import summarize_trades_slice

logger = logging.getLogger(__name__)


def generate_walk_forward_slices(
    start_ts: int,
    end_ts: int,
    train_days: int = 90,
    validation_days: int = 30,
    step_days: int = 30
) -> List[Tuple[int, int, int, int]]:
    """
    Generate chronological (train_start, train_end, val_start, val_end) timestamp tuples.
    Guarantees strict forward progression without future look-ahead.
    """
    total_seconds = end_ts - start_ts
    train_sec = train_days * 86400
    val_sec = validation_days * 86400
    step_sec = step_days * 86400

    windows: List[Tuple[int, int, int, int]] = []

    # If dataset is shorter than train + validation days, generate adapted proportional slices
    if total_seconds < (train_sec + val_sec):
        # Proportional 70% train / 30% validation
        split_ts = start_ts + int(total_seconds * 0.70)
        if (split_ts - start_ts) >= 3600 and (end_ts - split_ts) >= 1800:
            windows.append((start_ts, split_ts, split_ts, end_ts))
        return windows

    cur_start = start_ts
    while True:
        train_start = cur_start
        train_end = train_start + train_sec
        val_start = train_end
        val_end = val_start + val_sec

        if val_end > end_ts:
            # If remaining validation period has at least half validation_days or 24h, include final window
            if (end_ts - val_start) >= max(86400, val_sec // 2):
                windows.append((train_start, train_end, val_start, end_ts))
            break

        windows.append((train_start, train_end, val_start, val_end))
        cur_start += step_sec

    return windows


def _slice_candles_with_warmup(
    candles_1m: List[Dict[str, Any]],
    candles_5m: List[Dict[str, Any]],
    target_start_ts: int,
    target_end_ts: int,
    warmup_1m_bars: int = 120,
    warmup_5m_bars: int = 40
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Slice candles for a specific target window while including preceding warm-up bars.
    Warm-up bars allow indicators (EMA 50, RSI 14, MACD, ATR 14) to initialize before target_start_ts.
    """
    first_1m_idx = 0
    for idx, c in enumerate(candles_1m):
        if int(c["time"]) >= target_start_ts:
            first_1m_idx = idx
            break
    start_1m = max(0, first_1m_idx - warmup_1m_bars)
    sub_1m = [c for c in candles_1m[start_1m:] if int(c["time"]) <= target_end_ts]

    first_5m_idx = 0
    for idx, c in enumerate(candles_5m):
        if int(c["time"]) >= target_start_ts:
            first_5m_idx = idx
            break
    start_5m = max(0, first_5m_idx - warmup_5m_bars)
    sub_5m = [c for c in candles_5m[start_5m:] if int(c["time"]) <= target_end_ts]

    return sub_1m, sub_5m


def run_walk_forward_validation(
    candles_1m: List[Dict[str, Any]],
    candles_5m: List[Dict[str, Any]],
    base_config: BacktestConfig,
    train_days: int = 90,
    validation_days: int = 30,
    step_days: int = 30,
    all_trades: Optional[List[BacktestTrade]] = None
) -> List[WalkForwardWindowResult]:
    """
    Execute chronological Walk-Forward analysis over historical candle streams.
    """
    if not candles_1m or not candles_5m:
        return []

    start_ts = int(candles_1m[0]["time"])
    end_ts = int(candles_1m[-1]["time"])

    windows = generate_walk_forward_slices(
        start_ts=start_ts,
        end_ts=end_ts,
        train_days=train_days,
        validation_days=validation_days,
        step_days=step_days
    )

    results: List[WalkForwardWindowResult] = []

    for w_idx, (t_start, t_end, v_start, v_end) in enumerate(windows, start=1):
        if all_trades is not None:
            train_trades = [t for t in all_trades if t.entry_time >= t_start and t.entry_time <= t_end]
            train_metrics = summarize_trades_slice(
                trades=train_trades,
                signals_count=len(train_trades),
                period_name=f"Train Window #{w_idx}",
                start_ts=t_start,
                end_ts=t_end,
                initial_capital=base_config.initial_capital,
                risk_per_trade_usd=base_config.risk_per_trade_usd
            )
            val_trades = [t for t in all_trades if t.entry_time >= v_start and t.entry_time <= v_end]
            val_metrics = summarize_trades_slice(
                trades=val_trades,
                signals_count=len(val_trades),
                period_name=f"OOS Validation Window #{w_idx}",
                start_ts=v_start,
                end_ts=v_end,
                initial_capital=base_config.initial_capital,
                risk_per_trade_usd=base_config.risk_per_trade_usd
            )
        else:
            # 1. Run Train Window Replay
            train_1m, train_5m = _slice_candles_with_warmup(candles_1m, candles_5m, t_start, t_end)
            if len(train_1m) >= 40 and len(train_5m) >= 15:
                train_engine = BacktestReplayEngine(config=base_config)
                train_resp = train_engine.run_backtest(candles_1m=train_1m, candles_5m=train_5m)
                train_trades = [t for t in train_resp.trades if t.entry_time >= t_start and t.entry_time <= t_end]
                train_metrics = summarize_trades_slice(
                    trades=train_trades,
                    signals_count=train_resp.statistics.total_signals,
                    period_name=f"Train Window #{w_idx}",
                    start_ts=t_start,
                    end_ts=t_end,
                    initial_capital=base_config.initial_capital,
                    risk_per_trade_usd=base_config.risk_per_trade_usd
                )
            else:
                train_metrics = summarize_trades_slice(
                    trades=[],
                    signals_count=0,
                    period_name=f"Train Window #{w_idx}",
                    start_ts=t_start,
                    end_ts=t_end,
                    initial_capital=base_config.initial_capital,
                    risk_per_trade_usd=base_config.risk_per_trade_usd
                )

            # 2. Run Out-Of-Sample Validation Window Replay
            val_1m, val_5m = _slice_candles_with_warmup(candles_1m, candles_5m, v_start, v_end)
            if len(val_1m) >= 40 and len(val_5m) >= 15:
                val_engine = BacktestReplayEngine(config=base_config)
                val_resp = val_engine.run_backtest(candles_1m=val_1m, candles_5m=val_5m)
                val_trades = [t for t in val_resp.trades if t.entry_time >= v_start and t.entry_time <= v_end]
                val_metrics = summarize_trades_slice(
                    trades=val_trades,
                    signals_count=val_resp.statistics.total_signals,
                    period_name=f"OOS Validation Window #{w_idx}",
                    start_ts=v_start,
                    end_ts=v_end,
                    initial_capital=base_config.initial_capital,
                    risk_per_trade_usd=base_config.risk_per_trade_usd
                )
            else:
                val_metrics = summarize_trades_slice(
                    trades=[],
                    signals_count=0,
                    period_name=f"OOS Validation Window #{w_idx}",
                    start_ts=v_start,
                    end_ts=v_end,
                    initial_capital=base_config.initial_capital,
                    risk_per_trade_usd=base_config.risk_per_trade_usd
                )

        results.append(
            WalkForwardWindowResult(
                window_index=w_idx,
                train_start_iso=datetime.fromtimestamp(t_start, tz=timezone.utc).isoformat(),
                train_end_iso=datetime.fromtimestamp(t_end, tz=timezone.utc).isoformat(),
                train_metrics=train_metrics,
                validation_start_iso=datetime.fromtimestamp(v_start, tz=timezone.utc).isoformat(),
                validation_end_iso=datetime.fromtimestamp(v_end, tz=timezone.utc).isoformat(),
                validation_metrics=val_metrics,
                is_final_oos=(w_idx == len(windows))
            )
        )

    return results
