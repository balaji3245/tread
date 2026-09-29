"""
Phase 6E: Conditional Entry-State & Regime Models
Data structures and exception definitions for entry-state classifications,
session groupings, volatility quantiles, and Final OOS protection guards.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ProtectedFinalOOSAccessError(Exception):
    """Raised when candidate research or selection logic attempts to access protected Final OOS data."""
    pass


class ImpulseState(str, Enum):
    EARLY_IMPULSE = "EARLY_IMPULSE"
    CONTROLLED_PULLBACK = "CONTROLLED_PULLBACK"
    LATE_IMPULSE = "LATE_IMPULSE"
    NEUTRAL = "NEUTRAL"


class VolatilityQuantile(str, Enum):
    Q1_LOW = "0-20% (Low Vol)"
    Q2_MID_LOW = "20-40% (Mid-Low Vol)"
    Q3_MEDIAN = "40-60% (Median Vol)"
    Q4_MID_HIGH = "60-80% (Mid-High Vol)"
    Q5_HIGH = "80-100% (High Vol)"


class SessionBlock(str, Enum):
    ASIAN = "ASIAN (00:00-07:00 UTC)"
    LONDON = "LONDON (07:00-13:00 UTC)"
    NY_OVERLAP = "NY_OVERLAP (13:00-17:00 UTC)"
    NY_AFTERNOON = "NY_AFTERNOON (17:00-21:00 UTC)"
    LATE_NIGHT = "LATE_NIGHT (21:00-00:00 UTC)"


class TrendRangeRegime(str, Enum):
    STRONG_TREND = "STRONG_TREND"
    TREND_PULLBACK = "TREND_PULLBACK"
    RANGE_COMPRESSION = "RANGE_COMPRESSION"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"


class FeatureProvenance(BaseModel):
    """Audit metadata proving feature dependency strictly <= signal timestamp."""
    feature_name: str
    source_timeframe: str  # "1m" | "5m"
    calculation_timestamp: int
    required_historical_bars: int
    future_data_dependency: bool = False
    formula_description: str


class ConditionalBucketMetrics(BaseModel):
    """Summary metrics for a specific conditional market state / regime bucket."""
    bucket_name: str
    trade_count: int
    trade_share_pct: float
    win_count: int
    loss_count: int
    win_rate_pct: float
    total_net_r: float
    average_r: float
    median_r: float
    profit_factor: float
    gross_profit_r: float
    gross_loss_r: float
    mean_mae_r: float
    mean_mfe_r: float
    early_stop_rate_pct: float  # stopped <= 3 min
    reach_1r_mfe_pct: float  # MFE >= +1.0R
    instant_stop_rate_pct: float  # stopped at bar 1 (1m)


class InteractionHypothesisResult(BaseModel):
    """Results for mechanism-driven interaction pairs."""
    interaction_id: str
    interaction_name: str
    hypothesis_description: str
    dimension_a: str
    dimension_b: str
    bucket_results: List[ConditionalBucketMetrics]
