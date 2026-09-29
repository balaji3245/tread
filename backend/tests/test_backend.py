import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.candles import CandleAggregator
from app.market_data import market_service


def test_candle_aggregator_1m():
    agg = CandleAggregator(timeframe_seconds=60, max_candles=10)
    base_t = 1700000000  # 1700000000 % 60 == 40 -> bucket is 1699999980
    bucket = base_t - (base_t % 60)

    # First tick
    c1, is_new = agg.process_tick(price=2000.50, timestamp_sec=base_t)
    assert is_new is True
    assert c1["time"] == bucket
    assert c1["open"] == 2000.50
    assert c1["high"] == 2000.50
    assert c1["low"] == 2000.50
    assert c1["close"] == 2000.50

    # Second tick in same 1m bucket with higher price
    c2, is_new = agg.process_tick(price=2002.00, timestamp_sec=base_t + 15)
    assert is_new is False
    assert c2["time"] == bucket
    assert c2["open"] == 2000.50
    assert c2["high"] == 2002.00
    assert c2["low"] == 2000.50
    assert c2["close"] == 2002.00

    # Third tick in same 1m bucket with lower price
    c3, is_new = agg.process_tick(price=1999.00, timestamp_sec=base_t + 30)
    assert is_new is False
    assert c3["high"] == 2002.00
    assert c3["low"] == 1999.00
    assert c3["close"] == 1999.00

    # Fourth tick in NEXT 1m bucket
    next_t = bucket + 60
    c4, is_new = agg.process_tick(price=2001.20, timestamp_sec=next_t + 5)
    assert is_new is True
    assert c4["time"] == next_t
    assert c4["open"] == 2001.20
    assert c4["high"] == 2001.20
    assert c4["low"] == 2001.20
    assert c4["close"] == 2001.20
    assert len(agg.get_candles()) == 2


def test_candle_aggregator_5m():
    agg = CandleAggregator(timeframe_seconds=300, max_candles=10)
    bucket = 1700000100  # multiple of 300
    base_t = bucket

    c1, is_new = agg.process_tick(price=2000.00, timestamp_sec=base_t)
    assert is_new is True
    assert c1["time"] == bucket

    # Tick 120s later is still in same 5m bucket (120 < 300)
    c2, is_new = agg.process_tick(price=2005.00, timestamp_sec=base_t + 120)
    assert is_new is False
    assert c2["time"] == bucket
    assert c2["high"] == 2005.00

    # Tick 360s later is in next 5m bucket
    c3, is_new = agg.process_tick(price=2003.00, timestamp_sec=base_t + 360)
    assert is_new is True
    assert c3["time"] == bucket + 300


def test_health_endpoint():
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "mt5_connected" in data
        assert "timestamp" in data
        assert data["symbol"] is not None


def test_market_tick_endpoint():
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        resp = client.get("/api/market/xauusd/tick")
        if resp.status_code == 200:
            data = resp.json()
            assert data["symbol"] is not None
            assert "bid" in data
            assert "ask" in data
            assert "spread" in data
            assert data["bid"] > 0
            assert data["ask"] >= data["bid"]
            assert data["spread"] >= 0
            assert "timestamp" in data
            assert "timestampISO" in data
        else:
            # 503 if not connected in test runner environment
            assert resp.status_code == 503


def test_market_candles_endpoints():
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        # 1m candles
        resp_1m = client.get("/api/market/xauusd/candles?timeframe=1m&count=50")
        if resp_1m.status_code == 200:
            data_1m = resp_1m.json()
            assert data_1m["timeframe"] == "1m"
            assert len(data_1m["candles"]) > 0
            candle = data_1m["candles"][0]
            assert "time" in candle
            assert "open" in candle
            assert "high" in candle
            assert "low" in candle
            assert "close" in candle
        else:
            assert resp_1m.status_code == 503

        # Invalid timeframe check
        resp_inv = client.get("/api/market/xauusd/candles?timeframe=15m")
        assert resp_inv.status_code == 400


def test_symbol_info_endpoint():
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        resp = client.get("/api/market/xauusd/info")
        if resp.status_code == 200:
            data = resp.json()
            assert "symbol" in data
            assert "digits" in data
            assert "point" in data
        else:
            assert resp.status_code == 503


def test_market_analysis_endpoint():
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        resp = client.get("/api/market/xauusd/analysis")
        if resp.status_code == 200:
            data = resp.json()
            assert "symbol" in data
            assert "signal" in data
            sig = data["signal"]
            assert sig["type"] in ["LONG_SETUP", "SHORT_SETUP", "WAIT"]
            assert "strength" in sig
            assert "maxStrength" in sig
            assert "indicators" in sig
            assert "reasons" in sig
            assert "warnings" in sig
        else:
            assert resp.status_code == 503


def test_websocket_stream():
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        with client.websocket_connect("/ws/market/xauusd") as websocket:
            # Receive initial status message
            msg1 = websocket.receive_json()
            assert msg1["type"] in ["status", "tick", "candle", "analysis"]

