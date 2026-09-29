import json
import logging
import math
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try importing MetaTrader5 (available on Windows / Wine environments)
try:
    import importlib
    mt5: Any = importlib.import_module("MetaTrader5")
    MT5_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    mt5 = None
    MT5_AVAILABLE = False


class MT5Client:
    def __init__(
        self,
        preferred_symbol: str = "XAUUSD",
        mock_fallback: bool = True,
        bridge_url: str = "http://127.0.0.1:18812"
    ):
        self.preferred_symbol = preferred_symbol
        self.mock_fallback = mock_fallback
        self.bridge_url = bridge_url
        self.is_connected = False
        self.is_mock = False
        self.resolved_symbol: Optional[str] = None
        self.symbol_info: Dict[str, Any] = {}
        self.last_tick_time: float = 0
        self.connection_error: Optional[str] = None
        self._use_bridge = False

        # Simulated mock state for local non-Windows / offline test verification
        self._mock_base_price = 3745.20
        self._mock_spread = 0.27
        self._mock_candles_1m: List[Dict[str, Any]] = []
        self._mock_candles_5m: List[Dict[str, Any]] = []
        self._init_mock_data()

    def _init_mock_data(self):
        """Pre-populate realistic mock historical candles for fallback/testing mode."""
        now = int(time.time())
        # 1-minute historical candles (past 300 minutes)
        cur_price = self._mock_base_price - 12.0
        self._mock_candles_1m = []
        for i in range(300, 0, -1):
            c_time = (now - i * 60) - ((now - i * 60) % 60)
            drift = random.gauss(0.04, 0.35)
            c_open = cur_price
            c_close = cur_price + drift
            c_high = max(c_open, c_close) + abs(random.gauss(0.1, 0.2))
            c_low = min(c_open, c_close) - abs(random.gauss(0.1, 0.2))
            self._mock_candles_1m.append({
                "time": c_time,
                "open": round(c_open, 2),
                "high": round(c_high, 2),
                "low": round(c_low, 2),
                "close": round(c_close, 2)
            })
            cur_price = c_close

        # 5-minute historical candles (past 300 5-min bars)
        cur_price = self._mock_base_price - 25.0
        self._mock_candles_5m = []
        for i in range(300, 0, -1):
            c_time = (now - i * 300) - ((now - i * 300) % 300)
            drift = random.gauss(0.08, 0.8)
            c_open = cur_price
            c_close = cur_price + drift
            c_high = max(c_open, c_close) + abs(random.gauss(0.25, 0.4))
            c_low = min(c_open, c_close) - abs(random.gauss(0.25, 0.4))
            self._mock_candles_5m.append({
                "time": c_time,
                "open": round(c_open, 2),
                "high": round(c_high, 2),
                "low": round(c_low, 2),
                "close": round(c_close, 2)
            })
            cur_price = c_close

    def _bridge_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        timeout: float = 2.0
    ) -> Optional[Dict[str, Any]]:
        """Perform a fast local HTTP request to the Wine MT5 Bridge."""
        try:
            url = f"{self.bridge_url.rstrip('/')}{path}"
            if params:
                query_str = urllib.parse.urlencode(params)
                url = f"{url}?{query_str}"

            req_data = None
            headers = {}
            if body is not None:
                req_data = json.dumps(body).encode("utf-8")
                headers["Content-Type"] = "application/json"

            req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)
                return None
        except Exception as e:
            logger.debug("Bridge request failed (%s %s): %s", method, path, e)
            return None

    def connect(self, path: Optional[str] = None) -> bool:
        """Connect to local MetaTrader 5 terminal and resolve XAUUSD symbol."""
        self.connection_error = None
        self._use_bridge = False

        # 1. Direct native MT5 connection (Windows / Wine native)
        if MT5_AVAILABLE:
            try:
                init_kwargs = {}
                if path:
                    init_kwargs["path"] = path

                logger.info("Attempting direct native MetaTrader 5 connection...")
                if mt5.initialize(**init_kwargs):
                    term_info = mt5.terminal_info()
                    if term_info is None:
                        err = mt5.last_error()
                        self.connection_error = f"MT5 terminal info unavailable (Error: {err})"
                        logger.warning(self.connection_error)
                    else:
                        logger.info("Connected to native MT5 terminal: %s (build %s)", term_info.name, term_info.build)

                    # Resolve symbol
                    resolved, err_msg = self.resolve_symbol()
                    if resolved:
                        self.is_connected = True
                        self.is_mock = False
                        logger.info("Successfully connected to native MT5. Active Symbol: %s", self.resolved_symbol)
                        return True
                    else:
                        self.connection_error = err_msg or "Failed to resolve XAUUSD symbol in MT5"
                        logger.error(self.connection_error)
                else:
                    err = mt5.last_error()
                    self.connection_error = f"MT5 initialization failed (Error code: {err})"
                    logger.warning(self.connection_error)
            except Exception as e:
                self.connection_error = f"Exception during native MT5 connection: {str(e)}"
                logger.error(self.connection_error, exc_info=True)

        # 2. Local Wine MT5 Bridge connection (Linux host -> Wine localhost HTTP bridge)
        bridge_health = self._bridge_request("GET", "/health", timeout=1.5)
        if bridge_health and bridge_health.get("status") == "ok":
            # If bridge MT5 is already initialized and connected
            if bridge_health.get("initialized") and bridge_health.get("terminal_connected") and bridge_health.get("resolved_symbol"):
                self.is_connected = True
                self.is_mock = False
                self._use_bridge = True
                self.resolved_symbol = bridge_health.get("resolved_symbol")
                self.symbol_info = bridge_health.get("symbol_info", {})
                self.connection_error = None
                logger.info("Successfully connected to MT5 via Wine Bridge. Active Symbol: %s", self.resolved_symbol)
                return True
            else:
                # Attempt to trigger bridge initialization
                init_payload = {"preferred_symbol": self.preferred_symbol}
                if path:
                    init_payload["path"] = path
                init_res = self._bridge_request("POST", "/initialize", body=init_payload, timeout=5.0)
                if init_res and init_res.get("success"):
                    self.is_connected = True
                    self.is_mock = False
                    self._use_bridge = True
                    self.resolved_symbol = init_res.get("resolved_symbol")
                    self.symbol_info = init_res.get("symbol_info", {})
                    self.connection_error = None
                    logger.info("Successfully initialized and connected to MT5 via Wine Bridge. Active Symbol: %s", self.resolved_symbol)
                    return True
                else:
                    err = init_res.get("error") if init_res else "Wine bridge failed to initialize MT5"
                    self.connection_error = f"Wine MT5 Bridge initialization error: {err}"
                    logger.warning(self.connection_error)

        if not self.connection_error:
            if not MT5_AVAILABLE:
                self.connection_error = "MetaTrader5 native module and local Wine bridge unavailable."

        # Fallback to simulated mode if enabled
        if self.mock_fallback:
            logger.info("Running in Mock/Simulation fallback mode for XAUUSD market data.")
            self.is_connected = True
            self.is_mock = True
            self.resolved_symbol = self.preferred_symbol
            self.symbol_info = {
                "name": self.preferred_symbol,
                "description": "Gold vs US Dollar (Simulated Live Feed)",
                "digits": 2,
                "point": 0.01,
                "spread": 27,
                "currency_base": "XAU",
                "currency_profit": "USD",
                "trade_mode": "READ_ONLY",
                "is_mock": True
            }
            return True

        self.is_connected = False
        return False

    def disconnect(self):
        """Disconnect and shutdown MT5."""
        if MT5_AVAILABLE and mt5 and not self.is_mock and not self._use_bridge:
            try:
                mt5.shutdown()
            except Exception as e:
                logger.warning("Error during MT5 shutdown: %s", e)
        self.is_connected = False
        self._use_bridge = False
        self.resolved_symbol = None

    def resolve_symbol(self) -> Tuple[bool, Optional[str]]:
        """
        Discover and resolve the broker's XAUUSD symbol (e.g. XAUUSD, XAUUSDm, XAUUSD., XAUUSD#).
        """
        if self._use_bridge and not self.is_mock:
            if self.resolved_symbol:
                return True, None
            health = self._bridge_request("GET", "/health", timeout=1.5)
            if health and health.get("resolved_symbol"):
                self.resolved_symbol = health["resolved_symbol"]
                self.symbol_info = health.get("symbol_info", {})
                return True, None
            return False, "Failed to resolve symbol via bridge"

        if not MT5_AVAILABLE or mt5 is None or self.is_mock:
            self.resolved_symbol = self.preferred_symbol
            return True, None

        try:
            symbols = mt5.symbols_get()
            if symbols is None:
                return False, "Failed to retrieve symbols from MT5 terminal."

            all_symbol_names = [s.name for s in symbols]
            logger.info("Retrieved %d symbols from MT5 terminal", len(all_symbol_names))

            # Candidate checks
            candidates = [
                self.preferred_symbol,
                f"{self.preferred_symbol}m",
                f"{self.preferred_symbol}.",
                f"{self.preferred_symbol}#",
                f"{self.preferred_symbol}_i",
                f"{self.preferred_symbol}.ecn",
                f"{self.preferred_symbol}.pro",
                "GOLD",
                "GOLDm",
                "GOLD."
            ]

            target_symbol = None
            # 1. Exact match in candidates
            for candidate in candidates:
                if candidate in all_symbol_names:
                    target_symbol = candidate
                    break

            # 2. Case-insensitive / substring match if still not found
            if not target_symbol:
                for s_name in all_symbol_names:
                    upper = s_name.upper()
                    if upper.startswith("XAUUSD") or upper.startswith("GOLD"):
                        target_symbol = s_name
                        break

            if not target_symbol:
                return False, "No XAUUSD-compatible symbol was found in the connected MT5 terminal."

            # Ensure symbol is selected in MarketWatch
            selected = mt5.symbol_select(target_symbol, True)
            if not selected:
                return False, f"Failed to select symbol '{target_symbol}' in MT5 MarketWatch."

            sym_info = mt5.symbol_info(target_symbol)
            if sym_info is None:
                return False, f"Could not retrieve symbol info for '{target_symbol}'."

            self.resolved_symbol = target_symbol
            self.symbol_info = {
                "name": sym_info.name,
                "description": sym_info.description,
                "digits": sym_info.digits,
                "point": sym_info.point,
                "spread": sym_info.spread,
                "currency_base": sym_info.currency_base,
                "currency_profit": sym_info.currency_profit,
                "is_mock": False
            }
            logger.info("XAUUSD symbol resolved: %s (digits: %d, point: %s)", target_symbol, sym_info.digits, sym_info.point)
            return True, None

        except Exception as e:
            return False, f"Error resolving symbol: {str(e)}"

    def get_latest_tick(self) -> Optional[Dict[str, Any]]:
        """Fetch latest tick for resolved XAUUSD symbol."""
        if not self.is_connected:
            return None

        # Wine Bridge tick
        if self._use_bridge and not self.is_mock and self.resolved_symbol:
            res = self._bridge_request("GET", "/tick", params={"symbol": self.resolved_symbol}, timeout=1.0)
            if res and "bid" in res and "ask" in res:
                self.last_tick_time = time.time()
                return {
                    "symbol": res.get("symbol", self.resolved_symbol),
                    "bid": round(float(res["bid"]), 2),
                    "ask": round(float(res["ask"]), 2),
                    "spread": round(float(res["spread"]), 2),
                    "timestamp": int(res["timestamp"]),
                    "timestampISO": res.get("timestampISO", "")
                }
            return None

        # Real MT5 tick (native)
        if MT5_AVAILABLE and mt5 and not self.is_mock and self.resolved_symbol:
            try:
                tick = mt5.symbol_info_tick(self.resolved_symbol)
                if tick is None:
                    return None

                # MT5 tick time in milliseconds
                timestamp_ms = int(tick.time_msc) if hasattr(tick, 'time_msc') and tick.time_msc > 0 else int(tick.time * 1000)
                dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
                iso_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

                bid = round(float(tick.bid), 2)
                ask = round(float(tick.ask), 2)
                spread = round(ask - bid, 2)

                self.last_tick_time = time.time()

                return {
                    "symbol": self.resolved_symbol,
                    "bid": bid,
                    "ask": ask,
                    "spread": spread,
                    "timestamp": timestamp_ms,
                    "timestampISO": iso_str
                }
            except Exception as e:
                logger.error("Error retrieving tick from MT5: %s", e)
                return None

        # Fallback simulated tick
        if self.is_mock and self.resolved_symbol:
            now_ms = int(time.time() * 1000)
            now_sec = now_ms / 1000.0
            dt = datetime.fromtimestamp(now_sec, tz=timezone.utc)
            iso_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

            # Smooth Brownian drift
            drift = random.gauss(0.0, 0.08)
            # Gentle mean reversion
            reversion = (3745.20 - self._mock_base_price) * 0.005
            self._mock_base_price = round(self._mock_base_price + drift + reversion, 2)

            bid = round(self._mock_base_price, 2)
            ask = round(bid + self._mock_spread, 2)
            spread = round(ask - bid, 2)

            self.last_tick_time = time.time()

            return {
                "symbol": self.resolved_symbol,
                "bid": bid,
                "ask": ask,
                "spread": spread,
                "timestamp": now_ms,
                "timestampISO": iso_str
            }

        return None

    def get_historical_candles(self, timeframe: str = "1m", count: int = 300) -> List[Dict[str, Any]]:
        """Fetch historical OHLC candles from MT5 rates or mock data."""
        if not self.is_connected or not self.resolved_symbol:
            return []

        # Wine Bridge rates
        if self._use_bridge and not self.is_mock:
            res = self._bridge_request("GET", "/rates", params={
                "symbol": self.resolved_symbol,
                "timeframe": timeframe,
                "count": count
            }, timeout=3.0)
            if res and "rates" in res:
                return res["rates"]
            return []

        # Real MT5 rates (native)
        if MT5_AVAILABLE and mt5 and not self.is_mock:
            try:
                tf = mt5.TIMEFRAME_M1 if timeframe == "1m" else mt5.TIMEFRAME_M5
                rates = mt5.copy_rates_from_pos(self.resolved_symbol, tf, 0, count)
                if rates is None or len(rates) == 0:
                    logger.warning("No historical rates returned from MT5 for timeframe %s", timeframe)
                    return []

                candles = []
                for r in rates:
                    candles.append({
                        "time": int(r["time"]),
                        "open": round(float(r["open"]), 2),
                        "high": round(float(r["high"]), 2),
                        "low": round(float(r["low"]), 2),
                        "close": round(float(r["close"]), 2),
                        "tick_volume": int(r["tick_volume"]) if "tick_volume" in r.dtype.names else None,
                        "spread": float(r["spread"]) if "spread" in r.dtype.names else None,
                        "real_volume": int(r["real_volume"]) if "real_volume" in r.dtype.names else None
                    })
                return candles
            except Exception as e:
                logger.error("Error fetching historical rates from MT5: %s", e)
                return []

        # Fallback simulated rates
        if self.is_mock:
            candles_list = self._mock_candles_1m if timeframe == "1m" else self._mock_candles_5m
            return list(candles_list[-count:])

        return []

    def get_historical_candles_chunked(
        self,
        timeframe: str = "1m",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        chunk_days: int = 14,
        return_manifest: bool = False
    ) -> Any:
        """
        Fetch historical candles in small chunked windows from MT5 to bypass terminal buffer limits,
        prevent timeouts, deduplicate overlaps, and sort strictly ascending.
        If return_manifest is True, returns Tuple[List[Dict[str, Any]], List[Dict[str, Any]]].
        """
        if not self.is_connected or not self.resolved_symbol:
            return ([], []) if return_manifest else []

        if self.is_mock:
            candles_list = self._mock_candles_1m if timeframe == "1m" else self._mock_candles_5m
            mock_chunk = {
                "chunk_id": 1,
                "requested_start": (date_from or datetime.now(timezone.utc) - timedelta(days=365)).isoformat(),
                "requested_end": (date_to or datetime.now(timezone.utc)).isoformat(),
                "actual_start": candles_list[0]["time"] if candles_list else None,
                "actual_end": candles_list[-1]["time"] if candles_list else None,
                "count": len(candles_list),
                "status": "SUCCESS",
                "mt5_error": None
            }
            return (list(candles_list), [mock_chunk]) if return_manifest else list(candles_list)

        now = datetime.now(timezone.utc)
        dt_end = date_to or now
        dt_start = date_from or (dt_end - timedelta(days=365))

        all_candles_by_time: Dict[int, Dict[str, Any]] = {}
        chunks_manifest: List[Dict[str, Any]] = []
        cur_end = dt_end
        chunk_idx = 0

        # Request backwards in chunk_days windows
        while cur_end > dt_start:
            chunk_idx += 1
            cur_start = max(dt_start, cur_end - timedelta(days=chunk_days))
            req_start_iso = cur_start.isoformat()
            req_end_iso = cur_end.isoformat()

            rates = None
            mt5_err_str = None
            try:
                if self._use_bridge:
                    res = self._bridge_request("GET", "/rates_range", params={
                        "symbol": self.resolved_symbol,
                        "timeframe": timeframe,
                        "date_from": int(cur_start.timestamp()),
                        "date_to": int(cur_end.timestamp())
                    }, timeout=5.0)
                    rates = res.get("rates") if res else None
                elif MT5_AVAILABLE and mt5:
                    tf = mt5.TIMEFRAME_M1 if timeframe == "1m" else mt5.TIMEFRAME_M5
                    rates_raw = mt5.copy_rates_range(self.resolved_symbol, tf, cur_start, cur_end)
                    if rates_raw is None or len(rates_raw) == 0:
                        raw_err = mt5.last_error()
                        mt5_err_str = str(raw_err)
                        mt5.symbol_select(self.resolved_symbol, True)
                        time.sleep(0.05)
                        rates_raw = mt5.copy_rates_range(self.resolved_symbol, tf, cur_start, cur_end)
                        if rates_raw is None or len(rates_raw) == 0:
                            raw_err_retry = mt5.last_error()
                            mt5_err_str = f"Initial: {raw_err}, Retry: {raw_err_retry}"
                    if rates_raw is not None and len(rates_raw) > 0:
                        rates = []
                        for r in rates_raw:
                            rates.append({
                                "time": int(r["time"]),
                                "open": round(float(r["open"]), 2),
                                "high": round(float(r["high"]), 2),
                                "low": round(float(r["low"]), 2),
                                "close": round(float(r["close"]), 2),
                                "tick_volume": int(r["tick_volume"]) if "tick_volume" in r.dtype.names else None,
                                "spread": float(r["spread"]) if "spread" in r.dtype.names else None,
                                "real_volume": int(r["real_volume"]) if "real_volume" in r.dtype.names else None
                            })
            except Exception as ex:
                mt5_err_str = str(ex)
                logger.error("Error fetching chunk [%s -> %s]: %s", cur_start, cur_end, ex)

            chunk_count = len(rates) if rates is not None else 0
            act_start_iso = None
            act_end_iso = None

            if rates is not None and len(rates) > 0:
                act_start_iso = datetime.fromtimestamp(int(rates[0]["time"]), tz=timezone.utc).isoformat()
                act_end_iso = datetime.fromtimestamp(int(rates[-1]["time"]), tz=timezone.utc).isoformat()
                for r in rates:
                    ts = int(r["time"])
                    if ts not in all_candles_by_time:
                        all_candles_by_time[ts] = {
                            "time": ts,
                            "open": round(float(r["open"]), 2),
                            "high": round(float(r["high"]), 2),
                            "low": round(float(r["low"]), 2),
                            "close": round(float(r["close"]), 2),
                            "tick_volume": int(r["tick_volume"]) if r.get("tick_volume") is not None else None,
                            "spread": float(r["spread"]) if r.get("spread") is not None else None,
                            "real_volume": int(r["real_volume"]) if r.get("real_volume") is not None else None
                        }

            chunk_status = "SUCCESS" if chunk_count > 0 else "EMPTY"
            chunks_manifest.append({
                "chunk_id": chunk_idx,
                "requested_start": req_start_iso,
                "requested_end": req_end_iso,
                "actual_start": act_start_iso,
                "actual_end": act_end_iso,
                "count": chunk_count,
                "status": chunk_status,
                "mt5_error": mt5_err_str
            })

            if cur_start <= dt_start:
                break
            cur_end = cur_start + timedelta(hours=1)

        sorted_candles = sorted(all_candles_by_time.values(), key=lambda c: c["time"])
        if sorted_candles:
            logger.info(
                "Chunked retrieval completed for %s (%s): %d unique candles across %d chunks (Span: %s to %s)",
                self.resolved_symbol,
                timeframe,
                len(sorted_candles),
                len(chunks_manifest),
                datetime.fromtimestamp(sorted_candles[0]["time"], tz=timezone.utc).strftime("%Y-%m-%d"),
                datetime.fromtimestamp(sorted_candles[-1]["time"], tz=timezone.utc).strftime("%Y-%m-%d")
            )

        if return_manifest:
            return sorted_candles, chunks_manifest
        return sorted_candles

    def get_historical_candles_range(
        self,
        timeframe: str = "1m",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch historical rates within a datetime range from MT5."""
        if not self.is_connected or not self.resolved_symbol:
            return []

        if self._use_bridge and not self.is_mock:
            if date_from and date_to and (date_to - date_from).total_seconds() > (7 * 86400):
                return self.get_historical_candles_chunked(
                    timeframe=timeframe,
                    date_from=date_from,
                    date_to=date_to,
                    chunk_days=14 if timeframe == "1m" else 30
                )
            if date_from and date_to:
                res = self._bridge_request("GET", "/rates_range", params={
                    "symbol": self.resolved_symbol,
                    "timeframe": timeframe,
                    "date_from": int(date_from.timestamp()),
                    "date_to": int(date_to.timestamp())
                }, timeout=3.0)
                if res and res.get("rates"):
                    return res["rates"]
                return self.get_historical_candles(timeframe=timeframe, count=count or 3000)
            elif count:
                return self.get_historical_candles(timeframe=timeframe, count=count)
            else:
                return self.get_historical_candles(timeframe=timeframe, count=1000)

        if MT5_AVAILABLE and mt5 and not self.is_mock:
            try:
                # If date range is provided and spans > 7 days, use chunked retrieval
                if date_from and date_to and (date_to - date_from).total_seconds() > (7 * 86400):
                    return self.get_historical_candles_chunked(
                        timeframe=timeframe,
                        date_from=date_from,
                        date_to=date_to,
                        chunk_days=14 if timeframe == "1m" else 30
                    )

                tf = mt5.TIMEFRAME_M1 if timeframe == "1m" else mt5.TIMEFRAME_M5
                if date_from and date_to:
                    rates = mt5.copy_rates_range(self.resolved_symbol, tf, date_from, date_to)
                    if rates is None or len(rates) == 0:
                        # Fallback to chunked retrieval before falling back to pos
                        chunked = self.get_historical_candles_chunked(
                            timeframe=timeframe, date_from=date_from, date_to=date_to
                        )
                        if chunked:
                            return chunked
                        rates = mt5.copy_rates_from_pos(self.resolved_symbol, tf, 0, count or 3000)
                elif count:
                    rates = mt5.copy_rates_from_pos(self.resolved_symbol, tf, 0, count)
                else:
                    rates = mt5.copy_rates_from_pos(self.resolved_symbol, tf, 0, 1000)

                if rates is None or len(rates) == 0:
                    logger.warning("No historical rates in range for %s", timeframe)
                    return []

                candles = []
                for r in rates:
                    candles.append({
                        "time": int(r["time"]),
                        "open": round(float(r["open"]), 2),
                        "high": round(float(r["high"]), 2),
                        "low": round(float(r["low"]), 2),
                        "close": round(float(r["close"]), 2),
                        "tick_volume": int(r["tick_volume"]) if "tick_volume" in r.dtype.names else None,
                        "spread": float(r["spread"]) if "spread" in r.dtype.names else None,
                        "real_volume": int(r["real_volume"]) if "real_volume" in r.dtype.names else None
                    })
                return candles
            except Exception as e:
                logger.error("Error fetching rates range from MT5: %s", e)
                return []

        if self.is_mock:
            candles_list = self._mock_candles_1m if timeframe == "1m" else self._mock_candles_5m
            return list(candles_list)

        return []
