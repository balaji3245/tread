import bisect
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.backtest_models import (
    BacktestConfig,
    BacktestResponse,
    BacktestTrade,
    HistoricalCandle,
)
from app.backtest_statistics import compute_statistics, determine_session
from app.indicators import get_latest_atr
from app.signal_engine import SignalEngine
from app.signal_models import MarketSignal

logger = logging.getLogger(__name__)

# Local in-memory dataset cache: (symbol, timeframe, start_t, end_t) -> List[Dict]
_CANDLE_CACHE: Dict[Tuple[str, str, int, int], List[Dict[str, Any]]] = {}


def parse_date_to_timestamp(date_str: Optional[str], default_ts: int) -> int:
    """Safely parse ISO date string, YYYY-MM-DD, or integer timestamp to Unix seconds."""
    if not date_str:
        return default_ts

    try:
        # Numeric timestamp
        if str(date_str).isdigit():
            ts = int(date_str)
            return ts // 1000 if ts > 10_000_000_000 else ts

        # ISO format or YYYY-MM-DD
        dt_str = str(date_str).replace("Z", "+00:00")
        if "T" in dt_str:
            dt = datetime.fromisoformat(dt_str)
        else:
            dt = datetime.strptime(dt_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception as e:
        logger.warning("Could not parse date '%s' (%s), using default timestamp %d", date_str, e, default_ts)
        return default_ts


class BacktestReplayEngine:
    """
    Deterministic chronological historical backtesting replay engine for XAUUSD.
    Guarantees strict zero look-ahead bias and reuses the exact live SignalEngine rules.
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.signal_engine = SignalEngine(
            setup_threshold=config.signal_threshold,
            max_strength=10
        )

    def precompute_signals(
        self,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]]
    ) -> Dict[int, Tuple[MarketSignal, float]]:
        """
        Precompute all signals and ATR values across the historical series for fast sensitivity/OOS iterations.
        """
        c5m_times = [int(c["time"]) for c in candles_5m]
        signals: Dict[int, Tuple[MarketSignal, float]] = {}
        for i in range(30, len(candles_1m) - 1):
            current_1m = candles_1m[i]
            t_1m = int(current_1m["time"])
            past_1m_slice = candles_1m[max(0, i - 120):i + 1]
            max_closed_5m_open = t_1m + 60 - 300
            idx_5m = bisect.bisect_right(c5m_times, max_closed_5m_open)
            past_5m_slice = candles_5m[max(0, idx_5m - 60):idx_5m]

            if len(past_1m_slice) >= 20 and len(past_5m_slice) >= 10:
                current_bar_tick = {
                    "bid": float(current_1m["close"]),
                    "ask": float(current_1m["close"]),
                    "timestamp": t_1m * 1000
                }
                sig = self.signal_engine.analyze(
                    candles_1m=past_1m_slice,
                    candles_5m=past_5m_slice,
                    current_tick=current_bar_tick
                )
                if sig.type in ["LONG_SETUP", "SHORT_SETUP"]:
                    atr_val = sig.indicators.atr_1m or get_latest_atr(past_1m_slice, 14) or 1.50
                    signals[i] = (sig, atr_val)
        return signals

    def run_backtest(
        self,
        candles_1m: List[Dict[str, Any]],
        candles_5m: List[Dict[str, Any]],
        precomputed_signals: Optional[Dict[int, Tuple[MarketSignal, float]]] = None
    ) -> BacktestResponse:
        """
        Execute full historical simulation over synchronized 1m and 5m candle sets.
        """
        if len(candles_1m) < 40 or len(candles_5m) < 15:
            raise ValueError(
                f"Insufficient historical candles for backtesting. Provided 1m: {len(candles_1m)}, 5m: {len(candles_5m)} (minimum required: 40 1m and 15 5m bars)."
            )

        # Ensure sorted chronologically
        candles_1m = sorted(candles_1m, key=lambda x: int(x["time"]))
        candles_5m = sorted(candles_5m, key=lambda x: int(x["time"]))

        trades: List[BacktestTrade] = []
        total_signals = 0

        # State tracking
        active_trade: Optional[Dict[str, Any]] = None
        pending_signal: Optional[Dict[str, Any]] = None

        # Pre-index 5m bars for fast binary or chronological lookup
        c5m_times = [int(c["time"]) for c in candles_5m]

        # Warmup period: require at least 30 1m bars and 10 5m bars before first evaluation
        start_idx = 30
        spread_cost = self.config.assumed_spread if self.config.execution_mode == "fixed_spread" else 0.0

        for i in range(start_idx, len(candles_1m)):
            current_1m = candles_1m[i]
            t_1m = int(current_1m["time"])

            # -------------------------------------------------------------
            # Step A: Check if a pending signal from previous bar enters NOW at OPEN
            # -------------------------------------------------------------
            if pending_signal is not None and active_trade is None:
                entry_candle = current_1m
                sig = pending_signal["signal"]
                direction = "LONG" if sig.type == "LONG_SETUP" else "SHORT"

                # Base entry price is open of this candle
                raw_open = float(entry_candle["open"])
                spread_val = (
                    float(entry_candle.get("spread", spread_cost))
                    if self.config.execution_mode == "historical_spread" and entry_candle.get("spread") is not None
                    else spread_cost
                )

                if direction == "LONG":
                    entry_price = round(raw_open + spread_val, 2)
                    atr_val = pending_signal["atr"]
                    sl_dist = max(0.50, round(atr_val * self.config.sl_atr_multiplier, 2))
                    tp1_dist = round(atr_val * self.config.tp1_atr_multiplier, 2)
                    tp2_dist = round(atr_val * self.config.tp2_atr_multiplier, 2)
                    stop_loss = round(entry_price - sl_dist, 2)
                    take_profit_1 = round(entry_price + tp1_dist, 2)
                    take_profit_2 = round(entry_price + tp2_dist, 2)
                else:
                    entry_price = round(raw_open - spread_val, 2)
                    atr_val = pending_signal["atr"]
                    sl_dist = max(0.50, round(atr_val * self.config.sl_atr_multiplier, 2))
                    tp1_dist = round(atr_val * self.config.tp1_atr_multiplier, 2)
                    tp2_dist = round(atr_val * self.config.tp2_atr_multiplier, 2)
                    stop_loss = round(entry_price + sl_dist, 2)
                    take_profit_1 = round(entry_price - tp1_dist, 2)
                    take_profit_2 = round(entry_price - tp2_dist, 2)

                active_trade = {
                    "id": str(uuid.uuid4())[:8],
                    "direction": direction,
                    "signal_time": pending_signal["signal_time"],
                    "entry_time": t_1m,
                    "signal_strength": sig.strength,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit_1": take_profit_1,
                    "take_profit_2": take_profit_2,
                    "sl_dist": sl_dist,
                    "atr": pending_signal["atr"],
                    "entry_reason": sig.reasons[0] if sig.reasons else "Rule confluence",
                    "market_regime": sig.trend_5m,
                    "session": determine_session(t_1m),
                    "peak_mfe_price": 0.0,
                    "peak_mae_price": 0.0,
                    "peak_mfe_r": 0.0,
                    "peak_mae_r": 0.0
                }
                pending_signal = None

            # -------------------------------------------------------------
            # Step B: If trade is active, evaluate exit conditions on this bar
            # -------------------------------------------------------------
            if active_trade is not None:
                c_high = float(current_1m["high"])
                c_low = float(current_1m["low"])
                c_close = float(current_1m["close"])
                dir_t = active_trade["direction"]
                sl = active_trade["stop_loss"]
                tp1 = active_trade["take_profit_1"]
                tp2 = active_trade["take_profit_2"]
                entry_p = active_trade["entry_price"]
                sl_dist = active_trade["sl_dist"]
                atr_t = active_trade.get("atr", 1.50)
                holding_mins = (t_1m - active_trade["entry_time"]) / 60.0

                # 1. Update dynamic excursions
                if dir_t == "LONG":
                    bar_fav = max(0.0, c_high - entry_p)
                    bar_adv = max(0.0, entry_p - c_low)
                else:
                    bar_fav = max(0.0, entry_p - c_low)
                    bar_adv = max(0.0, c_high - entry_p)

                active_trade["peak_mfe_price"] = max(active_trade["peak_mfe_price"], bar_fav)
                active_trade["peak_mae_price"] = max(active_trade["peak_mae_price"], bar_adv)
                active_trade["peak_mfe_r"] = active_trade["peak_mfe_price"] / sl_dist if sl_dist > 0 else 0.0
                active_trade["peak_mae_r"] = active_trade["peak_mae_price"] / sl_dist if sl_dist > 0 else 0.0

                peak_mfe_r = active_trade["peak_mfe_r"]

                # 2. Dynamic Stop Loss Updates (Zero Future Information: uses only past/intrabar prices)
                # Breakeven Rule
                if self.config.breakeven_trigger_r is not None and peak_mfe_r >= self.config.breakeven_trigger_r:
                    if dir_t == "LONG":
                        sl = max(sl, entry_p)
                    else:
                        sl = min(sl, entry_p)
                    active_trade["stop_loss"] = sl

                # Trailing Stop Rule
                if (self.config.trailing_trigger_r is not None and
                    self.config.trailing_stop_atr is not None and
                    peak_mfe_r >= self.config.trailing_trigger_r):
                    if dir_t == "LONG":
                        trail_sl = round(c_high - (self.config.trailing_stop_atr * atr_t), 2)
                        sl = max(sl, trail_sl)
                    else:
                        trail_sl = round(c_low + (self.config.trailing_stop_atr * atr_t), 2)
                        sl = min(sl, trail_sl)
                    active_trade["stop_loss"] = sl

                trade_closed = False
                exit_price = c_close
                result = "EXPIRED"
                exit_reason = "Holding time limit reached"

                if dir_t == "LONG":
                    hit_sl = c_low <= sl
                    hit_tp2 = c_high >= tp2
                    hit_tp1 = c_high >= tp1

                    if hit_sl and hit_tp1:
                        # Same candle conflict resolution
                        if self.config.same_candle_policy == "stop_first":
                            trade_closed = True
                            exit_price = sl
                            result = "STOP_LOSS"
                            exit_reason = "Stop-loss triggered (Stop-first conflict policy)"
                        else:
                            trade_closed = True
                            exit_price = tp1
                            result = "TP1"
                            exit_reason = "Take-profit 1 reached"
                    elif hit_sl:
                        trade_closed = True
                        exit_price = sl
                        result = "STOP_LOSS"
                        exit_reason = "Stop-loss price reached"
                    elif hit_tp2:
                        trade_closed = True
                        exit_price = tp2
                        result = "TP2"
                        exit_reason = "Take-profit 2 reached"
                    elif hit_tp1:
                        trade_closed = True
                        exit_price = tp1
                        result = "TP1"
                        exit_reason = "Take-profit 1 reached"
                    elif (self.config.time_invalidation_minutes is not None and
                          self.config.time_invalidation_min_mfe_r is not None and
                          holding_mins >= self.config.time_invalidation_minutes and
                          peak_mfe_r < self.config.time_invalidation_min_mfe_r):
                        trade_closed = True
                        exit_price = c_close
                        result = "EXPIRED"
                        exit_reason = f"Time-based invalidation (MFE {peak_mfe_r:.2f}R < {self.config.time_invalidation_min_mfe_r}R at {self.config.time_invalidation_minutes}m)"
                    elif holding_mins >= self.config.max_holding_minutes:
                        trade_closed = True
                        exit_price = c_close
                        result = "EXPIRED"
                        exit_reason = f"Max holding time ({self.config.max_holding_minutes}m) expired"

                else:  # SHORT
                    hit_sl = c_high >= sl
                    hit_tp2 = c_low <= tp2
                    hit_tp1 = c_low <= tp1

                    if hit_sl and hit_tp1:
                        if self.config.same_candle_policy == "stop_first":
                            trade_closed = True
                            exit_price = sl
                            result = "STOP_LOSS"
                            exit_reason = "Stop-loss triggered (Stop-first conflict policy)"
                        else:
                            trade_closed = True
                            exit_price = tp1
                            result = "TP1"
                            exit_reason = "Take-profit 1 reached"
                    elif hit_sl:
                        trade_closed = True
                        exit_price = sl
                        result = "STOP_LOSS"
                        exit_reason = "Stop-loss price reached"
                    elif hit_tp2:
                        trade_closed = True
                        exit_price = tp2
                        result = "TP2"
                        exit_reason = "Take-profit 2 reached"
                    elif hit_tp1:
                        trade_closed = True
                        exit_price = tp1
                        result = "TP1"
                        exit_reason = "Take-profit 1 reached"
                    elif (self.config.time_invalidation_minutes is not None and
                          self.config.time_invalidation_min_mfe_r is not None and
                          holding_mins >= self.config.time_invalidation_minutes and
                          peak_mfe_r < self.config.time_invalidation_min_mfe_r):
                        trade_closed = True
                        exit_price = c_close
                        result = "EXPIRED"
                        exit_reason = f"Time-based invalidation (MFE {peak_mfe_r:.2f}R < {self.config.time_invalidation_min_mfe_r}R at {self.config.time_invalidation_minutes}m)"
                    elif holding_mins >= self.config.max_holding_minutes:
                        trade_closed = True
                        exit_price = c_close
                        result = "EXPIRED"
                        exit_reason = f"Max holding time ({self.config.max_holding_minutes}m) expired"

                if trade_closed:
                    # Calculate PnL and R-multiple
                    if dir_t == "LONG":
                        price_diff = exit_price - entry_p
                    else:
                        price_diff = entry_p - exit_price

                    r_multiple = round(price_diff / sl_dist, 2) if sl_dist > 0 else 0.0
                    pnl = round(r_multiple * self.config.risk_per_trade_usd, 2)

                    trade_obj = BacktestTrade(
                        id=active_trade["id"],
                        symbol=self.config.symbol,
                        direction=dir_t,
                        signal_time=active_trade["signal_time"],
                        signal_time_iso=datetime.fromtimestamp(active_trade["signal_time"], tz=timezone.utc).isoformat(),
                        entry_time=active_trade["entry_time"],
                        entry_time_iso=datetime.fromtimestamp(active_trade["entry_time"], tz=timezone.utc).isoformat(),
                        exit_time=t_1m,
                        exit_time_iso=datetime.fromtimestamp(t_1m, tz=timezone.utc).isoformat(),
                        signal_strength=active_trade["signal_strength"],
                        entry_price=entry_p,
                        stop_loss=sl,
                        take_profit_1=tp1,
                        take_profit_2=tp2,
                        exit_price=exit_price,
                        result=result,
                        pnl=pnl,
                        r_multiple=r_multiple,
                        holding_minutes=round(max(1.0, holding_mins), 1),
                        exit_reason=exit_reason,
                        entry_reason=active_trade["entry_reason"],
                        market_regime=active_trade["market_regime"],
                        session=active_trade["session"],
                        mae_r=round(active_trade["peak_mae_r"], 2),
                        mfe_r=round(active_trade["peak_mfe_r"], 2),
                        mae_price=round(active_trade["peak_mae_price"], 2),
                        mfe_price=round(active_trade["peak_mfe_price"], 2)
                    )
                    trades.append(trade_obj)
                    active_trade = None

            # -------------------------------------------------------------
            # Step C: Evaluate Signal on this Closed 1m Bar (Strict Anti-Look-Ahead)
            # -------------------------------------------------------------
            if active_trade is None and pending_signal is None and (i < len(candles_1m) - 1):
                if precomputed_signals is not None:
                    cached_item = precomputed_signals.get(i)
                    if cached_item is not None:
                        sig, atr_val = cached_item
                        total_signals += 1
                        is_valid = (
                            (sig.type == "LONG_SETUP" and self.config.enable_long) or
                            (sig.type == "SHORT_SETUP" and self.config.enable_short)
                        ) and (sig.strength >= self.config.signal_threshold)

                        if is_valid:
                            pending_signal = {
                                "signal": sig,
                                "signal_time": t_1m,
                                "atr": atr_val
                            }
                else:
                    # Historical slice: ONLY closed 1m bars up to index i
                    past_1m_slice = candles_1m[max(0, i - 120):i + 1]

                    # Historical slice: ONLY 5m bars closed at or before t_1m + 60
                    # A 5m bar with open time t5 is closed at t5 + 300
                    max_closed_5m_open = t_1m + 60 - 300
                    idx_5m = bisect.bisect_right(c5m_times, max_closed_5m_open)
                    past_5m_slice = candles_5m[max(0, idx_5m - 60):idx_5m]

                    if len(past_1m_slice) >= 20 and len(past_5m_slice) >= 10:
                        current_bar_tick = {
                            "bid": float(current_1m["close"]),
                            "ask": float(current_1m["close"]) + spread_cost,
                            "timestamp": t_1m * 1000
                        }
                        signal: MarketSignal = self.signal_engine.analyze(
                            candles_1m=past_1m_slice,
                            candles_5m=past_5m_slice,
                            current_tick=current_bar_tick
                        )

                        if signal.type in ["LONG_SETUP", "SHORT_SETUP"]:
                            total_signals += 1
                            is_valid = (
                                (signal.type == "LONG_SETUP" and self.config.enable_long) or
                                (signal.type == "SHORT_SETUP" and self.config.enable_short)
                            ) and (signal.strength >= self.config.signal_threshold)

                            if is_valid:
                                atr_val = signal.indicators.atr_1m or get_latest_atr(past_1m_slice, 14) or 1.50
                                pending_signal = {
                                    "signal": signal,
                                    "signal_time": t_1m,
                                    "atr": atr_val
                                }

        # -------------------------------------------------------------
        # Step D: Compute Overall Performance Statistics & Equity Curve
        # -------------------------------------------------------------
        stats, equity_curve = compute_statistics(
            trades=trades,
            total_signals=total_signals,
            initial_capital=self.config.initial_capital,
            risk_per_trade_usd=self.config.risk_per_trade_usd
        )

        start_ts = int(candles_1m[0]["time"])
        end_ts = int(candles_1m[-1]["time"])

        return BacktestResponse(
            symbol=self.config.symbol,
            period={
                "start": datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(),
                "end": datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat(),
                "total_1m_candles": str(len(candles_1m)),
                "total_5m_candles": str(len(candles_5m))
            },
            configuration=self.config.model_dump(),
            execution_metadata={
                "engine": "Deterministic Multi-Timeframe Replay (Strict No-Lookahead)",
                "signal_source": "Live SignalEngine Rule-Confluence",
                "entry_rule": "Next 1m Candle Open",
                "execution_mode": self.config.execution_mode,
                "assumed_spread": f"${self.config.assumed_spread:.2f}",
                "same_candle_policy": self.config.same_candle_policy,
                "disclaimer": "Historical simulations are for rule verification and measurement only. Past performance does not guarantee future profitability."
            },
            statistics=stats,
            trades=trades,
            equity_curve=equity_curve
        )
