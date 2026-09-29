import math
from datetime import datetime, timezone
import pytest

from app.validation.robustness import run_strategy_validation
from app.validation.validation_models import ValidationRequest
from app.validation.walk_forward import generate_walk_forward_slices


def _create_synthetic_candles(total_bars: int = 1200, start_price: float = 2000.0):
    """Generate synthetic synchronized 1m and 5m bars."""
    candles_1m = []
    candles_5m = []

    base_ts = 1700000000
    price = start_price

    # 1m bars
    for i in range(total_bars):
        t = base_ts + i * 60
        wave = math.sin(i / 20.0) * 5.0
        c_open = price + wave
        c_close = c_open + (0.4 if i % 2 == 0 else -0.4)
        c_high = max(c_open, c_close) + 0.8
        c_low = min(c_open, c_close) - 0.8

        bar = {
            "time": t,
            "open": round(c_open, 2),
            "high": round(c_high, 2),
            "low": round(c_low, 2),
            "close": round(c_close, 2),
            "tick_volume": 50,
            "spread": 0.30
        }
        candles_1m.append(bar)

        # 5m bars
        if i % 5 == 0:
            candles_5m.append(bar)

    return candles_1m, candles_5m


def test_generate_walk_forward_slices_multi_windows():
    start_ts = 1700000000
    end_ts = start_ts + 365 * 86400  # 12 months
    slices = generate_walk_forward_slices(start_ts, end_ts, train_days=90, validation_days=30, step_days=30)
    # (365 - 120) / 30 = 8.16 => 9 windows
    assert len(slices) >= 8


def test_phase5_strategy_validation_run():
    c1, c5 = _create_synthetic_candles(total_bars=1500)
    req = ValidationRequest(
        symbol="XAUUSD",
        train_days=90,
        validation_days=30,
        step_days=30,
        signal_threshold=7,
        sl_atr_multiplier=1.0,
        tp1_atr_multiplier=1.0,
        tp2_atr_multiplier=2.0,
        max_holding_minutes=60,
        assumed_spread=0.30,
        monte_carlo_simulations=100,
        random_seed=42,
        final_oos_locked=True
    )

    resp = run_strategy_validation(candles_1m=c1, candles_5m=c5, req=req)

    assert resp.symbol == "XAUUSD"
    assert resp.validation_run_id.startswith("VAL-")
    assert resp.dataset_coverage.candle_count_1m == 1500
    assert resp.data_quality.is_clean is True
    assert resp.validation_status.final_oos_locked is True
    assert resp.validation_status.baseline_evaluated is True
    assert len(resp.spread_sensitivity) >= 2
    assert len(resp.threshold_sensitivity_development) >= 2
    assert len(resp.exit_sensitivity_development) >= 2
    assert resp.oos_consistency is not None


def test_phase5_reproducibility():
    c1, c5 = _create_synthetic_candles(total_bars=800)
    req = ValidationRequest(
        symbol="XAUUSD",
        train_days=30,
        validation_days=15,
        step_days=15,
        monte_carlo_simulations=100,
        random_seed=999
    )

    resp1 = run_strategy_validation(candles_1m=c1, candles_5m=c5, req=req)
    resp2 = run_strategy_validation(candles_1m=c1, candles_5m=c5, req=req)

    assert resp1.dataset_coverage.dataset_hash == resp2.dataset_coverage.dataset_hash
    assert resp1.configuration_hash == resp2.configuration_hash
    assert resp1.overall_metrics.trades_count == resp2.overall_metrics.trades_count
    assert resp1.overall_metrics.total_r == resp2.overall_metrics.total_r
    assert resp1.monte_carlo.median_ending_r == resp2.monte_carlo.median_ending_r


def test_no_trading_execution_in_backend():
    """Verify strictly zero trading execution keywords exist in the backend source code."""
    import inspect
    import app.main
    import app.routes.validation
    import app.routes.history

    forbidden_keywords = ["order_send", "OrderSend", "ct.order_send", "trade_execute", "place_order"]
    for mod in [app.main, app.routes.validation, app.routes.history]:
        src = inspect.getsource(mod)
        for kw in forbidden_keywords:
            assert kw not in src, f"Forbidden trading execution keyword '{kw}' found in {mod.__name__}!"
