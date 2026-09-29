import pytest
from app.validation.walk_forward import generate_walk_forward_slices, _slice_candles_with_warmup


def test_generate_walk_forward_slices_basic():
    # 180 days period
    start_ts = 1700000000
    end_ts = start_ts + (180 * 86400)
    train_days = 60
    val_days = 30
    step_days = 30

    slices = generate_walk_forward_slices(
        start_ts=start_ts,
        end_ts=end_ts,
        train_days=train_days,
        validation_days=val_days,
        step_days=step_days
    )

    assert len(slices) >= 3
    for idx, (t_start, t_end, v_start, v_end) in enumerate(slices):
        assert t_start < t_end
        assert t_end == v_start
        assert v_start < v_end
        assert v_end <= end_ts
        # Verify train length
        assert (t_end - t_start) == train_days * 86400
        if idx < len(slices) - 1:
            assert (v_end - v_start) == val_days * 86400


def test_generate_walk_forward_slices_short_period_adaptation():
    # 10 days period (shorter than standard 90/30)
    start_ts = 1700000000
    end_ts = start_ts + (10 * 86400)

    slices = generate_walk_forward_slices(
        start_ts=start_ts,
        end_ts=end_ts,
        train_days=90,
        validation_days=30,
        step_days=30
    )

    assert len(slices) == 1
    t_start, t_end, v_start, v_end = slices[0]
    assert t_start == start_ts
    assert t_end == v_start
    assert v_end == end_ts
    assert t_end > t_start


def test_slice_candles_with_warmup():
    base_t = 1700000000
    candles_1m = [{"time": base_t + (i * 60), "open": 2000 + i, "high": 2001 + i, "low": 1999 + i, "close": 2000.5 + i} for i in range(200)]
    candles_5m = [{"time": base_t + (i * 300), "open": 2000 + i, "high": 2002 + i, "low": 1998 + i, "close": 2001 + i} for i in range(40)]

    # Target window is from bar 100 to bar 150 (time: base_t + 6000 to base_t + 9000)
    target_start = base_t + 6000
    target_end = base_t + 9000

    sub_1m, sub_5m = _slice_candles_with_warmup(
        candles_1m=candles_1m,
        candles_5m=candles_5m,
        target_start_ts=target_start,
        target_end_ts=target_end,
        warmup_1m_bars=50,
        warmup_5m_bars=10
    )

    assert len(sub_1m) > 50  # Contains target bars + preceding warmup bars
    assert int(sub_1m[0]["time"]) < target_start
    assert int(sub_1m[-1]["time"]) <= target_end
