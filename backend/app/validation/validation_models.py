from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.historical_data_quality import DataQualityReport


class ValidationRequest(BaseModel):
    symbol: str = "XAUUSD"
    start: Optional[str] = None
    end: Optional[str] = None
    months: Optional[int] = Field(default=None, ge=1, le=24, description="Target historical months (e.g. 3, 6, 9, 12)")

    # Walk-forward parameters
    train_days: int = Field(default=90, ge=7, le=365, description="Days in each training window")
    validation_days: int = Field(default=30, ge=1, le=180, description="Days in each validation (OOS) window")
    step_days: int = Field(default=30, ge=1, le=180, description="Step size in days between consecutive windows")

    # Baseline configuration (Strictly preserved Phase 4 parameters)
    signal_threshold: int = Field(default=7, ge=1, le=10)
    sl_atr_multiplier: float = Field(default=1.0, gt=0)
    tp1_atr_multiplier: float = Field(default=1.0, gt=0)
    tp2_atr_multiplier: float = Field(default=2.0, gt=0)
    max_holding_minutes: int = Field(default=60, ge=5, le=1440)
    initial_capital: float = Field(default=10000.0, gt=0)
    risk_per_trade_usd: float = Field(default=100.0, gt=0)
    assumed_spread: float = Field(default=0.30, ge=0.0)
    execution_mode: Literal["fixed_spread", "historical_spread"] = "fixed_spread"
    same_candle_policy: Literal["stop_first", "tp_first"] = "stop_first"
    max_concurrent_trades: int = Field(default=1, ge=1, le=5)

    # Sensitivity matrix configuration
    spread_values: List[float] = Field(default=[0.0, 0.20, 0.30, 0.50, 0.75, 1.0])
    threshold_values: List[int] = Field(default=[7, 8, 9, 10])

    # Monte Carlo simulation configuration
    monte_carlo_simulations: int = Field(default=5000, ge=100, le=50000)
    random_seed: Optional[int] = Field(default=42)

    # Final OOS Locking
    final_oos_locked: bool = Field(default=True, description="Strict lock preventing OOS parameter mutation or tuning")


class DatasetCoverage(BaseModel):
    requested_start_iso: str
    requested_end_iso: str
    actual_start_iso: str
    actual_end_iso: str
    requested_days: int
    available_days: int
    candle_count_1m: int
    candle_count_5m: int
    data_complete: bool
    coverage_status: str  # "INSUFFICIENT_HISTORY" | "LIMITED_HISTORY" | "12_MONTH_HISTORY_AVAILABLE"
    dataset_hash: str
    source: str = "Exness MT5"


class ValidationStatus(BaseModel):
    status: str  # "VALIDATION_SUFFICIENT_COVERAGE" | "INSUFFICIENT_OOS_WINDOWS" | "LIMITED_HISTORY" | "INSUFFICIENT_HISTORY"
    history_days: int
    oos_windows: int
    minimum_oos_windows: int = 6
    baseline_evaluated: bool = True
    final_oos_locked: bool = True
    parameter_optimization: bool = False
    notes: List[str] = Field(default_factory=list)


class PeriodMetricSummary(BaseModel):
    period_name: str
    start_time: int
    start_iso: str
    end_time: int
    end_iso: str
    trades_count: int
    signals_count: int
    winning_trades: int
    losing_trades: int
    expired_trades: int
    win_rate: float
    total_r: float
    average_r: float
    median_r: float
    profit_factor: Optional[float] = None
    gross_profit_usd: float = 0.0
    gross_loss_usd: float = 0.0
    average_win_r: float = 0.0
    average_loss_r: float = 0.0
    largest_win_r: float = 0.0
    largest_loss_r: float = 0.0
    max_drawdown_usd: float
    max_drawdown_pct: float
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    avg_holding_minutes: float = 0.0
    long_trades: int = 0
    short_trades: int = 0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    long_total_r: float = 0.0
    short_total_r: float = 0.0
    is_equity_depleted: bool = False
    depletion_trade_index: Optional[int] = None
    equity_status: str = "SOLVENT"


class WalkForwardWindowResult(BaseModel):
    window_index: int
    train_start_iso: str
    train_end_iso: str
    train_metrics: PeriodMetricSummary
    validation_start_iso: str
    validation_end_iso: str
    validation_metrics: PeriodMetricSummary
    is_final_oos: bool = False


class OutOfSampleSummary(BaseModel):
    oos_periods_count: int
    positive_oos_periods: int
    negative_oos_periods: int
    profitable_period_fraction: float
    total_oos_trades: int
    total_oos_r: float
    average_oos_r: float
    oos_profit_factor: Optional[float] = None
    oos_max_drawdown_usd: float = 0.0
    oos_max_drawdown_pct: float = 0.0
    oos_expectancy: float = 0.0
    windows: List[PeriodMetricSummary] = Field(default_factory=list)


class OosConsistencyMetrics(BaseModel):
    positive_month_fraction: float
    positive_oos_window_fraction: float
    median_monthly_r: float
    median_oos_window_r: float
    std_dev_monthly_r: float
    std_dev_oos_r: float
    largest_positive_month: Optional[str] = None
    largest_negative_month: Optional[str] = None
    largest_positive_oos_window: Optional[str] = None
    largest_negative_oos_window: Optional[str] = None
    top_month_removed_total_r: float = 0.0
    top_month_removed_impact: str = ""


class SpreadSensitivityItem(BaseModel):
    spread: float
    trades: int
    win_rate: float
    average_r: float
    total_r: float
    profit_factor: Optional[float] = None
    max_drawdown_usd: float


class ThresholdSensitivityItem(BaseModel):
    threshold: int
    signals: int
    trades: int
    win_rate: float
    average_r: float
    total_r: float
    profit_factor: Optional[float] = None
    max_drawdown_usd: float
    sample_size_warning: bool
    sample_size_note: Optional[str] = None


class ExitSensitivityItem(BaseModel):
    case_id: str
    label: str
    sl_atr_multiplier: float
    tp1_atr_multiplier: float
    tp2_atr_multiplier: float
    trades: int
    win_rate: float
    average_r: float
    total_r: float
    profit_factor: Optional[float] = None
    max_drawdown_usd: float


class MonthlyMetricItem(BaseModel):
    year_month: str
    month_name: str
    trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_r: float
    average_r: float
    profit_factor: Optional[float] = None
    max_drawdown_usd: float
    long_trades: int
    short_trades: int
    candle_count_1m: int = 0
    candle_count_5m: int = 0
    data_completeness: str = "100%"


class PeriodConcentration(BaseModel):
    total_r: float
    top_1_month_r: float
    top_1_month_pct: float
    top_1_month_label: str
    top_2_month_r: float
    top_2_month_pct: float
    top_3_month_r: float
    top_3_month_pct: float
    top_month_removed_total_r: float = 0.0
    description: str


class ExpectancyAnalysis(BaseModel):
    expectancy_per_trade: float
    win_probability: float
    loss_probability: float
    avg_winning_r: float
    avg_losing_r: float
    risk_reward_ratio: float


class DrawdownAnalysis(BaseModel):
    max_drawdown_usd: float
    max_drawdown_pct: float
    avg_drawdown_usd: float
    num_drawdowns: int
    longest_drawdown_duration_trades: int
    max_losing_streak: int
    avg_losing_streak: float
    recovery_factor: Optional[float] = None
    is_equity_depleted: bool = False
    depletion_trade_index: Optional[int] = None
    equity_status: str = "SOLVENT"


class MonteCarloDistribution(BaseModel):
    percentile_5: float
    percentile_25: float
    median: float
    percentile_75: float
    percentile_95: float


class MonteCarloResult(BaseModel):
    simulations: int
    random_seed: Optional[int]
    median_max_drawdown_usd: float
    percentile_95_max_drawdown_usd: float
    median_ending_r: float
    percentile_5_ending_r: float
    percentile_95_ending_r: float
    max_observed_drawdown_usd: float
    max_observed_losing_streak: int
    drawdown_distribution: MonteCarloDistribution
    ending_r_distribution: MonteCarloDistribution
    disclaimer: str = (
        "Monte Carlo analysis evaluates sensitivity of historical trade-order outcomes. "
        "It is not a forecast of future market returns."
    )


class DiagnosticFlag(BaseModel):
    code: str
    severity: Literal["INFO", "WARNING", "CAUTION"]
    title: str
    measured_evidence: str


class RobustnessSummary(BaseModel):
    periods_tested: int
    positive_periods: int
    negative_periods: int
    profitable_period_fraction: float
    oos_periods_tested: int
    oos_positive_periods: int
    spread_sensitive: bool
    threshold_sensitive: bool
    exit_sensitive: bool
    flags: List[DiagnosticFlag] = Field(default_factory=list)


class ValidationResponse(BaseModel):
    validation_run_id: str = "VAL-20260926-001"
    symbol: str = "XAUUSD"
    dataset_coverage: DatasetCoverage
    data_quality: DataQualityReport
    validation_status: ValidationStatus
    oos_consistency: OosConsistencyMetrics
    baseline_configuration: Dict[str, Any]
    configuration_hash: str
    overall_metrics: PeriodMetricSummary
    expectancy: ExpectancyAnalysis
    drawdown_analysis: DrawdownAnalysis
    monthly: List[MonthlyMetricItem]
    period_concentration: PeriodConcentration
    walk_forward: List[WalkForwardWindowResult]
    out_of_sample: OutOfSampleSummary
    spread_sensitivity: List[SpreadSensitivityItem]
    threshold_sensitivity_development: List[ThresholdSensitivityItem]
    exit_sensitivity_development: List[ExitSensitivityItem]
    direction_breakdown: Dict[str, Any]
    session_breakdown: List[Any]
    regime_breakdown: Dict[str, Any]
    monte_carlo: MonteCarloResult
    diagnostics: List[DiagnosticFlag]
    robustness_summary: RobustnessSummary
    disclaimer: str = (
        "Historical strategy validation and walk-forward results are empirical measurements based "
        "on historical market data and stated execution assumptions. They do not guarantee future "
        "profitability and do not represent actual broker-executed trades."
    )
