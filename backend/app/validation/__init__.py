"""
Validation, Walk-Forward, Robustness, Sensitivity, and Monte Carlo Engine for XAUUSD.
"""

from app.validation.monte_carlo import run_monte_carlo
from app.validation.report_builder import export_validation_to_csv_dict
from app.validation.robustness import generate_robustness_flags, run_strategy_validation
from app.validation.sensitivity import (
    run_exit_sensitivity,
    run_spread_sensitivity,
    run_threshold_sensitivity,
)
from app.validation.validation_models import (
    DiagnosticFlag,
    DrawdownAnalysis,
    ExitSensitivityItem,
    ExpectancyAnalysis,
    MonthlyMetricItem,
    OutOfSampleSummary,
    PeriodConcentration,
    PeriodMetricSummary,
    RobustnessSummary,
    SpreadSensitivityItem,
    ThresholdSensitivityItem,
    ValidationRequest,
    ValidationResponse,
    WalkForwardWindowResult,
)
from app.validation.validation_statistics import (
    aggregate_out_of_sample,
    compute_drawdown_analysis,
    compute_expectancy,
    compute_monthly_metrics,
    compute_period_concentration,
    summarize_trades_slice,
)
from app.validation.walk_forward import (
    generate_walk_forward_slices,
    run_walk_forward_validation,
)

__all__ = [
    "ValidationRequest",
    "ValidationResponse",
    "PeriodMetricSummary",
    "WalkForwardWindowResult",
    "OutOfSampleSummary",
    "SpreadSensitivityItem",
    "ThresholdSensitivityItem",
    "ExitSensitivityItem",
    "MonthlyMetricItem",
    "PeriodConcentration",
    "ExpectancyAnalysis",
    "DrawdownAnalysis",
    "DiagnosticFlag",
    "RobustnessSummary",
    "run_strategy_validation",
    "run_walk_forward_validation",
    "generate_walk_forward_slices",
    "run_spread_sensitivity",
    "run_threshold_sensitivity",
    "run_exit_sensitivity",
    "run_monte_carlo",
    "export_validation_to_csv_dict",
    "summarize_trades_slice",
    "compute_expectancy",
    "compute_drawdown_analysis",
    "compute_monthly_metrics",
    "compute_period_concentration",
    "aggregate_out_of_sample",
    "generate_robustness_flags",
]
