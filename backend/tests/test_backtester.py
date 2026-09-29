import pytest
from app.backtest_models import BacktestConfig
from app.backtester import BacktestReplayEngine, parse_date_to_timestamp


def generate_synthetic_history(base_price: float = 2000.0, total_1m: int = 150):
    """Generate synthetic 1m and 5m synchronized series for replay testing."""
    candles_1m = []
    current = base_price
    base_time = 1700000000

    for i in range(total_1m):
        # Create wave cycles
        drift = 0.6 if (i % 6 < 4) else -0.4
        c_open = current
        c_close = current + drift
        c_high = max(c_open, c_close) + 0.4
        c_low = min(c_open, c_close) - 0.4
        t = base_time + i * 60

        candles_1m.append({
            "time": t,
            "open": round(c_open, 2),
            "high": round(c_high, 2),
            "low": round(c_low, 2),
            "close": round(c_close, 2)
        })
        current = c_close

    # Build 5m candles by aggregating 1m bars
    candles_5m = []
    for i in range(0, total_1m, 5):
        chunk = candles_1m[i:i+5]
        if chunk:
            candles_5m.append({
                "time": chunk[0]["time"],
                "open": chunk[0]["open"],
                "high": max(c["high"] for c in chunk),
                "low": min(c["low"] for c in chunk),
                "close": chunk[-1]["close"]
            })

    return candles_1m, candles_5m


def test_date_parser():
    ts = parse_date_to_timestamp("2026-01-01T00:00:00Z", 0)
    assert ts > 0
    assert parse_date_to_timestamp(None, 12345) == 12345


def test_replay_engine_execution():
    candles_1m, candles_5m = generate_synthetic_history(2000.0, total_1m=120)
    config = BacktestConfig(
        symbol="XAUUSD",
        signal_threshold=7,
        initial_capital=10000.0,
        sl_atr_multiplier=1.0,
        tp1_atr_multiplier=1.0,
        max_holding_minutes=30
    )
    engine = BacktestReplayEngine(config)
    res = engine.run_backtest(candles_1m, candles_5m)

    assert res.symbol == "XAUUSD"
    assert "total_1m_candles" in res.period
    assert res.statistics is not None
    assert len(res.equity_curve) >= 1


def test_replay_insufficient_candles_rejection():
    config = BacktestConfig(symbol="XAUUSD")
    engine = BacktestReplayEngine(config)
    with pytest.raises(ValueError, match="Insufficient historical candles"):
        engine.run_backtest(candles_1m=[], candles_5m=[])


def test_backtest_api_endpoint():
    from starlette.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        # Valid backtest call
        resp = client.post("/api/backtest/xauusd", json={
            "symbol": "XAUUSD",
            "signal_threshold": 7,
            "initial_capital": 10000.0,
            "assumed_spread": 0.30
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "XAUUSD"
        assert "statistics" in data
        assert "trades" in data
        assert "equity_curve" in data

        # Invalid threshold (rejected by Pydantic validation)
        resp_bad = client.post("/api/backtest/xauusd", json={
            "symbol": "XAUUSD",
            "signal_threshold": 25
        })
        assert resp_bad.status_code in [400, 422]

        # Invalid symbol
        resp_sym = client.post("/api/backtest/xauusd", json={
            "symbol": "INVALID_COIN"
        })
        assert resp_sym.status_code == 400
