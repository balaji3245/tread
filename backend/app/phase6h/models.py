"""
Phase 6H: Locked Final OOS Validation Models
Data models for pre-registration manifest, trade path audit records,
side-by-side comparative metrics, and Final OOS validation artifacts.
"""
import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

FINAL_OOS_START_TS = 1787843700  # 2026-08-27T15:15:00+00:00
FINAL_OOS_END_TS = 1790377140    # 2026-09-25T22:59:00+00:00
FINAL_OOS_DATE_RANGE = "2026-08-27 to 2026-09-25"


class FinalOOSVerdict(str, Enum):
    PASS_FINAL_OOS = "PASS_FINAL_OOS"
    FAIL_FINAL_OOS = "FAIL_FINAL_OOS"
    INCONCLUSIVE_FINAL_OOS = "INCONCLUSIVE_FINAL_OOS"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"


class FinalOOSManifest(BaseModel):
    """Immutable pre-registration manifest defining frozen candidate and parameters."""
    candidate_id: str = "V6F-H006"
    candidate_version: str = "phase6f-h006-v1"
    candidate_title: str = "Tight Expiration Window (0.15 ATR Retrace / 2m Window)"
    candidate_parameters: Dict[str, Any] = Field(
        default_factory=lambda: {"retrace_atr": 0.15, "max_wait_bars": 2}
    )
    baseline_version: str = "phase6-baseline-v1"
    dataset_hash: str = "e9db340c4efa9e63"
    final_oos_start_ts: int = FINAL_OOS_START_TS
    final_oos_end_ts: int = FINAL_OOS_END_TS
    final_oos_date_range: str = FINAL_OOS_DATE_RANGE
    spread_dollars: float = 0.30
    execution_model: str = "intrabar_limit_spread_adjusted"
    same_candle_policy: str = "stop_first"
    concurrency_policy: str = "max_concurrent_1"
    holding_time_policy: str = "60_minutes_entry_origin"
    created_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def compute_manifest_hash(self) -> str:
        """Compute deterministic SHA256 hash of manifest parameters."""
        dump_str = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.sha256(dump_str.encode("utf-8")).hexdigest()


class FinalOOSTradeAudit(BaseModel):
    """Detailed trade path audit record for a single trade executed during Final OOS."""
    trade_id: str
    direction: str
    signal_timestamp: int
    signal_timestamp_iso: str
    entry_timestamp: int
    entry_timestamp_iso: str
    entry_price: float
    retracement_atr: float
    delay_minutes: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    exit_timestamp: int
    exit_timestamp_iso: str
    exit_price: float
    exit_reason: str
    result: str
    holding_minutes: float
    mae_r: float
    mfe_r: float
    r_multiple: float
    pnl_usd: float


class PerformanceSliceMetrics(BaseModel):
    """Comprehensive performance metrics for a backtest slice."""
    label: str
    signals_count: int
    executed_trades: int
    trade_conversion_pct: float
    win_count: int
    loss_count: int
    win_rate_pct: float
    total_net_r: float
    expectancy_r: float
    profit_factor: float
    gross_profit_r: float
    gross_loss_r: float
    max_drawdown_r: float
    max_drawdown_pct: float
    mean_mae_r: float
    mean_mfe_r: float
    average_win_r: float
    average_loss_r: float
    longest_losing_streak: int
    early_stop_rate_pct: float  # stopped <= 3m


class FinalOOSComparison(BaseModel):
    """Side-by-side metric comparison between Baseline and Candidate on Final OOS."""
    signals_delta: int
    trades_delta: int
    trade_reduction_pct: float
    win_rate_delta_pct: float
    net_r_delta: float
    expectancy_delta_r: float
    profit_factor_delta: float
    drawdown_reduction_r: float
    mae_delta_r: float
    mfe_delta_r: float


class FinalOOSValidationArtifact(BaseModel):
    """Permanent serialization schema for V6F-H006_final_oos_result.json."""
    candidate_id: str
    candidate_version: str
    manifest: FinalOOSManifest
    manifest_hash: str
    dataset_hash: str
    final_oos_start_iso: str
    final_oos_end_iso: str
    final_oos_locked: bool = True
    final_oos_evaluated: bool = True
    
    baseline_metrics: PerformanceSliceMetrics
    candidate_metrics: PerformanceSliceMetrics
    comparison: FinalOOSComparison
    
    signal_accounting: Dict[str, Any]
    timing_statistics: Dict[str, Any]
    trade_log: List[FinalOOSTradeAudit]
    
    verdict: FinalOOSVerdict
    verdict_rationale: str
    live_strategy: str = "phase6-baseline-v1"
    trading_execution: str = "NONE"
    strategy_promotion: str = "BLOCKED"
