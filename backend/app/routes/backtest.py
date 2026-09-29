import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException

from app.backtest_models import BacktestConfig, BacktestResponse
from app.backtester import BacktestReplayEngine, parse_date_to_timestamp
from app.market_data import market_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["Historical Backtesting"])

# In-memory dataset cache for fast repeated runs
_BACKTEST_DATA_CACHE: Dict[str, Dict[str, Any]] = {}


@router.post("/xauusd", response_model=BacktestResponse)
async def run_xauusd_backtest(config: BacktestConfig):
    """
    Execute historical backtest replay simulation on XAUUSD.
    Strictly deterministic, zero look-ahead bias, utilizing identical live SignalEngine rules.
    """
    # 1. Validate configuration parameters
    if config.symbol.upper() not in ["XAUUSD", "GOLD"]:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "UNSUPPORTED_SYMBOL",
                "message": f"Symbol '{config.symbol}' is unsupported. Only 'XAUUSD' is currently supported."
            }
        )

    if config.initial_capital <= 0:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "code": "INVALID_CAPITAL", "message": "initial_capital must be greater than 0."}
        )

    if config.sl_atr_multiplier <= 0 or config.tp1_atr_multiplier <= 0 or config.tp2_atr_multiplier <= 0:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "code": "INVALID_MULTIPLIER", "message": "ATR multipliers must be greater than 0."}
        )

    if config.signal_threshold < 1 or config.signal_threshold > 10:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "code": "INVALID_THRESHOLD", "message": "signal_threshold must be between 1 and 10."}
        )

    # 2. Parse and validate date ranges
    now_ts = int(time.time())
    start_ts = parse_date_to_timestamp(config.start_date, now_ts - 86400 * 3) # default last 3 days
    end_ts = parse_date_to_timestamp(config.end_date, now_ts)

    if end_ts <= start_ts:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "INVALID_DATE_RANGE",
                "message": "end_date must be strictly greater than start_date."
            }
        )

    # 3. Retrieve Historical Data from MT5
    # 3. Retrieve Historical Data (From cache first, MT5 if available)
    from app.historical_data_cache import load_cached_candles
    cached_1m, _ = load_cached_candles(config.symbol, "1m")
    cached_5m, _ = load_cached_candles(config.symbol, "5m")

    if not cached_1m or not cached_5m:
        dt_start = datetime.fromtimestamp(start_ts, tz=timezone.utc)
        dt_end = datetime.fromtimestamp(end_ts, tz=timezone.utc)

        # Query MT5 range or recent bars
        candles_1m = market_service.mt5_client.get_historical_candles_range(
            timeframe="1m", date_from=dt_start, date_to=dt_end, count=2500
        )
        candles_5m = market_service.mt5_client.get_historical_candles_range(
            timeframe="5m", date_from=dt_start, date_to=dt_end, count=800
        )

        if len(candles_1m) < 40:
            candles_1m = market_service.candles_1m.get_candles(count=1000) or market_service.mt5_client.get_historical_candles("1m", 1000)
            candles_5m = market_service.candles_5m.get_candles(count=500) or market_service.mt5_client.get_historical_candles("5m", 500)
    else:
        candles_1m = [c for c in cached_1m if int(c["time"]) >= start_ts - 3600 and int(c["time"]) <= end_ts]
        candles_5m = [c for c in cached_5m if int(c["time"]) >= start_ts - 7200 and int(c["time"]) <= end_ts]

    # Offline test fallback if both cache and MT5 disconnected
    if len(candles_1m) < 40 and market_service.mt5_client._mock_candles_1m:
        candles_1m = market_service.mt5_client._mock_candles_1m
    if len(candles_5m) < 15 and market_service.mt5_client._mock_candles_5m:
        candles_5m = market_service.mt5_client._mock_candles_5m

    if len(candles_1m) < 40 or len(candles_5m) < 15:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": "INSUFFICIENT_HISTORICAL_DATA",
                "message": f"Only retrieved {len(candles_1m)} 1m candles and {len(candles_5m)} 5m candles. Minimum required for multi-timeframe analysis is 40 1m and 15 5m bars."
            }
        )

    # 4. Execute Backtest Simulation
    try:
        engine = BacktestReplayEngine(config)
        response = engine.run_backtest(candles_1m, candles_5m)
        return response
    except Exception as e:
        logger.error("Error executing backtest: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": "BACKTEST_EXECUTION_ERROR",
                "message": f"Backtest execution failed: {str(e)}"
            }
        )
