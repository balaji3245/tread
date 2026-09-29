export interface MarketTick {
  symbol: string;
  bid: number;
  ask: number;
  spread: number;
  timestamp: number;
  timestampISO: string;
}

export interface Candle {
  time: number; // Unix timestamp in seconds for lightweight-charts
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface SymbolInfo {
  symbol: string;
  description?: string;
  digits: number;
  point: number;
  spread?: number;
  currency_base?: string;
  currency_profit?: string;
  is_mock?: boolean;
}

export interface HealthStatus {
  status: "ok" | "degraded";
  mt5_connected: boolean;
  is_mock: boolean;
  symbol: string | null;
  timestamp: number;
  message: string;
}

export type Timeframe = "1m" | "5m";

export type ConnectionState = "CONNECTING" | "CONNECTED" | "DISCONNECTED" | "RECONNECTING";

export interface WsStatusData {
  mt5_connected: boolean;
  symbol: string | null;
  is_mock: boolean;
  message: string;
}

export type SignalType = "LONG_SETUP" | "SHORT_SETUP" | "WAIT";

export interface PriceLevel {
  price: number;
  type: "support" | "resistance";
  strength: number;
}

export interface SignalIndicators {
  ema9_1m?: number | null;
  ema21_1m?: number | null;
  ema50_1m?: number | null;

  ema9_5m?: number | null;
  ema21_5m?: number | null;
  ema50_5m?: number | null;

  rsi_1m?: number | null;
  rsi_5m?: number | null;

  macd_1m?: number | null;
  macdSignal_1m?: number | null;
  macdHist_1m?: number | null;

  atr_1m?: number | null;
  atr_5m?: number | null;

  vwap_1m?: number | null;
}

export interface MarketSignal {
  symbol: string;
  type: SignalType;
  timeframe: string;
  generatedAt: number;
  strength: number;
  maxStrength: number;
  price: number;
  trend_5m: "BULLISH" | "BEARISH" | "RANGE";
  structure_1m: "BULLISH" | "BEARISH" | "RANGE";
  reasons: string[];
  warnings: string[];
  indicators: SignalIndicators;
  supportLevels: PriceLevel[];
  resistanceLevels: PriceLevel[];
}

export interface AnalysisResponse {
  symbol: string;
  signal: MarketSignal;
  timestamp: number;
}

export type WsMessage =
  | { type: "tick"; data: MarketTick }
  | { type: "candle"; timeframe: Timeframe; data: Candle }
  | { type: "status"; data: WsStatusData }
  | { type: "analysis"; data: { symbol: string; signal: MarketSignal } };

export interface BacktestConfig {
  symbol?: string;
  start_date?: string | null;
  end_date?: string | null;
  timeframe_primary?: string;
  timeframe_trigger?: string;
  initial_capital?: number;
  risk_per_trade_usd?: number;
  signal_threshold?: number;
  sl_atr_multiplier?: number;
  tp1_atr_multiplier?: number;
  tp2_atr_multiplier?: number;
  max_holding_minutes?: number;
  assumed_spread?: number;
  execution_mode?: "fixed_spread" | "historical_spread";
  same_candle_policy?: "stop_first" | "tp_first";
  max_concurrent_trades?: number;
  enable_long?: boolean;
  enable_short?: boolean;
}

export interface BacktestTrade {
  id: string;
  symbol: string;
  direction: "LONG" | "SHORT";
  signal_time: number;
  signal_time_iso: string;
  entry_time: number;
  entry_time_iso: string;
  exit_time: number;
  exit_time_iso: string;
  signal_strength: number;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  exit_price: number;
  result: "TP1" | "TP2" | "STOP_LOSS" | "EXPIRED";
  pnl: number;
  r_multiple: number;
  holding_minutes: number;
  exit_reason: string;
  entry_reason?: string;
  market_regime?: string;
  session?: string;
}

export interface EquityPoint {
  time: number;
  time_iso: string;
  equity: number;
  drawdown: number;
  drawdown_pct: number;
}

export interface StrengthStat {
  strength: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_r: number;
  average_r: number;
  profit_factor: number;
}

export interface DirectionStat {
  direction: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_r: number;
  average_r: number;
  profit_factor: number;
  max_drawdown: number;
}

export interface SessionStat {
  session: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_r: number;
  average_r: number;
}

export interface BacktestStatistics {
  total_signals: number;
  total_trades: number;
  long_trades: number;
  short_trades: number;
  winning_trades: number;
  losing_trades: number;
  expired_trades: number;
  win_rate: number;
  total_r: number;
  average_r: number;
  median_r: number;
  profit_factor: number;
  average_win_r: number;
  average_loss_r: number;
  largest_win_r: number;
  largest_loss_r: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  average_holding_minutes: number;
  longest_holding_minutes: number;
  by_strength: StrengthStat[];
  by_direction: Record<string, DirectionStat>;
  by_session: SessionStat[];
  by_regime: Record<string, any>;
}

export interface BacktestResponse {
  symbol: string;
  period: {
    start: string;
    end: string;
    total_1m_candles?: string;
    total_5m_candles?: string;
  };
  configuration: Record<string, any>;
  execution_metadata: Record<string, any>;
  statistics: BacktestStatistics;
  trades: BacktestTrade[];
  equity_curve: EquityPoint[];
}

// ==========================================
// PHASE 4 & 5: STRATEGY VALIDATION & DATA EXPANSION
// ==========================================

export interface DatasetCoverage {
  requested_start_iso: string;
  requested_end_iso: string;
  actual_start_iso: string;
  actual_end_iso: string;
  requested_days: number;
  available_days: number;
  candle_count_1m: number;
  candle_count_5m: number;
  data_complete: boolean;
  coverage_status: "INSUFFICIENT_HISTORY" | "LIMITED_HISTORY" | "12_MONTH_HISTORY_AVAILABLE" | string;
  dataset_hash: string;
  source: string;
}

export interface DataQualityReport {
  symbol: string;
  total_1m_candles: number;
  total_5m_candles: number;
  actual_start_ts: number;
  actual_end_ts: number;
  actual_start_iso: string;
  actual_end_iso: string;
  history_days: number;
  requested_days: number;
  is_complete: boolean;
  coverage_status: string;
  duplicate_count_1m: number;
  duplicate_count_5m: number;
  invalid_candles_count_1m: number;
  invalid_candles_count_5m: number;
  non_monotonic_count_1m: number;
  non_monotonic_count_5m: number;
  unexpected_gaps_count: number;
  expected_market_gaps_count: number;
  alignment_status: "PASS" | "WARN" | "FAIL";
  alignment_details: string;
  timezone: string;
  dataset_hash: string;
  is_clean: boolean;
  summary_notes: string[];
}

export interface ValidationStatus {
  status: "VALIDATION_SUFFICIENT_COVERAGE" | "INSUFFICIENT_OOS_WINDOWS" | "LIMITED_HISTORY" | "INSUFFICIENT_HISTORY" | string;
  history_days: number;
  oos_windows: number;
  minimum_oos_windows: number;
  baseline_evaluated: boolean;
  final_oos_locked: boolean;
  parameter_optimization: boolean;
  notes: string[];
}

export interface OosConsistencyMetrics {
  positive_month_fraction: number;
  positive_oos_window_fraction: number;
  median_monthly_r: number;
  median_oos_window_r: number;
  std_dev_monthly_r: number;
  std_dev_oos_r: number;
  largest_positive_month?: string | null;
  largest_negative_month?: string | null;
  largest_positive_oos_window?: string | null;
  largest_negative_oos_window?: string | null;
  top_month_removed_total_r: number;
  top_month_removed_impact: string;
}

export interface HistoryStatusResponse {
  symbol: string;
  timeframes: {
    "1m": { start: string; end: string; candles: number };
    "5m": { start: string; end: string; candles: number };
  };
  history_days: number;
  coverage_status: string;
  data_quality: DataQualityReport;
  complete: boolean;
  dataset_hash: string;
}

export interface ValidationRequest {
  symbol?: string;
  start?: string | null;
  end?: string | null;
  months?: number | null;
  train_days?: number;
  validation_days?: number;
  step_days?: number;
  signal_threshold?: number;
  sl_atr_multiplier?: number;
  tp1_atr_multiplier?: number;
  tp2_atr_multiplier?: number;
  max_holding_minutes?: number;
  initial_capital?: number;
  risk_per_trade_usd?: number;
  assumed_spread?: number;
  execution_mode?: "fixed_spread" | "historical_spread";
  same_candle_policy?: "stop_first" | "tp_first";
  max_concurrent_trades?: number;
  spread_values?: number[];
  threshold_values?: number[];
  monte_carlo_simulations?: number;
  random_seed?: number;
  final_oos_locked?: boolean;
}

export interface PeriodMetricSummary {
  period_name: string;
  start_time: number;
  start_iso: string;
  end_time: number;
  end_iso: string;
  trades_count: number;
  signals_count: number;
  winning_trades: number;
  losing_trades: number;
  expired_trades: number;
  win_rate: number;
  total_r: number;
  average_r: number;
  median_r: number;
  profit_factor: number | null;
  gross_profit_usd: number;
  gross_loss_usd: number;
  average_win_r: number;
  average_loss_r: number;
  largest_win_r: number;
  largest_loss_r: number;
  max_drawdown_usd: number;
  max_drawdown_pct: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  avg_holding_minutes: number;
  long_trades: number;
  short_trades: number;
  long_win_rate: number;
  short_win_rate: number;
  long_total_r: number;
  short_total_r: number;
}

export interface WalkForwardWindowResult {
  window_index: number;
  train_start_iso: string;
  train_end_iso: string;
  train_metrics: PeriodMetricSummary;
  validation_start_iso: string;
  validation_end_iso: string;
  validation_metrics: PeriodMetricSummary;
  is_final_oos?: boolean;
}

export interface OutOfSampleSummary {
  oos_periods_count: number;
  positive_oos_periods: number;
  negative_oos_periods: number;
  profitable_period_fraction: number;
  total_oos_trades: number;
  total_oos_r: number;
  average_oos_r: number;
  oos_profit_factor: number | null;
  oos_max_drawdown_usd: number;
  oos_max_drawdown_pct: number;
  oos_expectancy: number;
  windows: PeriodMetricSummary[];
}

export interface SpreadSensitivityItem {
  spread: number;
  trades: number;
  win_rate: number;
  average_r: number;
  total_r: number;
  profit_factor: number | null;
  max_drawdown_usd: number;
}

export interface ThresholdSensitivityItem {
  threshold: number;
  signals: number;
  trades: number;
  win_rate: number;
  average_r: number;
  total_r: number;
  profit_factor: number | null;
  max_drawdown_usd: number;
  sample_size_warning: boolean;
  sample_size_note: string | null;
}

export interface ExitSensitivityItem {
  case_id: string;
  label: string;
  sl_atr_multiplier: number;
  tp1_atr_multiplier: number;
  tp2_atr_multiplier: number;
  trades: number;
  win_rate: number;
  average_r: number;
  total_r: number;
  profit_factor: number | null;
  max_drawdown_usd: number;
}

export interface MonthlyMetricItem {
  year_month: string;
  month_name: string;
  trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_r: number;
  average_r: number;
  profit_factor: number | null;
  max_drawdown_usd: number;
  long_trades: number;
  short_trades: number;
  candle_count_1m?: number;
  candle_count_5m?: number;
  data_completeness?: string;
}

export interface PeriodConcentration {
  total_r: number;
  top_1_month_r: number;
  top_1_month_pct: number;
  top_1_month_label: string;
  top_2_month_r: number;
  top_2_month_pct: number;
  top_3_month_r: number;
  top_3_month_pct: number;
  top_month_removed_total_r?: number;
  description: string;
}

export interface ExpectancyAnalysis {
  expectancy_per_trade: number;
  win_probability: number;
  loss_probability: number;
  avg_winning_r: number;
  avg_losing_r: number;
  risk_reward_ratio: number;
}

export interface DrawdownAnalysis {
  max_drawdown_usd: number;
  max_drawdown_pct: number;
  avg_drawdown_usd: number;
  num_drawdowns: number;
  longest_drawdown_duration_trades: number;
  max_losing_streak: number;
  avg_losing_streak: number;
  recovery_factor: number | null;
}

export interface MonteCarloDistribution {
  percentile_5: number;
  percentile_25: number;
  median: number;
  percentile_75: number;
  percentile_95: number;
}

export interface MonteCarloResult {
  simulations: number;
  random_seed: number | null;
  median_max_drawdown_usd: number;
  percentile_95_max_drawdown_usd: number;
  median_ending_r: number;
  percentile_5_ending_r: number;
  percentile_95_ending_r: number;
  max_observed_drawdown_usd: number;
  max_observed_losing_streak: number;
  drawdown_distribution: MonteCarloDistribution;
  ending_r_distribution: MonteCarloDistribution;
  disclaimer: string;
}

export interface DiagnosticFlag {
  code: string;
  severity: "INFO" | "WARNING" | "CAUTION";
  title: string;
  measured_evidence: string;
}

export interface RobustnessSummary {
  periods_tested: number;
  positive_periods: number;
  negative_periods: number;
  profitable_period_fraction: number;
  oos_periods_tested: number;
  oos_positive_periods: number;
  spread_sensitive: boolean;
  threshold_sensitive: boolean;
  exit_sensitive: boolean;
  flags: DiagnosticFlag[];
}

export interface ValidationResponse {
  validation_run_id: string;
  symbol: string;
  dataset_coverage: DatasetCoverage;
  data_quality: DataQualityReport;
  validation_status: ValidationStatus;
  oos_consistency: OosConsistencyMetrics;
  baseline_configuration: Record<string, any>;
  configuration_hash: string;
  overall_metrics: PeriodMetricSummary;
  expectancy: ExpectancyAnalysis;
  drawdown_analysis: DrawdownAnalysis;
  monthly: MonthlyMetricItem[];
  period_concentration: PeriodConcentration;
  walk_forward: WalkForwardWindowResult[];
  out_of_sample: OutOfSampleSummary;
  spread_sensitivity: SpreadSensitivityItem[];
  threshold_sensitivity_development: ThresholdSensitivityItem[];
  exit_sensitivity_development: ExitSensitivityItem[];
  direction_breakdown: Record<string, any>;
  session_breakdown: any[];
  regime_breakdown: Record<string, any>;
  monte_carlo: MonteCarloResult;
  diagnostics: DiagnosticFlag[];
  robustness_summary: RobustnessSummary;
  disclaimer: string;
}

export interface ValidationExportResponse {
  symbol: string;
  validation_run_id: string;
  configuration_hash: string;
  dataset_coverage: DatasetCoverage;
  data_quality: DataQualityReport;
  validation_status: ValidationStatus;
  json_data: ValidationResponse;
  csv_files: Record<string, string>;
}

// ==========================================
// PHASE 6: FORENSICS & EXPERIMENT TYPES
// ==========================================

export interface DistributionStats {
  metric_name: string;
  count: number;
  mean: number;
  median: number;
  std_dev: number;
  percentile_25: number;
  percentile_75: number;
  percentile_90: number;
  percentile_95: number;
  min_val?: number;
  max_val?: number;
}

export interface FailureCategorySummary {
  category: string;
  trade_count: number;
  pct_of_losses: number;
  average_r: number;
  average_mae_r: number;
  average_mfe_r: number;
  description: string;
}

export interface ScoreForensicsItem {
  score: number;
  direction: string;
  total_trades: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
  average_r: number;
  total_r: number;
  profit_factor: number | null;
  average_holding_minutes: number;
  avg_mae_r: number;
  avg_mfe_r: number;
}

export interface ConditionContributionItem {
  condition_name: string;
  description: string;
  occurrence_count: number;
  win_rate_when_present: number;
  avg_r_when_present: number;
  loss_rate_when_present: number;
  occurrence_count_absent: number;
  win_rate_when_absent: number;
  avg_r_when_absent: number;
  delta_win_rate: number;
  delta_avg_r: number;
}

export interface WinLossComparisonItem {
  feature_name: string;
  winning_distribution: DistributionStats;
  losing_distribution: DistributionStats;
  interpretation: string;
}

export interface HoldingTimeBucketItem {
  bucket_label: string;
  min_minutes: number;
  max_minutes: number;
  trades_count: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
  total_r: number;
  average_r: number;
  profit_factor: number | null;
}

export interface LossClusteringSummary {
  max_consecutive_losses: number;
  losses_by_session: Record<string, number>;
  losses_by_regime?: Record<string, number>;
  loss_rate_overall: number;
}

export interface CandidateHypothesisItem {
  hypothesis_id: string;
  title: string;
  failure_mechanism_addressed: string;
  empirical_evidence: string;
  proposed_rule_change: string;
  expected_impact: string;
}

export interface ForensicsReport {
  report_id: string;
  created_at_iso: string;
  dataset_hash: string;
  total_trades_analyzed: number;
  winning_trades: number;
  losing_trades: number;
  expired_trades: number;
  baseline_win_rate: number;
  baseline_average_r: number;
  baseline_total_r: number;
  baseline_profit_factor: number | null;
  overall_mae: DistributionStats;
  overall_mfe: DistributionStats;
  sl_to_tp_1r_reversal_count: number;
  sl_to_tp_1r_reversal_pct: number;
  sl_to_tp_2r_reversal_count: number;
  sl_to_tp_2r_reversal_pct: number;
  failure_categories: FailureCategorySummary[];
  score_forensics: ScoreForensicsItem[];
  condition_contributions: ConditionContributionItem[];
  win_loss_comparisons: WinLossComparisonItem[];
  holding_time_breakdown: HoldingTimeBucketItem[];
  loss_clustering: LossClusteringSummary;
  candidate_hypotheses: CandidateHypothesisItem[];
}

export interface ExperimentDeltaSummary {
  delta_trades: number;
  delta_win_rate_pct: number;
  delta_average_r: number;
  delta_total_r: number;
  delta_expectancy: number;
  delta_profit_factor: number;
  delta_max_drawdown_usd: number;
  delta_max_drawdown_pct: number;
  trade_reduction_pct: number;
}

export interface ExperimentWindowResult {
  window_index: number;
  is_final_oos: boolean;
  val_start_iso: string;
  val_end_iso: string;
  baseline_trades: number;
  baseline_win_rate: number;
  baseline_net_r: number;
  baseline_profit_factor: number | null;
  experiment_trades: number;
  experiment_win_rate: number;
  experiment_net_r: number;
  experiment_profit_factor: number | null;
  delta_r: number;
}

export interface SpreadRobustnessCheck {
  spread: number;
  baseline_win_rate: number;
  baseline_total_r: number;
  experiment_win_rate: number;
  experiment_total_r: number;
  delta_total_r: number;
  is_resilient: boolean;
}

export interface ExperimentResult {
  experiment_id: string;
  title: string;
  hypothesis: string;
  status: "DRAFT" | "DEVELOPMENT" | "OOS_SCREENING" | "REJECTED" | "NEEDS_MORE_DATA" | "PROMISING" | "FINAL_OOS_PENDING" | "ARCHIVED";
  decision: "REJECTED" | "NEEDS_MORE_DATA" | "PROMISING";
  baseline_version: string;
  configuration_hash: string;
  dataset_hash: string;
  executed_at_iso: string;
  development_period_label: string;
  development_baseline: PeriodMetricSummary;
  development_experiment: PeriodMetricSummary;
  development_deltas: ExperimentDeltaSummary;
  preliminary_oos_periods_count: number;
  preliminary_oos_baseline_r: number;
  preliminary_oos_experiment_r: number;
  preliminary_oos_baseline_wr: number;
  preliminary_oos_experiment_wr: number;
  preliminary_oos_baseline_pf: number | null;
  preliminary_oos_experiment_pf: number | null;
  preliminary_oos_deltas: ExperimentDeltaSummary;
  final_oos_locked: boolean;
  final_oos_evaluated: boolean;
  final_oos_baseline?: PeriodMetricSummary | null;
  final_oos_experiment?: PeriodMetricSummary | null;
  final_oos_deltas?: ExperimentDeltaSummary | null;
  walk_forward_windows: ExperimentWindowResult[];
  spread_robustness: SpreadRobustnessCheck[];
  acceptance_checks: {
    has_min_dev_trades: boolean;
    has_min_oos_trades: boolean;
    improved_oos_expectancy: boolean;
    improved_oos_profit_factor: boolean;
    drawdown_not_worsened: boolean;
  };
  decision_rationale: string;
  diagnostics: string[];
}

export interface AuditCheckItem {
  name: string;
  passed: boolean;
  status_label: "PASS" | "WARN" | "FAIL";
  evidence: string;
}

export interface ExperimentTradeReconciliation {
  baseline_total_signals: number;
  baseline_executed_trades: number;
  baseline_ignored_signals: number;
  experiment_executed_trades: number;
  removed_trades_count: number;
  changed_exit_trades_count: number;
  unchanged_trades_count: number;
}

export interface ExperimentAuditReport {
  experiment_id: string;
  title: string;
  baseline_version: string;
  dataset_hash: string;
  configuration_hash: string;
  audit_timestamp_iso: string;
  baseline_reproducible: boolean;
  experiment_reproducible: boolean;
  trade_set_verified: boolean;
  timing_verified: boolean;
  oos_integrity_verified: boolean;
  sample_size_valid: boolean;
  accounting_verified: boolean;
  status: "DRAFT" | "DEVELOPMENT" | "OOS_SCREENING" | "REJECTED" | "NEEDS_MORE_DATA" | "PROMISING" | "FINAL_OOS_PENDING" | "ARCHIVED";
  decision: "REJECTED" | "NEEDS_MORE_DATA" | "PROMISING";
  decision_rationale: string;
  attribution: string;
  checks: AuditCheckItem[];
  trade_reconciliation: ExperimentTradeReconciliation;
  development_baseline: PeriodMetricSummary;
  development_experiment: PeriodMetricSummary;
  development_deltas: ExperimentDeltaSummary;
  preliminary_oos_deltas: ExperimentDeltaSummary;
  walk_forward_windows: ExperimentWindowResult[];
  spread_robustness: SpreadRobustnessCheck[];
}

// ==========================================
// PHASE 6B: MAE / MFE EXCURSIONS & PATH TYPES
// ==========================================

export interface MfeReachByScoreItem {
  score: number;
  trade_count: number;
  p_reach_0_5r_pct: number;
  p_reach_1_0r_pct: number;
  p_reach_1_5r_pct: number;
  p_reach_2_0r_pct: number;
}

export interface MaeRecoveryItem {
  adverse_threshold_r: number;
  trades_reaching_count: number;
  pct_of_all_trades: number;
  later_reached_1r_count: number;
  later_reached_1r_pct: number;
  later_reached_2r_count: number;
  later_reached_2r_pct: number;
}

export interface TimeToAdverseBucketItem {
  bucket: string;
  trade_count: number;
  loss_pct: number;
  avg_mae_r: number;
  avg_mfe_r: number;
}

export interface ExcursionsForensicReport {
  dataset_hash: string;
  total_trades: number;
  mfe_reach_by_score: MfeReachByScoreItem[];
  mae_recovery_table: MaeRecoveryItem[];
  time_to_adverse_buckets: TimeToAdverseBucketItem[];
  early_noise_count: number;
  early_stopped_count: number;
  early_stopped_later_1r_pct: number;
  early_stopped_later_2r_pct: number;
  mfe_at_horizons_mean: Record<string, number>;
  mae_at_horizons_mean: Record<string, number>;
  time_to_mfe_mean: number;
  time_to_mae_mean: number;
  time_to_sl_mean: number;
  time_to_tp_mean: number;
  max_mfe_before_stop_mean: number;
  max_mae_before_recovery_mean: number;
}

export interface ExitPathPoint {
  minute: number;
  price: number;
  r: number;
}

export interface ExitPathSample {
  signal_time: number;
  direction: string;
  score: number;
  entry_price: number;
  exit_price: number;
  exit_reason: string;
  realized_r: number;
  mae_r: number;
  mfe_r: number;
  duration_minutes: number;
  path_points: ExitPathPoint[];
}
