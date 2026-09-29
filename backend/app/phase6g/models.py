"""
Phase 6G: Entry Execution Realism & Robustness Audit Models
Data structures, audit records, perturbation grids, and Final OOS protection guards.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.phase6f.models import FINAL_OOS_END_TS, FINAL_OOS_START_TS, ProtectedFinalOOSAccessError


class AuditVerdict(str, Enum):
    PASS_VERIFIED = "PASS — EXECUTION MODEL VERIFIED"
    PASS_WITH_CONCERNS = "PASS WITH ROBUSTNESS CONCERNS"
    FAIL_ACCOUNTING = "FAIL — EXECUTION ACCOUNTING ERROR"
    FAIL_SELECTION_BIAS = "FAIL — LOOK-AHEAD / SELECTION BIAS"
    FAIL_FINAL_OOS = "FAIL — FINAL OOS INTEGRITY"
    UNRESOLVED = "UNRESOLVED"


class CandidateReconstructionSummary(BaseModel):
    candidate_id: str
    title: str
    reconstructed_dev_exp: float
    reconstructed_dev_net_r: float
    reconstructed_dev_trades: int
    reconstructed_dev_wr: float
    reconstructed_dev_pf: float
    reconstructed_prelim_exp: float
    reconstructed_prelim_net_r: float
    reconstructed_prelim_trades: int
    reconstructed_prelim_wr: float
    reconstructed_prelim_pf: float
    reconstructed_positive_windows: int
    reconstructed_trade_reduction_pct: float
    stored_prelim_exp: float
    stored_prelim_net_r: float
    is_exact_match: bool


class SameCandleAuditResult(BaseModel):
    total_trades: int
    entry_bar_exits_count: int
    entry_bar_exits_pct: float
    entry_bar_sl_count: int
    entry_bar_tp1_count: int
    entry_bar_conflict_count: int  # both SL and TP price touched on entry bar
    standard_policy_net_r: float
    conservative_policy_net_r: float
    delta_net_r: float


class ConcurrencyAuditResult(BaseModel):
    total_signals: int
    signals_during_idle: int
    signals_during_active_trade: int
    signals_during_pending_wait: int
    executed_trades: int
    cancelled_by_concurrency: int
    concurrency_violation_count: int = 0


class HoldingTimeAuditResult(BaseModel):
    origin_convention: str  # "ENTRY_TIME" vs "SIGNAL_TIME"
    trade_count: int
    net_r: float
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    expired_count: int
    delta_r_vs_entry_time: float


class NegativeControlResult(BaseModel):
    control_name: str
    seed: int
    trade_count: int
    win_rate_pct: float
    net_r: float
    expectancy_r: float
    profit_factor: float
    positive_windows: int
    h006_outperformance_r: float


class TimingPerturbationCell(BaseModel):
    retrace_atr: float
    max_wait_minutes: int
    dev_trades: int
    dev_expectancy_r: float
    dev_pf: float
    prelim_trades: int
    prelim_expectancy_r: float
    prelim_pf: float
    prelim_net_r: float
    positive_windows: int
    trade_reduction_pct: float


class PriceDegradationCell(BaseModel):
    adverse_slippage_atr: float
    adverse_slippage_dollars: float
    prelim_trades: int
    prelim_win_rate_pct: float
    prelim_expectancy_r: float
    prelim_profit_factor: float
    prelim_net_r: float
    delta_net_r: float
    positive_windows: int


class SpreadSensitivityCell(BaseModel):
    spread_dollars: float
    prelim_trades: int
    prelim_win_rate_pct: float
    prelim_expectancy_r: float
    prelim_profit_factor: float
    prelim_net_r: float
    delta_net_r: float
    positive_windows: int
