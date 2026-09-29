import time
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.market_data import market_service

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    mt5_connected: bool
    is_mock: bool
    symbol: Optional[str]
    timestamp: int
    message: str


@router.get("/health", response_model=HealthResponse)
async def get_health():
    is_connected = market_service.mt5_client.is_connected
    is_mock = market_service.mt5_client.is_mock
    symbol = market_service.mt5_client.resolved_symbol or market_service.mt5_client.preferred_symbol
    now_ms = int(time.time() * 1000)

    if is_connected:
        status = "ok"
        msg = "MT5 Exness market data stream active" if not is_mock else "MT5 Simulation fallback mode active"
    else:
        status = "degraded"
        msg = market_service.mt5_client.connection_error or "MT5 disconnected"

    return HealthResponse(
        status=status,
        mt5_connected=is_connected,
        is_mock=is_mock,
        symbol=symbol,
        timestamp=now_ms,
        message=msg
    )
