"""
Phase 6F: Entry Timing & Price-Path Models
Data structures, state machine definitions, conversion accounting,
and Final OOS protection guards for entry timing research.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


FINAL_OOS_START_TS = 1787843700  # 2026-08-27T15:15:00+00:00
FINAL_OOS_END_TS = 1790377140    # 2026-09-25T22:59:00+00:00


class ProtectedFinalOOSAccessError(Exception):
    """Raised when candidate research or selection logic attempts to access protected Final OOS data."""
    pass


class SignalEntryStatus(str, Enum):
    """Causal state of a signal during the entry-timing lifecycle."""
    WAITING_FOR_SIGNAL = "WAITING_FOR_SIGNAL"
    SIGNAL_ACTIVE = "SIGNAL_ACTIVE"
    WAITING_FOR_RETRACE = "WAITING_FOR_RETRACE"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    ENTERED_IMMEDIATELY = "ENTERED_IMMEDIATELY"
    ENTERED_AFTER_DELAY = "ENTERED_AFTER_DELAY"
    MISSED = "MISSED"
    INVALIDATED = "INVALIDATED"
    TIMED_OUT = "TIMED_OUT"


class PathForensicLabel(str, Enum):
    """
    Forensic outcome labels classified strictly AFTER the event for post-hoc analysis.
    FORBIDDEN as causal entry features.
    """
    IMMEDIATE_FAVORABLE = "IMMEDIATE_FAVORABLE"
    EARLY_ADVERSE_THEN_RECOVERY = "EARLY_ADVERSE_THEN_RECOVERY"
    PURE_ADVERSE = "PURE_ADVERSE"
    CONTROLLED_RETRACE = "CONTROLLED_RETRACE"
    FAST_CONTINUATION = "FAST_CONTINUATION"
    CHOP = "CHOP"


class TimingFeatureProvenance(BaseModel):
    """Audit record proving that feature calculation uses data strictly <= signal timestamp."""
    feature_name: str
    source_timeframe: str  # "1m" | "5m"
    calculation_timestamp: int
    required_historical_bars: int
    future_data_dependency: bool = False
    formula_description: str


class EarlyPathExcursion(BaseModel):
    """Forward excursion metrics measured at 1m, 2m, 3m, and 5m after signal."""
    horizon_minutes: int
    mfe_r: float
    mae_r: float
    directional_continuation: bool
    price_change_atr: float


class SignalTimingRecord(BaseModel):
    """Detailed research record for a single baseline signal at timestamp T."""
    signal_id: str
    signal_timestamp: int
    signal_timestamp_iso: str
    signal_direction: str
    signal_score: int
    signal_open: float
    signal_high: float
    signal_low: float
    signal_close: float
    atr_at_signal: float
    ema21_at_signal: float
    ema50_at_signal: float
    distance_to_ema21_atr: float
    distance_to_ema50_atr: float
    recent_impulse_size_atr: float
    recent_range_atr: float
    recent_body_ratio: float
    spread_at_signal: float
    session: str
    volatility_regime: str
    market_regime: str
    entry_state: str
    
    # Baseline immediate execution (T+1 Open)
    baseline_entry_price: float
    baseline_entry_time: int
    baseline_realized_r: Optional[float] = None
    baseline_result: Optional[str] = None
    baseline_mae_r: Optional[float] = None
    baseline_mfe_r: Optional[float] = None
    baseline_early_stop: Optional[bool] = None

    # Forward excursions
    path_1m: Optional[EarlyPathExcursion] = None
    path_2m: Optional[EarlyPathExcursion] = None
    path_3m: Optional[EarlyPathExcursion] = None
    path_5m: Optional[EarlyPathExcursion] = None
    forensic_outcome_label: Optional[PathForensicLabel] = None


class SignalConversionMetrics(BaseModel):
    """Comprehensive accounting of signals converted to trades vs missed/invalidated."""
    signal_count: int
    entered_immediately_count: int
    entered_after_delay_count: int
    total_entered_count: int
    missed_count: int
    invalidated_count: int
    timed_out_count: int
    signal_conversion_rate_pct: float
    trade_reduction_pct: float
    average_delay_minutes: float
    median_delay_minutes: float


class EntryPriceQualityMetrics(BaseModel):
    """Comparative price quality and risk/reward metrics between baseline and candidate entry."""
    average_price_improvement_r: float
    median_price_improvement_r: float
    atr_normalized_improvement: float
    baseline_mean_mae_r: float
    candidate_mean_mae_r: float
    baseline_early_stop_rate_pct: float
    candidate_early_stop_rate_pct: float
    baseline_mean_mfe_r: float
    candidate_mean_mfe_r: float
    baseline_reach_1r_pct: float
    candidate_reach_1r_pct: float
    baseline_reach_2r_pct: float
    candidate_reach_2r_pct: float


class WindowTimingMetrics(BaseModel):
    """Performance metrics for a specific OOS window."""
    window_index: int
    val_start_iso: str
    val_end_iso: str
    baseline_trades: int
    candidate_trades: int
    trade_reduction_pct: float
    baseline_win_rate_pct: float
    candidate_win_rate_pct: float
    baseline_expectancy_r: float
    candidate_expectancy_r: float
    baseline_profit_factor: float
    candidate_profit_factor: float
    candidate_net_r: float
    delta_r: float
    candidate_early_stop_rate_pct: float


class CandidateTimingResult(BaseModel):
    """Standardized serialization artifact for Phase 6F entry-timing candidate."""
    candidate_id: str
    title: str
    hypothesis_type: str
    rule_description: str
    same_candle_policy: str = "stop_first"
    
    # Development summary (90 days)
    dev_trade_count: int
    dev_net_r: float
    dev_win_rate: float
    dev_profit_factor: float
    dev_expectancy: float
    dev_trade_reduction_pct: float
    
    # Preliminary OOS summary (Windows #1 to #8)
    preliminary_oos_trade_count: int
    preliminary_oos_net_r: float
    preliminary_oos_delta_r: float
    preliminary_oos_win_rate: float
    preliminary_oos_profit_factor: float
    preliminary_oos_expectancy: float
    preliminary_oos_trade_reduction_pct: float
    
    # Window robustness
    positive_windows: int
    negative_windows: int
    mean_window_expectancy: float
    median_window_expectancy: float
    worst_window_expectancy: float
    best_window_expectancy: float
    windows: List[WindowTimingMetrics]
    
    # Conversion and Price Quality
    conversion_metrics: SignalConversionMetrics
    price_quality_metrics: EntryPriceQualityMetrics
    
    # Decision
    status: Literal["REJECTED", "EXPLORATORY", "PROMISING", "NEEDS_MORE_DATA"]
    decision: Literal["REJECTED", "EXPLORATORY", "PROMISING", "NEEDS_MORE_DATA"]
    decision_rationale: str
    
    # Final OOS Protection Guard
    final_oos_locked: bool = True
    final_oos_evaluated: bool = False
    final_oos_date_range: str = "2026-08-27 to 2026-09-25"
    
    provenance: List[TimingFeatureProvenance]
