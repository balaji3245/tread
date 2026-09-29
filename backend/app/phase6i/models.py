"""
Phase 6I: Live Shadow / Paper Validation Models
Data structures for real-time state machine, persistent journal records,
daily summaries, heartbeat health status, and live monitoring metrics.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ShadowState(str, Enum):
    IDLE = "IDLE"
    SIGNAL_ACTIVE = "SIGNAL_ACTIVE"
    WAITING_FOR_RETRACE = "WAITING_FOR_RETRACE"
    FILLED = "FILLED"
    VIRTUAL_TRADE_ACTIVE = "VIRTUAL_TRADE_ACTIVE"
    EXITED = "EXITED"
    TIMED_OUT = "TIMED_OUT"
    INVALIDATED = "INVALIDATED"
    CANCELLED_CONCURRENCY = "CANCELLED_CONCURRENCY"


class ShadowSignalClassification(str, Enum):
    NO_H006_SETUP = "NO_H006_SETUP"
    WAITING = "WAITING"
    FILLED = "FILLED"
    TIMED_OUT = "TIMED_OUT"
    INVALIDATED = "INVALIDATED"
    CANCELLED_CONCURRENCY = "CANCELLED_CONCURRENCY"


class ShadowJournalEntry(BaseModel):
    """Immutable, append-only record logged for each signal event and trade lifecycle."""
    event_id: str
    timestamp_utc: str
    signal_timestamp: int
    signal_timestamp_iso: str
    signal_direction: str
    signal_score: int
    
    # Baseline comparison
    baseline_signal: bool = True
    h006_signal: bool = True
    
    # At-signal market features
    signal_price: float
    atr_at_signal: float
    ema21_at_signal: float
    ema50_at_signal: float
    spread_at_signal: float
    bid_at_signal: float
    ask_at_signal: float
    
    session: str
    volatility_regime: str
    market_regime: str
    entry_state: str
    
    # H006 Trigger mechanics
    retracement_target: float
    entry_triggered: bool = False
    entry_timestamp: Optional[int] = None
    entry_timestamp_iso: Optional[str] = None
    virtual_entry_price: Optional[float] = None
    delay_seconds: Optional[float] = None
    delay_minutes: Optional[float] = None
    entry_price_improvement_r: Optional[float] = None
    
    # Terminal outcomes
    timeout: bool = False
    invalidation: bool = False
    cancellation_reason: Optional[str] = None
    
    # Virtual trade exit details
    virtual_sl: Optional[float] = None
    virtual_tp1: Optional[float] = None
    virtual_tp2: Optional[float] = None
    exit_timestamp: Optional[int] = None
    exit_timestamp_iso: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    result: Optional[str] = None
    holding_minutes: Optional[float] = None
    
    r_multiple: Optional[float] = None
    pnl_usd: Optional[float] = None
    mae_r: Optional[float] = None
    mfe_r: Optional[float] = None


class ActiveVirtualTrade(BaseModel):
    """In-memory active virtual trade state preserved across service restarts."""
    trade_id: str
    signal_id: str
    direction: str
    signal_timestamp: int
    entry_timestamp: int
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    sl_dist: float
    atr: float
    entry_reason: str
    peak_mfe_price: float = 0.0
    peak_mae_price: float = 0.0
    peak_mfe_r: float = 0.0
    peak_mae_r: float = 0.0


class PendingShadowSignal(BaseModel):
    """In-memory state for a signal currently in the 2-minute waiting window."""
    signal_id: str
    signal_timestamp: int
    direction: str
    score: int
    signal_close: float
    atr: float
    target_price: float
    invalidation_price: float
    max_wait_seconds: int = 120
    created_at_time: float


class ShadowDailySummary(BaseModel):
    """Aggregated daily reporting metrics."""
    date_str: str
    baseline_signals_count: int = 0
    h006_eligible_count: int = 0
    h006_filled_count: int = 0
    h006_timeout_count: int = 0
    h006_invalidated_count: int = 0
    h006_concurrency_cancelled_count: int = 0
    h006_virtual_trades_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate_pct: float = 0.0
    total_net_r: float = 0.0
    expectancy_r: float = 0.0
    profit_factor: float = 0.0
    gross_profit_r: float = 0.0
    gross_loss_r: float = 0.0
    mean_mae_r: float = 0.0
    mean_mfe_r: float = 0.0
    average_delay_minutes: float = 0.0
    average_entry_improvement_r: float = 0.0
    longest_losing_streak: int = 0


class ShadowHealthStatus(BaseModel):
    """Real-time health status and operational telemetry of the live shadow engine."""
    shadow_engine_active: bool = True
    market_feed_status: Literal["ACTIVE", "MARKET_INACTIVE", "DISCONNECTED"] = "MARKET_INACTIVE"
    is_live_trading_disabled: bool = True  # Strict safety guarantee
    real_orders_count: int = 0             # Must always be 0
    last_tick_timestamp: Optional[int] = None
    last_signal_timestamp: Optional[int] = None
    last_evaluation_timestamp_utc: Optional[str] = None
    active_virtual_trade: Optional[ActiveVirtualTrade] = None
    pending_signal: Optional[PendingShadowSignal] = None
    journal_write_ok: bool = True
    total_journal_entries: int = 0
    checkpoint_milestone: str = "0/100 Signals"
