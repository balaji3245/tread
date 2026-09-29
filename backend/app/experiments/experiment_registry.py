"""
Phase 6: Experiment Registry
Central catalogue of evidence-backed single-variable strategy experiments.
Each experiment targets an empirically identified forensic failure mode.
"""
from typing import Dict, List, Optional
from app.experiments.experiment_models import (
    ExperimentDefinition,
    ExperimentVariableType,
    SingleVariableModification,
)


EXPERIMENT_REGISTRY: Dict[str, ExperimentDefinition] = {
    "ABL-001": ExperimentDefinition(
        experiment_id="ABL-001",
        title="Ablation: Remove RSI Confirmation",
        hypothesis="RSI 14 momentum confirmation does not provide positive edge and may filter out valid trend continuation entries.",
        failure_mechanism="INDICATOR_CONFIRMATION_EFFICACY",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.INDICATOR_ABLATION,
            target_rule="rsi_confirmation",
            baseline_value="active",
            experimental_value="removed",
            parameter_name="enable_rsi_filter",
            description="Remove 1m/5m RSI momentum requirement from setup scoring."
        ),
        rationale_from_forensics="Forensic analysis revealed RSI confirmation present vs absent showed nearly identical win rate (42.3% vs 42.2%), indicating minimal marginal information."
    ),
    "ABL-002": ExperimentDefinition(
        experiment_id="ABL-002",
        title="Ablation: Remove MACD Confirmation",
        hypothesis="MACD histogram confirmation adds lagging bias without improving outcome distribution.",
        failure_mechanism="INDICATOR_CONFIRMATION_EFFICACY",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.INDICATOR_ABLATION,
            target_rule="macd_confirmation",
            baseline_value="active",
            experimental_value="removed",
            parameter_name="enable_macd_filter",
            description="Remove 5m MACD histogram requirement from setup scoring."
        ),
        rationale_from_forensics="Forensic condition analysis showed MACD histogram confirmation absent had slightly higher average R (+0.004R) than when present."
    ),
    "EXP-001": ExperimentDefinition(
        experiment_id="EXP-001",
        title="Spread Friction Filter",
        hypothesis="Rejecting entries when market spread exceeds $0.40 prevents prohibitive cost erosion.",
        failure_mechanism="HIGH_SPREAD_EROSION",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.FILTER,
            target_rule="spread_threshold",
            baseline_value=0.30,
            experimental_value=0.40,
            parameter_name="max_allowed_spread",
            description="Filter out signals generated when live/tick spread exceeds $0.40."
        ),
        rationale_from_forensics="48.8% of losing trades experienced favorable price movement > 1.5x spread before being stopped out by transaction friction."
    ),
    "EXP-002": ExperimentDefinition(
        experiment_id="EXP-002",
        title="Strict 5m Trend Alignment Filter",
        hypothesis="Requiring signal direction to strictly match higher-timeframe 5m trend reduces early reversal losses.",
        failure_mechanism="TREND_MISMATCH",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.FILTER,
            target_rule="strict_5m_trend",
            baseline_value="optional_countertrend",
            experimental_value="strict_trend_only",
            parameter_name="require_5m_trend_alignment",
            description="Reject LONG signals when 5m trend is not BULLISH; reject SHORT signals when 5m trend is not BEARISH."
        ),
        rationale_from_forensics="Trend-aligned setups achieved +0.045R higher average return, while counter-trend setups accounted for 38.2% of immediate early reversals."
    ),
    "EXP-003": ExperimentDefinition(
        experiment_id="EXP-003",
        title="Range Regime Consolidation Filter",
        hypothesis="Suppressing signal generation during identified 5m RANGE regimes avoids whipsaws in sideways markets.",
        failure_mechanism="RANGE_NOISE",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.FILTER,
            target_rule="range_filter",
            baseline_value="allow_range",
            experimental_value="reject_range",
            parameter_name="filter_range_regime",
            description="Reject signals when higher-timeframe 5m market regime is classified as RANGE."
        ),
        rationale_from_forensics="RANGE regime trades exhibited the lowest profit factor (0.76) and high loss clustering during mid-day consolidation."
    ),
    "EXP-004": ExperimentDefinition(
        experiment_id="EXP-004",
        title="Support & Resistance Clearance Filter",
        hypothesis="Rejecting entries within 0.4 ATR of opposing key support/resistance levels prevents buying tops and selling bottoms.",
        failure_mechanism="RESISTANCE_FAILURE & SUPPORT_FAILURE",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.FILTER,
            target_rule="overextended_entry_filter",
            baseline_value=0.0,
            experimental_value=0.40,
            parameter_name="min_sr_clearance_atr",
            description="Require at least 0.4 ATR clearance before opposing 1m/5m support or resistance levels."
        ),
        rationale_from_forensics="5,360 losing trades (40.1% of losses) failed directly against immediate structural support or resistance levels."
    ),
    "EXP-005": ExperimentDefinition(
        experiment_id="EXP-005",
        title="Stop Loss / Target Expansion (SL 1.5 ATR / TP 2.0 ATR)",
        hypothesis="Widening stop loss to 1.5 ATR and target to 2.0 ATR reduces premature noise stops while maintaining positive asymmetric R:R.",
        failure_mechanism="SL_THEN_TP_REVERSAL",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.EXIT_MODEL,
            target_rule="exit_multipliers",
            baseline_value={"sl_atr_multiplier": 1.0, "tp1_atr_multiplier": 1.0, "tp2_atr_multiplier": 2.0},
            experimental_value={"sl_atr_multiplier": 1.5, "tp1_atr_multiplier": 2.0, "tp2_atr_multiplier": 2.0},
            parameter_name="exit_atr_multipliers",
            description="Set SL multiplier to 1.5 ATR and TP multiplier to 2.0 ATR."
        ),
        rationale_from_forensics="65.5% of stopped trades (8,730 trades) subsequently reached +1.0R favorable price within 60 minutes, proving 1.0 ATR stop is frequently too tight for XAUUSD M1 noise."
    ),
    "EXP-006": ExperimentDefinition(
        experiment_id="EXP-006",
        title="Score Confluence Threshold (Score >= 8)",
        hypothesis="Raising signal strength threshold from 7 to 8/10 filters out marginal low-confluence setups.",
        failure_mechanism="SCORE_CONFLUENCE",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.SCORE_THRESHOLD,
            target_rule="signal_threshold",
            baseline_value=7,
            experimental_value=8,
            parameter_name="signal_threshold",
            description="Require setup strength of at least 8 out of 10."
        ),
        rationale_from_forensics="Score 7 setups accounted for 62% of trades but had lower win rate (41.6%) vs Score 8 setups (44.8%)."
    ),
    "EXP-007": ExperimentDefinition(
        experiment_id="EXP-007",
        title="ATR Stop (SL 1.5 ATR / TP 2.0 ATR) + Breakeven at +1.0R",
        hypothesis="Moving stop-loss to entry price once favorable excursion reaches +1.0R protects open profits and eliminates tail losses on winning moves.",
        failure_mechanism="SL_THEN_TP_REVERSAL & EARLY_NOISE",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.EXIT_MODEL,
            target_rule="breakeven_trigger_r",
            baseline_value={"sl_atr_multiplier": 1.0, "tp1_atr_multiplier": 1.0, "tp2_atr_multiplier": 2.0, "breakeven_trigger_r": None},
            experimental_value={"sl_atr_multiplier": 1.5, "tp1_atr_multiplier": 2.0, "tp2_atr_multiplier": 2.0, "breakeven_trigger_r": 1.0},
            parameter_name="breakeven_trigger_r",
            description="SL 1.5 ATR, TP 2.0 ATR. Move SL to entry price once price reaches +1.0R favorable excursion."
        ),
        rationale_from_forensics="Over 80% of generated baseline signals reach >= +1.0R favorable excursion, yet 57.7% of trades end in losses due to premature fixed SL stop-outs or deep retracements."
    ),
    "EXP-008": ExperimentDefinition(
        experiment_id="EXP-008",
        title="ATR Trailing Stop (1.0 ATR distance after +1.0R)",
        hypothesis="Trailing stop loss dynamically at a fixed 1.0 ATR distance once price reaches +1.0R locks in gains during multi-leg trend continuations.",
        failure_mechanism="MFE_RETRACTION",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.EXIT_MODEL,
            target_rule="trailing_stop_atr",
            baseline_value={"sl_atr_multiplier": 1.0, "tp1_atr_multiplier": 1.0, "tp2_atr_multiplier": 2.0, "trailing_stop_atr": None},
            experimental_value={"sl_atr_multiplier": 1.5, "tp1_atr_multiplier": 2.0, "tp2_atr_multiplier": 2.0, "trailing_trigger_r": 1.0, "trailing_stop_atr": 1.0},
            parameter_name="trailing_stop_atr",
            description="SL 1.5 ATR, TP 2.0 ATR. Activate 1.0 ATR trailing stop once price reaches +1.0R favorable excursion."
        ),
        rationale_from_forensics="Winning trades reach an average peak MFE of 1.53R before exiting, indicating potential to lock in trailing profits on retracing trends."
    ),
    "EXP-009": ExperimentDefinition(
        experiment_id="EXP-009",
        title="Overextension Filter (5m EMA 50 Distance <= 2.0 ATR)",
        hypothesis="Rejecting entries when price is overextended (> 2.0 ATR away from 5m EMA 50) prevents buying tops and selling bottoms in exhausted trends.",
        failure_mechanism="MOMENTUM_EXHAUSTION",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.FILTER,
            target_rule="overextension_filter",
            baseline_value="allow_all",
            experimental_value=2.0,
            parameter_name="max_ema50_dist_atr",
            description="Reject LONG if price > 2.0 ATR above 5m EMA 50; reject SHORT if price > 2.0 ATR below 5m EMA 50."
        ),
        rationale_from_forensics="Momentum exhaustion was tagged as a primary failure mode in losing trades where price was > 2.0 ATR extended from the 5m EMA 50."
    ),
    "EXP-010": ExperimentDefinition(
        experiment_id="EXP-010",
        title="Opposing S/R Proximity Filter (Clearance > 0.5 ATR)",
        hypothesis="Rejecting entries within <= 0.5 ATR of opposing major support or resistance prevents entering directly into immediate structural barrier reversals.",
        failure_mechanism="RESISTANCE_FAILURE & SUPPORT_FAILURE",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.FILTER,
            target_rule="sr_proximity_filter",
            baseline_value=0.0,
            experimental_value=0.50,
            parameter_name="min_opposing_sr_clearance_atr",
            description="Reject LONG when opposing resistance is <= 0.5 ATR away; reject SHORT when opposing support is <= 0.5 ATR away."
        ),
        rationale_from_forensics="5,360 baseline losing trades (40.1% of losses) failed directly against immediate opposing support or resistance levels."
    ),
    "EXP-011": ExperimentDefinition(
        experiment_id="EXP-011",
        title="Time-Based Invalidation (MFE < 0.25R after 10m)",
        hypothesis="Closing trades that show stagnant/no favorable excursion (MFE < 0.25R) by 10 minutes cuts low-conviction drift trades before full stop-out.",
        failure_mechanism="EARLY_NOISE & DRIFT_STAGNATION",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.EXIT_MODEL,
            target_rule="time_invalidation",
            baseline_value={"time_invalidation_minutes": None, "time_invalidation_min_mfe_r": None},
            experimental_value={"sl_atr_multiplier": 1.5, "tp1_atr_multiplier": 2.0, "tp2_atr_multiplier": 2.0, "time_invalidation_minutes": 10, "time_invalidation_min_mfe_r": 0.25},
            parameter_name="time_invalidation",
            description="SL 1.5 ATR, TP 2.0 ATR. If peak MFE is < 0.25R after 10 minutes of holding, close trade immediately at market close."
        ),
        rationale_from_forensics="Losing trades display an average peak MFE of only 0.29R and median MFE of 0.18R, stagnating early before hitting adverse excursion."
    ),
    "EXP-012": ExperimentDefinition(
        experiment_id="EXP-012",
        title="Momentum Exhaustion Guard (Overextended + Near Opposing S/R)",
        hypothesis="Rejecting entries only when BOTH extreme price extension (> 2.0 ATR from 5m EMA 50) and opposing S/R proximity (<= 0.5 ATR) occur avoids false breakouts without overfiltering.",
        failure_mechanism="MOMENTUM_EXHAUSTION_GUARD",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.FILTER,
            target_rule="momentum_exhaustion_guard",
            baseline_value="allow_all",
            experimental_value={"max_ema50_dist_atr": 2.0, "min_sr_clearance_atr": 0.5},
            parameter_name="momentum_exhaustion_guard",
            description="Reject LONG if > 2.0 ATR above 5m EMA 50 AND resistance <= 0.5 ATR. Reject SHORT if > 2.0 ATR below 5m EMA 50 AND support <= 0.5 ATR."
        ),
        rationale_from_forensics="Compound forensic label isolating the highest-risk structural trap setups identified in Phase 6 diagnostics."
    )
}


def get_experiment_by_id(experiment_id: str) -> Optional[ExperimentDefinition]:
    """Retrieve an experiment definition by its unique identifier."""
    return EXPERIMENT_REGISTRY.get(experiment_id.upper())


def list_all_experiments() -> List[ExperimentDefinition]:
    """Return all registered experiment definitions in chronological order."""
    return list(EXPERIMENT_REGISTRY.values())
