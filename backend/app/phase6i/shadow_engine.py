"""
Phase 6I: Live Shadow / Paper Execution Engine
Purely observational, read-only shadow engine evaluating frozen candidate V6F-H006
alongside live baseline analyzer without submitting real orders.
"""
import copy
import json
import logging
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.phase6i.models import (
    ActiveVirtualTrade,
    PendingShadowSignal,
    ShadowDailySummary,
    ShadowHealthStatus,
    ShadowJournalEntry,
    ShadowSignalClassification,
    ShadowState,
)
from app.signal_models import MarketSignal

logger = logging.getLogger(__name__)

SHADOW_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "shadow"
JOURNAL_FILE = SHADOW_DATA_DIR / "phase6i_shadow_journal.jsonl"
STATE_FILE = SHADOW_DATA_DIR / "phase6i_state.json"
DAILY_SUMMARY_FILE = SHADOW_DATA_DIR / "phase6i_daily_summary.json"


class LiveShadowEngine:
    """
    Independent, failure-isolated live shadow validation engine for V6F-H006.
    Operates strictly in virtual paper mode (zero live order execution).
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or SHADOW_DATA_DIR
        self.journal_file = self.data_dir / "phase6i_shadow_journal.jsonl"
        self.state_file = self.data_dir / "phase6i_state.json"
        self.daily_summary_file = self.data_dir / "phase6i_daily_summary.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Frozen Strategy Parameters (phase6f-h006-v1)
        self.retrace_atr: float = 0.15
        self.max_wait_seconds: int = 120
        self.invalidation_atr: float = 0.75
        self.sl_atr_multiplier: float = 1.0
        self.tp1_atr_multiplier: float = 1.0
        self.tp2_atr_multiplier: float = 2.0
        self.assumed_spread: float = 0.30
        self.max_holding_seconds: int = 3600
        self.risk_per_trade_usd: float = 100.0

        # State tracking
        self.pending_signal: Optional[PendingShadowSignal] = None
        self.active_trade: Optional[ActiveVirtualTrade] = None
        self.processed_signal_ids: set = set()
        self.total_journal_entries: int = 0
        self.last_tick_timestamp: Optional[int] = None
        self.last_signal_timestamp: Optional[int] = None
        self.journal_write_ok: bool = True

        self._recover_state_on_startup()

    def _recover_state_on_startup(self):
        """Recover active state from persistent storage after server restart."""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                if state_data.get("active_trade"):
                    self.active_trade = ActiveVirtualTrade(**state_data["active_trade"])
                    logger.info("Shadow engine recovered active virtual trade: %s", self.active_trade.trade_id)
                if state_data.get("pending_signal"):
                    self.pending_signal = PendingShadowSignal(**state_data["pending_signal"])
                    logger.info("Shadow engine recovered pending signal: %s", self.pending_signal.signal_id)
                self.processed_signal_ids = set(state_data.get("processed_signal_ids", []))

            if self.journal_file.exists():
                with open(self.journal_file, "r", encoding="utf-8") as f:
                    self.total_journal_entries = sum(1 for _ in f)
        except Exception as e:
            logger.error("Failed to recover shadow state on startup: %s", e, exc_info=True)

    def _persist_state(self):
        """Persist current active state for restart survival."""
        try:
            state_data = {
                "active_trade": self.active_trade.model_dump() if self.active_trade else None,
                "pending_signal": self.pending_signal.model_dump() if self.pending_signal else None,
                "processed_signal_ids": list(self.processed_signal_ids)[-1000:],  # retain recent 1000
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.error("Failed to persist shadow state: %s", e, exc_info=True)

    def _append_to_journal(self, entry: ShadowJournalEntry):
        """Append an immutable journal record to JSONL log."""
        try:
            with open(self.journal_file, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
            self.total_journal_entries += 1
            self.journal_write_ok = True
        except Exception as e:
            self.journal_write_ok = False
            logger.error("Failed to append to shadow journal: %s", e, exc_info=True)

    def process_new_signal(
        self,
        signal: MarketSignal,
        candles_1m: List[Dict[str, Any]],
        current_tick: Optional[Dict[str, Any]] = None,
    ) -> Optional[ShadowJournalEntry]:
        """
        Evaluate new baseline signal arriving from live analyzer.
        Guarantees isolation: exceptions will never disrupt the live system.
        """
        try:
            if signal.type not in ["LONG_SETUP", "SHORT_SETUP"] or signal.strength < 7:
                return None

            if current_tick and "timestamp" in current_tick:
                t_raw = current_tick["timestamp"]
                sig_time = int(t_raw / 1000.0) if t_raw > 10_000_000_000 else int(t_raw)
            elif candles_1m:
                sig_time = int(candles_1m[-1]["time"])
            else:
                sig_time = signal.generatedAt // 1000 if signal.generatedAt > 10_000_000_000 else signal.generatedAt

            direction = "LONG" if signal.type == "LONG_SETUP" else "SHORT"
            signal_id = f"XAUUSD_1m_{sig_time}_{direction}"
            self.last_signal_timestamp = sig_time

            # Deduplication check
            if signal_id in self.processed_signal_ids:
                logger.debug("Duplicate signal ignored: %s", signal_id)
                return None

            self.processed_signal_ids.add(signal_id)

            atr_val = signal.indicators.atr_1m or 1.50
            c_close = signal.price
            spread_val = float(current_tick.get("spread", self.assumed_spread)) if current_tick else self.assumed_spread
            spread_dollars = spread_val * 0.01 if spread_val > 2.0 else spread_val
            bid_val = float(current_tick["bid"]) if current_tick else c_close
            ask_val = float(current_tick["ask"]) if current_tick else c_close + spread_dollars

            # Concurrency check (max_concurrent_trades = 1)
            if self.active_trade is not None or self.pending_signal is not None:
                canc_reason = "Channel busy: active virtual trade" if self.active_trade else "Channel busy: pending signal waiting"
                entry = ShadowJournalEntry(
                    event_id=f"EVT_{signal_id}_SKIPPED",
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    signal_timestamp=sig_time,
                    signal_timestamp_iso=datetime.fromtimestamp(sig_time, tz=timezone.utc).isoformat(),
                    signal_direction=direction,
                    signal_score=signal.strength,
                    baseline_signal=True,
                    h006_signal=False,
                    signal_price=c_close,
                    atr_at_signal=atr_val,
                    ema21_at_signal=signal.indicators.ema21_1m or c_close,
                    ema50_at_signal=signal.indicators.ema50_1m or c_close,
                    spread_at_signal=spread_dollars,
                    bid_at_signal=bid_val,
                    ask_at_signal=ask_val,
                    session="LIVE",
                    volatility_regime="LIVE",
                    market_regime=signal.trend_5m,
                    entry_state="CONCURRENCY_BLOCKED",
                    retracement_target=0.0,
                    entry_triggered=False,
                    timeout=False,
                    invalidation=False,
                    cancellation_reason=canc_reason,
                )
                self._append_to_journal(entry)
                self._persist_state()
                return entry

            # Initialize H006 waiting state
            retrace_dist = round(self.retrace_atr * atr_val, 2)
            inval_dist = round(self.invalidation_atr * atr_val, 2)

            if direction == "LONG":
                target_p = round(c_close - retrace_dist, 2)
                inval_p = round(c_close - inval_dist, 2)
            else:
                target_p = round(c_close + retrace_dist, 2)
                inval_p = round(c_close + inval_dist, 2)

            self.pending_signal = PendingShadowSignal(
                signal_id=signal_id,
                signal_timestamp=sig_time,
                direction=direction,
                score=signal.strength,
                signal_close=c_close,
                atr=atr_val,
                target_price=target_p,
                invalidation_price=inval_p,
                max_wait_seconds=self.max_wait_seconds,
                created_at_time=time.time(),
            )
            self._persist_state()
            logger.info("Shadow engine registered new pending signal: %s (Target: %.2f)", signal_id, target_p)
            return None

        except Exception as e:
            logger.error("Isolated error in shadow process_new_signal: %s", e, exc_info=True)
            return None

    def process_tick_update(self, tick: Dict[str, Any]) -> Optional[ShadowJournalEntry]:
        """
        Process live tick update against pending signals and active virtual trades.
        """
        try:
            bid = float(tick["bid"])
            ask = float(tick.get("ask", bid + self.assumed_spread))
            t_sec = int(tick["timestamp"] / 1000.0) if tick["timestamp"] > 10_000_000_000 else int(tick["timestamp"])
            self.last_tick_timestamp = t_sec
            spread = round(ask - bid, 2)

            # 1. Evaluate Pending Signal (Waiting Window <= 120s)
            if self.pending_signal is not None:
                ps = self.pending_signal
                elapsed_sec = t_sec - ps.signal_timestamp

                # Invalidation check
                if (ps.direction == "LONG" and bid <= ps.invalidation_price) or (ps.direction == "SHORT" and ask >= ps.invalidation_price):
                    entry = ShadowJournalEntry(
                        event_id=f"EVT_{ps.signal_id}_INVAL",
                        timestamp_utc=datetime.now(timezone.utc).isoformat(),
                        signal_timestamp=ps.signal_timestamp,
                        signal_timestamp_iso=datetime.fromtimestamp(ps.signal_timestamp, tz=timezone.utc).isoformat(),
                        signal_direction=ps.direction,
                        signal_score=ps.score,
                        signal_price=ps.signal_close,
                        atr_at_signal=ps.atr,
                        ema21_at_signal=ps.signal_close,
                        ema50_at_signal=ps.signal_close,
                        spread_at_signal=spread,
                        bid_at_signal=bid,
                        ask_at_signal=ask,
                        session="LIVE",
                        volatility_regime="LIVE",
                        market_regime="LIVE",
                        entry_state="INVALIDATED",
                        retracement_target=ps.target_price,
                        entry_triggered=False,
                        timeout=False,
                        invalidation=True,
                        cancellation_reason=f"Adverse invalidation price {ps.invalidation_price} reached",
                    )
                    self._append_to_journal(entry)
                    self.pending_signal = None
                    self._persist_state()
                    logger.info("Shadow pending signal invalidated: %s", ps.signal_id)
                    return entry

                # Limit Fill Trigger check
                if (ps.direction == "LONG" and bid <= ps.target_price) or (ps.direction == "SHORT" and ask >= ps.target_price):
                    # Long enters at Ask, Short enters at Bid
                    if ps.direction == "LONG":
                        entry_p = round(min(ps.target_price, bid) + spread, 2)
                        sl_dist = max(0.50, round(ps.atr * self.sl_atr_multiplier, 2))
                        tp1_dist = round(ps.atr * self.tp1_atr_multiplier, 2)
                        tp2_dist = round(ps.atr * self.tp2_atr_multiplier, 2)
                        sl = round(entry_p - sl_dist, 2)
                        tp1 = round(entry_p + tp1_dist, 2)
                        tp2 = round(entry_p + tp2_dist, 2)
                    else:
                        entry_p = round(max(ps.target_price, ask) - spread, 2)
                        sl_dist = max(0.50, round(ps.atr * self.sl_atr_multiplier, 2))
                        tp1_dist = round(ps.atr * self.tp1_atr_multiplier, 2)
                        tp2_dist = round(ps.atr * self.tp2_atr_multiplier, 2)
                        sl = round(entry_p + sl_dist, 2)
                        tp1 = round(entry_p - tp1_dist, 2)
                        tp2 = round(entry_p - tp2_dist, 2)

                    trade_id = f"TRD_{ps.signal_id}"
                    self.active_trade = ActiveVirtualTrade(
                        trade_id=trade_id,
                        signal_id=ps.signal_id,
                        direction=ps.direction,
                        signal_timestamp=ps.signal_timestamp,
                        entry_timestamp=t_sec,
                        entry_price=entry_p,
                        stop_loss=sl,
                        take_profit_1=tp1,
                        take_profit_2=tp2,
                        sl_dist=sl_dist,
                        atr=ps.atr,
                        entry_reason=f"0.15 ATR retrace limit filled at {entry_p}",
                    )
                    self.pending_signal = None
                    self._persist_state()
                    logger.info("Shadow engine filled virtual trade: %s at %.2f (SL: %.2f, TP1: %.2f)", trade_id, entry_p, sl, tp1)
                    return None

                # Timeout check
                if elapsed_sec > ps.max_wait_seconds:
                    entry = ShadowJournalEntry(
                        event_id=f"EVT_{ps.signal_id}_TIMEOUT",
                        timestamp_utc=datetime.now(timezone.utc).isoformat(),
                        signal_timestamp=ps.signal_timestamp,
                        signal_timestamp_iso=datetime.fromtimestamp(ps.signal_timestamp, tz=timezone.utc).isoformat(),
                        signal_direction=ps.direction,
                        signal_score=ps.score,
                        signal_price=ps.signal_close,
                        atr_at_signal=ps.atr,
                        ema21_at_signal=ps.signal_close,
                        ema50_at_signal=ps.signal_close,
                        spread_at_signal=spread,
                        bid_at_signal=bid,
                        ask_at_signal=ask,
                        session="LIVE",
                        volatility_regime="LIVE",
                        market_regime="LIVE",
                        entry_state="TIMED_OUT",
                        retracement_target=ps.target_price,
                        entry_triggered=False,
                        timeout=True,
                        invalidation=False,
                        cancellation_reason=f"2-minute timeout reached ({elapsed_sec}s)",
                    )
                    self._append_to_journal(entry)
                    self.pending_signal = None
                    self._persist_state()
                    logger.info("Shadow pending signal timed out: %s", ps.signal_id)
                    return entry

            # 2. Evaluate Active Virtual Trade Exits
            if self.active_trade is not None:
                at = self.active_trade
                holding_sec = t_sec - at.entry_timestamp

                # Update peak excursions
                if at.direction == "LONG":
                    fav = max(0.0, bid - at.entry_price)
                    adv = max(0.0, at.entry_price - bid)
                else:
                    fav = max(0.0, at.entry_price - ask)
                    adv = max(0.0, ask - at.entry_price)

                at.peak_mfe_price = max(at.peak_mfe_price, fav)
                at.peak_mae_price = max(at.peak_mae_price, adv)
                at.peak_mfe_r = round(at.peak_mfe_price / at.sl_dist, 3)
                at.peak_mae_r = round(at.peak_mae_price / at.sl_dist, 3)

                trade_closed = False
                exit_price = bid if at.direction == "LONG" else ask
                result = "EXPIRED"
                exit_reason = "Holding time limit reached"

                if at.direction == "LONG":
                    if bid <= at.stop_loss:
                        trade_closed = True; exit_price = at.stop_loss; result = "STOP_LOSS"; exit_reason = "Stop-loss reached"
                    elif bid >= at.take_profit_2:
                        trade_closed = True; exit_price = at.take_profit_2; result = "TP2"; exit_reason = "Take-profit 2 reached"
                    elif bid >= at.take_profit_1:
                        trade_closed = True; exit_price = at.take_profit_1; result = "TP1"; exit_reason = "Take-profit 1 reached"
                    elif holding_sec >= self.max_holding_seconds:
                        trade_closed = True; exit_price = bid; result = "EXPIRED"; exit_reason = f"Max holding ({self.max_holding_seconds}s) expired"
                else:
                    if ask >= at.stop_loss:
                        trade_closed = True; exit_price = at.stop_loss; result = "STOP_LOSS"; exit_reason = "Stop-loss reached"
                    elif ask <= at.take_profit_2:
                        trade_closed = True; exit_price = at.take_profit_2; result = "TP2"; exit_reason = "Take-profit 2 reached"
                    elif ask <= at.take_profit_1:
                        trade_closed = True; exit_price = at.take_profit_1; result = "TP1"; exit_reason = "Take-profit 1 reached"
                    elif holding_sec >= self.max_holding_seconds:
                        trade_closed = True; exit_price = ask; result = "EXPIRED"; exit_reason = f"Max holding ({self.max_holding_seconds}s) expired"

                if trade_closed:
                    price_diff = (exit_price - at.entry_price) if at.direction == "LONG" else (at.entry_price - exit_price)
                    r_mul = round(price_diff / at.sl_dist, 2)
                    pnl = round(r_mul * self.risk_per_trade_usd, 2)
                    delay_m = round((at.entry_timestamp - at.signal_timestamp) / 60.0, 2)

                    entry = ShadowJournalEntry(
                        event_id=f"EVT_{at.trade_id}_EXIT",
                        timestamp_utc=datetime.now(timezone.utc).isoformat(),
                        signal_timestamp=at.signal_timestamp,
                        signal_timestamp_iso=datetime.fromtimestamp(at.signal_timestamp, tz=timezone.utc).isoformat(),
                        signal_direction=at.direction,
                        signal_score=8,
                        signal_price=at.entry_price,
                        atr_at_signal=at.atr,
                        ema21_at_signal=at.entry_price,
                        ema50_at_signal=at.entry_price,
                        spread_at_signal=spread,
                        bid_at_signal=bid,
                        ask_at_signal=ask,
                        session="LIVE",
                        volatility_regime="LIVE",
                        market_regime="LIVE",
                        entry_state="FILLED_COMPLETED",
                        retracement_target=at.entry_price,
                        entry_triggered=True,
                        entry_timestamp=at.entry_timestamp,
                        entry_timestamp_iso=datetime.fromtimestamp(at.entry_timestamp, tz=timezone.utc).isoformat(),
                        virtual_entry_price=at.entry_price,
                        delay_seconds=round(at.entry_timestamp - at.signal_timestamp, 1),
                        delay_minutes=delay_m,
                        entry_price_improvement_r=0.15,
                        virtual_sl=at.stop_loss,
                        virtual_tp1=at.take_profit_1,
                        virtual_tp2=at.take_profit_2,
                        exit_timestamp=t_sec,
                        exit_timestamp_iso=datetime.fromtimestamp(t_sec, tz=timezone.utc).isoformat(),
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        result=result,
                        holding_minutes=round(holding_sec / 60.0, 1),
                        r_multiple=r_mul,
                        pnl_usd=pnl,
                        mae_r=at.peak_mae_r,
                        mfe_r=at.peak_mfe_r,
                    )
                    self._append_to_journal(entry)
                    self.active_trade = None
                    self._persist_state()
                    logger.info("Shadow virtual trade exited: %s (%s, %.2fR)", at.trade_id, result, r_mul)
                    return entry

            return None

        except Exception as e:
            logger.error("Isolated error in shadow process_tick_update: %s", e, exc_info=True)
            return None

    def get_health_status(self) -> ShadowHealthStatus:
        """Return live health, market status, and operational telemetry."""
        # Determine market feed status (e.g. inactive on weekends)
        now_ts = int(time.time())
        feed_status = "MARKET_INACTIVE"
        if self.last_tick_timestamp is not None:
            if now_ts - self.last_tick_timestamp < 30:
                feed_status = "ACTIVE"
            else:
                feed_status = "MARKET_INACTIVE"

        # Checkpoint milestones (100, 250, 500, 1000)
        n = self.total_journal_entries
        if n < 100:
            milestone = f"{n}/100 Signals"
        elif n < 250:
            milestone = f"{n}/250 Signals"
        elif n < 500:
            milestone = f"{n}/500 Signals"
        elif n < 1000:
            milestone = f"{n}/1000 Signals"
        else:
            milestone = f"{n}+ Signals Milestone Reached"

        return ShadowHealthStatus(
            shadow_engine_active=True,
            market_feed_status=feed_status,
            is_live_trading_disabled=True,
            real_orders_count=0,
            last_tick_timestamp=self.last_tick_timestamp,
            last_signal_timestamp=self.last_signal_timestamp,
            last_evaluation_timestamp_utc=datetime.now(timezone.utc).isoformat(),
            active_virtual_trade=self.active_trade,
            pending_signal=self.pending_signal,
            journal_write_ok=self.journal_write_ok,
            total_journal_entries=self.total_journal_entries,
            checkpoint_milestone=milestone,
        )


live_shadow_engine = LiveShadowEngine()
