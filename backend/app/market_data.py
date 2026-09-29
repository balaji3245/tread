import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.candles import CandleAggregator
from app.config import settings
from app.mt5_client import MT5Client
from app.phase6i.shadow_engine import live_shadow_engine
from app.signal_engine import SignalEngine
from app.signal_models import MarketSignal
from app.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(self):
        self.mt5_client = MT5Client(
            preferred_symbol=settings.mt5_symbol,
            mock_fallback=settings.mt5_mock_fallback,
            bridge_url=settings.mt5_bridge_url
        )
        self.candles_1m = CandleAggregator(timeframe_seconds=60, max_candles=settings.historical_candle_count)
        self.candles_5m = CandleAggregator(timeframe_seconds=300, max_candles=settings.historical_candle_count)
        self.signal_engine = SignalEngine(setup_threshold=7, max_strength=10)
        self.latest_signal: Optional[MarketSignal] = None
        self.latest_tick: Optional[Dict[str, Any]] = None
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._last_broadcast_tick_time: int = 0
        self._last_analysis_time: float = 0.0
        self._last_analysis_price: float = 0.0
        self._last_1m_candle_signature: Optional[Tuple[int, float, float, float, float]] = None
        self._last_5m_candle_signature: Optional[Tuple[int, float, float, float, float]] = None

    async def start(self):
        """Start the market data service."""
        logger.info("Starting Market Data Service...")
        self._running = True

        # Attempt initial MT5 connection
        connected = self.mt5_client.connect(path=settings.mt5_path if settings.mt5_path else None)
        if connected:
            self._load_historical_candles()
            self._recalculate_signal()
            logger.info("Market data initialized for symbol %s (Mock: %s)", self.mt5_client.resolved_symbol, self.mt5_client.is_mock)
        else:
            logger.warning("MT5 connection failed on startup: %s", self.mt5_client.connection_error)

        self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop(self):
        """Stop the market data service."""
        logger.info("Stopping Market Data Service...")
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self.mt5_client.disconnect()

    def _load_historical_candles(self):
        """Load initial historical candles from MT5 or mock generator."""
        if not self.mt5_client.is_connected:
            return

        c_1m = self.mt5_client.get_historical_candles(timeframe="1m", count=settings.historical_candle_count)
        if c_1m:
            self.candles_1m.set_candles(c_1m)
            logger.info("Loaded %d historical 1m candles", len(c_1m))

        c_5m = self.mt5_client.get_historical_candles(timeframe="5m", count=settings.historical_candle_count)
        if c_5m:
            self.candles_5m.set_candles(c_5m)
            logger.info("Loaded %d historical 5m candles", len(c_5m))

    def _recalculate_signal(self) -> Optional[MarketSignal]:
        """Recalculate signal and market structure analysis."""
        c_1m_list = self.candles_1m.get_candles()
        c_5m_list = self.candles_5m.get_candles()
        signal = self.signal_engine.analyze(
            candles_1m=c_1m_list,
            candles_5m=c_5m_list,
            current_tick=self.latest_tick
        )
        self.latest_signal = signal
        self._last_analysis_time = time.time()
        if self.latest_tick:
            self._last_analysis_price = float(self.latest_tick["bid"])
        
        # Dispatch to Phase 6I Live Shadow Engine (strictly isolated, failure safe)
        if signal:
            try:
                live_shadow_engine.process_new_signal(signal, c_1m_list, self.latest_tick)
            except Exception as e:
                logger.error("Isolated error dispatching signal to shadow engine: %s", e)

        return signal

    async def _poll_loop(self):
        """Main loop to continuously retrieve ticks and push real-time updates."""
        poll_interval_sec = max(0.01, settings.tick_poll_interval_ms / 1000.0)
        reconnect_delay = 1.0
        max_reconnect_delay = 30.0

        while self._running:
            try:
                if not self.mt5_client.is_connected:
                    logger.info("Attempting MT5 reconnection (retry in %.1fs)...", reconnect_delay)
                    connected = self.mt5_client.connect(path=settings.mt5_path if settings.mt5_path else None)
                    if connected:
                        reconnect_delay = 1.0
                        self._load_historical_candles()
                        self._recalculate_signal()
                        await ws_manager.broadcast({
                            "type": "status",
                            "data": {
                                "mt5_connected": True,
                                "symbol": self.mt5_client.resolved_symbol,
                                "is_mock": self.mt5_client.is_mock,
                                "message": "MT5 connected successfully."
                            }
                        })
                    else:
                        await ws_manager.broadcast({
                            "type": "status",
                            "data": {
                                "mt5_connected": False,
                                "symbol": None,
                                "is_mock": False,
                                "message": self.mt5_client.connection_error or "MT5 disconnected."
                            }
                        })
                        await asyncio.sleep(reconnect_delay)
                        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                        continue

                # Get latest tick
                tick = self.mt5_client.get_latest_tick()
                if tick:
                    self.latest_tick = tick

                    # Dispatch tick to Phase 6I Live Shadow Engine (isolated, failure safe)
                    try:
                        live_shadow_engine.process_tick_update(tick)
                    except Exception as e:
                        logger.error("Isolated error dispatching tick to shadow engine: %s", e)

                    timestamp_sec = tick["timestamp"] / 1000.0
                    price = tick["bid"]  # standard candlestick base price is Bid price

                    # Process 1m candle
                    c_1m, is_new_1m = self.candles_1m.process_tick(price, timestamp_sec)
                    sig_1m = (c_1m["time"], c_1m["open"], c_1m["high"], c_1m["low"], c_1m["close"])

                    # Process 5m candle
                    c_5m, is_new_5m = self.candles_5m.process_tick(price, timestamp_sec)
                    sig_5m = (c_5m["time"], c_5m["open"], c_5m["high"], c_5m["low"], c_5m["close"])

                    # Broadcast tick
                    await ws_manager.broadcast({
                        "type": "tick",
                        "data": tick
                    })

                    # Broadcast 1m candle update if changed
                    if sig_1m != self._last_1m_candle_signature:
                        self._last_1m_candle_signature = sig_1m
                        await ws_manager.broadcast({
                            "type": "candle",
                            "timeframe": "1m",
                            "data": c_1m
                        })

                    # Broadcast 5m candle update if changed
                    if sig_5m != self._last_5m_candle_signature:
                        self._last_5m_candle_signature = sig_5m
                        await ws_manager.broadcast({
                            "type": "candle",
                            "timeframe": "5m",
                            "data": c_5m
                        })

                    # Recompute analysis on new candle close or throttled (every 1.5s on price movement)
                    now_t = time.time()
                    should_reanalyze = (
                        is_new_1m
                        or is_new_5m
                        or (now_t - self._last_analysis_time >= 1.5 and abs(price - self._last_analysis_price) >= 0.10)
                        or self.latest_signal is None
                    )

                    if should_reanalyze:
                        signal = self._recalculate_signal()
                        if signal:
                            await ws_manager.broadcast({
                                "type": "analysis",
                                "data": {
                                    "symbol": "XAUUSD",
                                    "signal": signal.model_dump()
                                }
                            })

                await asyncio.sleep(poll_interval_sec)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in market data poll loop: %s", e, exc_info=True)
                await asyncio.sleep(1.0)


market_service = MarketDataService()
