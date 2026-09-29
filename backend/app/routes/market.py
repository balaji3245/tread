from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.market_data import market_service
from app.signal_models import AnalysisResponse, MarketSignal

router = APIRouter(prefix="/api/market/xauusd", tags=["Market Data"])


class MarketTick(BaseModel):
    symbol: str
    bid: float
    ask: float
    spread: float
    timestamp: int
    timestampISO: str


class Candle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float


class CandlesResponse(BaseModel):
    symbol: str
    timeframe: str
    count: int
    candles: List[Candle]


class SymbolInfoResponse(BaseModel):
    symbol: str
    description: Optional[str] = None
    digits: int = 2
    point: float = 0.01
    spread: Optional[float] = None
    currency_base: Optional[str] = "XAU"
    currency_profit: Optional[str] = "USD"
    is_mock: bool = False


@router.get("/tick", response_model=MarketTick)
async def get_latest_tick():
    """Retrieve the latest live XAUUSD tick."""
    if not market_service.mt5_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "code": "MT5_DISCONNECTED",
                "message": market_service.mt5_client.connection_error or "MT5 terminal is not connected."
            }
        )

    tick = market_service.latest_tick or market_service.mt5_client.get_latest_tick()
    if not tick:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": "NO_TICK_AVAILABLE",
                "message": "No live tick is currently available for XAUUSD."
            }
        )

    return MarketTick(**tick)


@router.get("/candles", response_model=CandlesResponse)
async def get_candles(
    timeframe: str = Query(default="1m", description="Timeframe: '1m' or '5m'"),
    count: int = Query(default=300, ge=1, le=1000, description="Number of candles to return")
):
    """Retrieve historical and current forming OHLC candles."""
    tf_norm = timeframe.lower().strip()
    if tf_norm not in ["1m", "5m"]:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "INVALID_TIMEFRAME",
                "message": f"Timeframe '{timeframe}' is invalid. Supported timeframes are '1m' and '5m'."
            }
        )

    if not market_service.mt5_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "code": "MT5_DISCONNECTED",
                "message": market_service.mt5_client.connection_error or "MT5 terminal is not connected."
            }
        )

    symbol = market_service.mt5_client.resolved_symbol or settings.mt5_symbol
    if tf_norm == "1m":
        candles = market_service.candles_1m.get_candles(count=count)
    else:
        candles = market_service.candles_5m.get_candles(count=count)

    # If cache is empty, fetch directly from MT5
    if not candles:
        candles = market_service.mt5_client.get_historical_candles(timeframe=tf_norm, count=count)

    return CandlesResponse(
        symbol=symbol,
        timeframe=tf_norm,
        count=len(candles),
        candles=[Candle(**c) for c in candles]
    )


@router.get("/info", response_model=SymbolInfoResponse)
async def get_symbol_info():
    """Retrieve resolved XAUUSD symbol details and market specifications."""
    if not market_service.mt5_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "code": "MT5_DISCONNECTED",
                "message": market_service.mt5_client.connection_error or "MT5 terminal is not connected."
            }
        )

    info = market_service.mt5_client.symbol_info
    symbol = market_service.mt5_client.resolved_symbol or settings.mt5_symbol
    return SymbolInfoResponse(
        symbol=symbol,
        description=info.get("description", "Gold vs US Dollar"),
        digits=info.get("digits", 2),
        point=info.get("point", 0.01),
        spread=info.get("spread", 0.27),
        currency_base=info.get("currency_base", "XAU"),
        currency_profit=info.get("currency_profit", "USD"),
        is_mock=info.get("is_mock", False)
    )


@router.get("/analysis", response_model=AnalysisResponse)
async def get_market_analysis():
    """Retrieve current real-time multi-timeframe market analysis and signal classification."""
    import time
    symbol = market_service.mt5_client.resolved_symbol or settings.mt5_symbol
    signal = market_service.latest_signal or market_service._recalculate_signal()
    if not signal:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "code": "ANALYSIS_UNAVAILABLE",
                "message": "Market analysis is currently initializing."
            }
        )
    return AnalysisResponse(
        symbol=symbol,
        signal=signal,
        timestamp=int(time.time() * 1000)
    )
