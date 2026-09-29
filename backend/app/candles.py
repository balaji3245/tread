import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CandleAggregator:
    def __init__(self, timeframe_seconds: int = 60, max_candles: int = 1000):
        self.timeframe_seconds = timeframe_seconds
        self.max_candles = max_candles
        self.candles: List[Dict[str, Any]] = []

    def set_candles(self, initial_candles: List[Dict[str, Any]]):
        """Set or replace the current candle history (e.g. from MT5 copy_rates)."""
        self.candles = list(initial_candles[-self.max_candles:])

    def get_candles(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get the latest candles."""
        if count is None or count >= len(self.candles):
            return list(self.candles)
        return list(self.candles[-count:])

    def get_current_candle(self) -> Optional[Dict[str, Any]]:
        """Return the currently forming candle if any."""
        if not self.candles:
            return None
        return self.candles[-1]

    def process_tick(self, price: float, timestamp_sec: float) -> Tuple[Dict[str, Any], bool]:
        """
        Process a new incoming tick price and update the forming candle.
        Returns (current_candle, is_new_candle).
        """
        candle_time = int(timestamp_sec) - (int(timestamp_sec) % self.timeframe_seconds)
        price = round(price, 2)

        if not self.candles:
            new_candle = {
                "time": candle_time,
                "open": price,
                "high": price,
                "low": price,
                "close": price
            }
            self.candles.append(new_candle)
            return new_candle, True

        current = self.candles[-1]

        if current["time"] == candle_time:
            # Update existing forming candle
            current["high"] = round(max(current["high"], price), 2)
            current["low"] = round(min(current["low"], price), 2)
            current["close"] = price
            return dict(current), False
        elif candle_time > current["time"]:
            # Start new candle
            new_candle = {
                "time": candle_time,
                "open": price,
                "high": price,
                "low": price,
                "close": price
            }
            self.candles.append(new_candle)
            if len(self.candles) > self.max_candles:
                self.candles.pop(0)
            return new_candle, True
        else:
            # Out of order older tick (rare) - update corresponding candle if exists
            for c in reversed(self.candles):
                if c["time"] == candle_time:
                    c["high"] = round(max(c["high"], price), 2)
                    c["low"] = round(min(c["low"], price), 2)
                    c["close"] = price
                    return dict(c), False
            return current, False
