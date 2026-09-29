import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.market_data import market_service
from app.routes import backtest, experiments, forensics, health, history, market, shadow, validation
from app.websocket_manager import ws_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("xauusd.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing XAUUSD Market Data Server...")
    await market_service.start()
    yield
    logger.info("Shutting down XAUUSD Market Data Server...")
    await market_service.stop()


app = FastAPI(
    title="XAUUSD Exness Live Market Data API",
    description="Local-only, read-only live market data server for XAUUSD (Gold) from MetaTrader 5 / Exness",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST routes
app.include_router(health.router)
app.include_router(market.router)
app.include_router(history.router)
app.include_router(backtest.router)
app.include_router(validation.router)
app.include_router(forensics.router)
app.include_router(experiments.router)
app.include_router(shadow.router)



@app.websocket("/ws/market/xauusd")
async def websocket_market_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time XAUUSD ticks and forming candle updates.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial status and latest tick/candles snapshot
        await ws_manager.send_personal_message({
            "type": "status",
            "data": {
                "mt5_connected": market_service.mt5_client.is_connected,
                "symbol": market_service.mt5_client.resolved_symbol,
                "is_mock": market_service.mt5_client.is_mock,
                "message": "Connected to local XAUUSD market stream."
            }
        }, websocket)

        if market_service.latest_tick:
            await ws_manager.send_personal_message({
                "type": "tick",
                "data": market_service.latest_tick
            }, websocket)

        c_1m = market_service.candles_1m.get_current_candle()
        if c_1m:
            await ws_manager.send_personal_message({
                "type": "candle",
                "timeframe": "1m",
                "data": c_1m
            }, websocket)

        c_5m = market_service.candles_5m.get_current_candle()
        if c_5m:
            await ws_manager.send_personal_message({
                "type": "candle",
                "timeframe": "5m",
                "data": c_5m
            }, websocket)

        if market_service.latest_signal:
            await ws_manager.send_personal_message({
                "type": "analysis",
                "data": {
                    "symbol": "XAUUSD",
                    "signal": market_service.latest_signal.model_dump()
                }
            }, websocket)

        # Keep connection open and listen for client ping/messages
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug("WebSocket client connection ended: %s", e)
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=False
    )
