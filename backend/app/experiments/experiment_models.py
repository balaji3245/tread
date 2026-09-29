"""
Phase 6: Controlled Experiment Models
Data contracts for single-variable strategy hypotheses, acceptance criteria,
walk-forward OOS evaluations, delta metrics, and robustness checks.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.backtest_models import BacktestConfig
from app.validation.validation_models import PeriodMetricSummary, WalkForwardWindowResult


class ExperimentStatus(str, Enum):
    DRAFT = "DRAFT"
    DEVELOPMENT = "DEVELOPMENT"
    OOS_SCREENING = "OOS_SCREENING"
    REJECTED = "REJECTED"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"
    PROMISING = "PROMISING"
    FINAL_OOS_PENDING = "FINAL_OOS_PENDING"
    ARCHIVED = "ARCHIVED"


class ExperimentDecision(str, Enum):
    REJECTED = "REJECTED"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"
    PROMISING = "PROMISING"
    FINAL_OOS_PENDING = "FINAL_OOS_PENDING"


class ExperimentVariableType(str, Enum):
    FILTER = "FILTER"
    EXIT_MODEL = "EXIT_MODEL"
    SCORE_THRESHOLD = "SCORE_THRESHOLD"
    INDICATOR_ABLATION = "INDICATOR_ABLATION"


class SingleVariableModification(BaseModel):
    """Encapsulates strictly ONE strategy rule change to prevent multi-variable confounding."""
    variable_type: ExperimentVariableType
    target_rule: str
    baseline_value: Any
    experimental_value: Any
    parameter_name: str
    description: str


class DeltaMetrics(BaseModel):
    """Exact difference between experimental metrics and baseline metrics."""
    delta_trades: int
    delta_win_rate_pct: float
    delta_average_r: float
    delta_total_r: float
    delta_expectancy: float
    delta_profit_factor: Optional[float] = None
    delta_max_drawdown_usd: float
    delta_max_drawdown_pct: float
    trade_reduction_pct: float


class ExperimentSpreadRobustness(BaseModel):
    """Robustness testing across spread perturbations ($0.20, $0.30, $0.50)."""
    spread: float
    baseline_win_rate: float
    baseline_total_r: float
    experiment_win_rate: float
    experiment_total_r: float
    delta_total_r: float
    is_resilient: bool


class ExperimentDefinition(BaseModel):
    """Specification of an evidence-backed single-variable experiment."""
    experiment_id: str
    title: str
    hypothesis: str
    failure_mechanism: str
    baseline_version: str = "phase6-baseline-v1"
    modification: SingleVariableModification
    rationale_from_forensics: str
    created_at_iso: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExperimentResult(BaseModel):
    """Immutable output of an executed controlled experiment."""
    experiment_id: str
    title: str
    hypothesis: str
    status: ExperimentStatus
    decision: ExperimentDecision
    baseline_version: str
    configuration_hash: str
    dataset_hash: str
    executed_at_iso: str

    # Development (In-Sample) Metrics (First 90 Days)
    development_period_label: str
    development_baseline: PeriodMetricSummary
    development_experiment: PeriodMetricSummary
    development_deltas: DeltaMetrics

    # Preliminary Out-of-Sample (OOS Windows #1 to #8)
    preliminary_oos_periods_count: int
    preliminary_oos_baseline_r: float
    preliminary_oos_experiment_r: float
    preliminary_oos_baseline_wr: float
    preliminary_oos_experiment_wr: float
    preliminary_oos_baseline_pf: Optional[float] = None
    preliminary_oos_experiment_pf: Optional[float] = None
    preliminary_oos_deltas: DeltaMetrics

    # Locked Final OOS (Window #9) — Evaluated ONLY if passing development + screening
    final_oos_locked: bool = True
    final_oos_evaluated: bool = False
    final_oos_baseline: Optional[PeriodMetricSummary] = None
    final_oos_experiment: Optional[PeriodMetricSummary] = None
    final_oos_deltas: Optional[DeltaMetrics] = None

    # Walk-forward windows
    walk_forward_windows: List[Dict[str, Any]] = Field(default_factory=list)

    # Robustness checks
    spread_robustness: List[ExperimentSpreadRobustness] = Field(default_factory=list)
    nearby_parameter_robustness: List[Dict[str, Any]] = Field(default_factory=list)

    # Diagnostic notes and decision rationale
    acceptance_checks: Dict[str, bool] = Field(default_factory=dict)
    decision_rationale: str
    diagnostics: List[str] = Field(default_factory=list)


class AuditCheckItem(BaseModel):
    name: str
    passed: bool
    status_label: Literal["PASS", "WARN", "FAIL"]
    evidence: str


class ExperimentTradeReconciliation(BaseModel):
    baseline_total_signals: int
    baseline_executed_trades: int
    baseline_ignored_signals: int
    experiment_executed_trades: int
    removed_trades_count: int
    changed_exit_trades_count: int
    unchanged_trades_count: int


class ExperimentAuditReport(BaseModel):
    experiment_id: str
    title: str
    baseline_version: str
    dataset_hash: str
    configuration_hash: str
    audit_timestamp_iso: str
    baseline_reproducible: bool
    experiment_reproducible: bool
    trade_set_verified: bool
    timing_verified: bool
    oos_integrity_verified: bool
    sample_size_valid: bool
    accounting_verified: bool
    status: ExperimentStatus
    decision: ExperimentDecision
    decision_rationale: str
    attribution: str
    checks: List[AuditCheckItem]
    trade_reconciliation: ExperimentTradeReconciliation
    development_baseline: PeriodMetricSummary
    development_experiment: PeriodMetricSummary
    development_deltas: DeltaMetrics
    preliminary_oos_deltas: DeltaMetrics
    walk_forward_windows: List[Dict[str, Any]]
    spread_robustness: List[ExperimentSpreadRobustness]
    nearby_parameter_robustness: List[Dict[str, Any]] = Field(default_factory=list)

