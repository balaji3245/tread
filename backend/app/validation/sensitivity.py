import copy
from typing import Any, Dict, List, Optional

from app.backtest_models import BacktestConfig
from app.backtester import BacktestReplayEngine
from app.validation.validation_models import (
    ExitSensitivityItem,
    SpreadSensitivityItem,
    ThresholdSensitivityItem,
)


def run_spread_sensitivity(
    candles_1m: List[Dict[str, Any]],
    candles_5m: List[Dict[str, Any]],
    base_config: BacktestConfig,
    spread_values: List[float],
    precomputed_signals: Optional[Any] = None
) -> List[SpreadSensitivityItem]:
    """
    Run controlled spread sensitivity matrix across specified fixed spread values.
    Measures execution cost resilience of the baseline signal engine.
    """
    if precomputed_signals is None:
        precomputed_signals = BacktestReplayEngine(config=base_config).precompute_signals(candles_1m, candles_5m)

    results: List[SpreadSensitivityItem] = []

    for s_val in spread_values:
        cfg = copy.deepcopy(base_config)
        cfg.assumed_spread = float(s_val)
        cfg.execution_mode = "fixed_spread"

        engine = BacktestReplayEngine(config=cfg)
        resp = engine.run_backtest(candles_1m=candles_1m, candles_5m=candles_5m, precomputed_signals=precomputed_signals)
        stats = resp.statistics

        results.append(
            SpreadSensitivityItem(
                spread=round(s_val, 2),
                trades=stats.total_trades,
                win_rate=stats.win_rate,
                average_r=stats.average_r,
                total_r=stats.total_r,
                profit_factor=stats.profit_factor if stats.profit_factor > 0 else None,
                max_drawdown_usd=stats.max_drawdown
            )
        )

    return results


def run_threshold_sensitivity(
    candles_1m: List[Dict[str, Any]],
    candles_5m: List[Dict[str, Any]],
    base_config: BacktestConfig,
    threshold_values: List[int],
    small_sample_threshold: int = 30,
    precomputed_signals: Optional[Any] = None
) -> List[ThresholdSensitivityItem]:
    """
    Run signal threshold sensitivity matrix (e.g. 7, 8, 9, 10).
    Flags small sample sizes to prevent overconfidence in low-sample subsets.
    """
    if precomputed_signals is None:
        precomputed_signals = BacktestReplayEngine(config=base_config).precompute_signals(candles_1m, candles_5m)

    results: List[ThresholdSensitivityItem] = []

    for t_val in threshold_values:
        cfg = copy.deepcopy(base_config)
        cfg.signal_threshold = int(t_val)

        engine = BacktestReplayEngine(config=cfg)
        resp = engine.run_backtest(candles_1m=candles_1m, candles_5m=candles_5m, precomputed_signals=precomputed_signals)
        stats = resp.statistics

        is_small = stats.total_trades < small_sample_threshold
        note = (
            f"Small sample ({stats.total_trades} trades < {small_sample_threshold}) — interpret cautiously"
            if is_small
            else None
        )

        results.append(
            ThresholdSensitivityItem(
                threshold=int(t_val),
                signals=stats.total_signals,
                trades=stats.total_trades,
                win_rate=stats.win_rate,
                average_r=stats.average_r,
                total_r=stats.total_r,
                profit_factor=stats.profit_factor if stats.profit_factor > 0 else None,
                max_drawdown_usd=stats.max_drawdown,
                sample_size_warning=is_small,
                sample_size_note=note
            )
        )

    return results


def run_exit_sensitivity(
    candles_1m: List[Dict[str, Any]],
    candles_5m: List[Dict[str, Any]],
    base_config: BacktestConfig,
    precomputed_signals: Optional[Any] = None
) -> List[ExitSensitivityItem]:
    """
    Run predefined ATR exit sensitivity matrix across 5 standard risk/reward profiles.
    Evaluates strategy sensitivity to reasonable exit multiplier assumptions.
    """
    if precomputed_signals is None:
        precomputed_signals = BacktestReplayEngine(config=base_config).precompute_signals(candles_1m, candles_5m)

    cases = [
        ("Case A", "SL 0.75 / TP 1.00", 0.75, 1.0, 1.0),
        ("Case B", "SL 1.00 / TP 1.00 (1:1)", 1.0, 1.0, 1.0),
        ("Case C", "SL 1.00 / TP 1.50 (1:1.5)", 1.0, 1.5, 1.5),
        ("Case D", "SL 1.00 / TP 2.00 (1:2)", 1.0, 2.0, 2.0),
        ("Case E", "SL 1.50 / TP 2.00", 1.5, 2.0, 2.0),
    ]

    results: List[ExitSensitivityItem] = []

    for case_id, label, sl_mult, tp1_mult, tp2_mult in cases:
        cfg = copy.deepcopy(base_config)
        cfg.sl_atr_multiplier = sl_mult
        cfg.tp1_atr_multiplier = tp1_mult
        cfg.tp2_atr_multiplier = tp2_mult

        engine = BacktestReplayEngine(config=cfg)
        resp = engine.run_backtest(candles_1m=candles_1m, candles_5m=candles_5m, precomputed_signals=precomputed_signals)
        stats = resp.statistics

        results.append(
            ExitSensitivityItem(
                case_id=case_id,
                label=label,
                sl_atr_multiplier=sl_mult,
                tp1_atr_multiplier=tp1_mult,
                tp2_atr_multiplier=tp2_mult,
                trades=stats.total_trades,
                win_rate=stats.win_rate,
                average_r=stats.average_r,
                total_r=stats.total_r,
                profit_factor=stats.profit_factor if stats.profit_factor > 0 else None,
                max_drawdown_usd=stats.max_drawdown
            )
        )

    return results
