"""
Local MetaTrader 5 Wine Bridge Server (Local-Only, Read-Only)
Runs inside Wine Python to bridge MetaTrader 5 Windows API to Linux host via localhost HTTP.
Strictly Read-Only: Zero order execution methods exist.
"""
import http.server
import json
import logging
import os
import socketserver
import sys
import time
import urllib.parse
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mt5_wine_bridge")

try:
    import MetaTrader5 as mt5
    MT5_LIB_AVAILABLE = True
except Exception as e:
    logger.error("MetaTrader5 library import error in Wine Python: %s", e)
    mt5 = None
    MT5_LIB_AVAILABLE = False

HOST = "127.0.0.1"
PORT = 18812
DEFAULT_TERMINAL_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"

_state = {
    "initialized": False,
    "terminal_connected": False,
    "resolved_symbol": None,
    "symbol_info": {},
    "terminal_build": None,
}


def _resolve_symbol(preferred_symbol="XAUUSD"):
    if not MT5_LIB_AVAILABLE or mt5 is None:
        return False, "MetaTrader5 library unavailable."

    symbols = mt5.symbols_get()
    if not symbols:
        return False, "No symbols returned from MT5."

    all_names = [s.name for s in symbols]
    candidates = [
        preferred_symbol,
        f"{preferred_symbol}m",
        f"{preferred_symbol}.",
        f"{preferred_symbol}#",
        f"{preferred_symbol}_i",
        f"{preferred_symbol}.ecn",
        f"{preferred_symbol}.pro",
        "GOLD",
        "GOLDm",
        "GOLD."
    ]

    target = None
    for cand in candidates:
        if cand in all_names:
            target = cand
            break

    if not target:
        for s_name in all_names:
            upper = s_name.upper()
            if upper.startswith("XAUUSD") or upper.startswith("GOLD"):
                target = s_name
                break

    if not target:
        return False, "Could not resolve XAUUSD symbol in MT5."

    mt5.symbol_select(target, True)
    sym_info = mt5.symbol_info(target)
    if not sym_info:
        return False, f"Could not get symbol info for {target}."

    _state["resolved_symbol"] = target
    _state["symbol_info"] = {
        "name": sym_info.name,
        "description": sym_info.description,
        "digits": sym_info.digits,
        "point": sym_info.point,
        "spread": sym_info.spread,
        "currency_base": sym_info.currency_base,
        "currency_profit": sym_info.currency_profit,
        "is_mock": False
    }
    logger.info("Resolved symbol: %s (digits: %d, point: %s)", target, sym_info.digits, sym_info.point)
    return True, None


def _init_mt5(terminal_path=None, preferred_symbol="XAUUSD"):
    if not MT5_LIB_AVAILABLE or mt5 is None:
        return False, "MetaTrader5 library not installed in Wine environment."

    path = terminal_path or DEFAULT_TERMINAL_PATH
    logger.info("Initializing MT5 with path: %s", path)
    init_res = mt5.initialize(path=path)
    if not init_res:
        err = mt5.last_error()
        return False, f"MT5 initialize failed: {err}"

    term_info = mt5.terminal_info()
    _state["initialized"] = True
    _state["terminal_connected"] = bool(term_info.connected) if term_info else False
    _state["terminal_build"] = term_info.build if term_info else None

    resolved, err_msg = _resolve_symbol(preferred_symbol)
    if not resolved:
        return False, err_msg

    return True, None


class MT5BridgeHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, data, status_code=200):
        try:
            body = json.dumps(data).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            logger.debug("Error sending JSON response: %s", e)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            term_info = mt5.terminal_info() if (MT5_LIB_AVAILABLE and _state["initialized"]) else None
            is_conn = bool(term_info.connected) if term_info else False
            self._send_json({
                "status": "ok",
                "mt5_available": MT5_LIB_AVAILABLE,
                "initialized": _state["initialized"],
                "terminal_connected": is_conn,
                "resolved_symbol": _state["resolved_symbol"],
                "symbol_info": _state["symbol_info"],
                "build": _state["terminal_build"]
            })

        elif path == "/tick":
            sym = query.get("symbol", [_state.get("resolved_symbol") or "XAUUSD"])[0]
            if not MT5_LIB_AVAILABLE or not _state["initialized"]:
                self._send_json({"error": "MT5 not initialized"}, status_code=503)
                return

            tick = mt5.symbol_info_tick(sym)
            if tick is None:
                self._send_json({"error": f"No tick returned for {sym}"}, status_code=404)
                return

            ts_ms = int(tick.time_msc) if hasattr(tick, "time_msc") and tick.time_msc > 0 else int(tick.time * 1000)
            bid = round(float(tick.bid), 2)
            ask = round(float(tick.ask), 2)
            spread = round(ask - bid, 2)
            dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)

            self._send_json({
                "symbol": sym,
                "bid": bid,
                "ask": ask,
                "spread": spread,
                "timestamp": ts_ms,
                "timestampISO": dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "flags": getattr(tick, "flags", 0)
            })

        elif path == "/rates":
            sym = query.get("symbol", [_state.get("resolved_symbol") or "XAUUSD"])[0]
            tf_str = query.get("timeframe", ["1m"])[0]
            count = int(query.get("count", [300])[0])

            if not MT5_LIB_AVAILABLE or not _state["initialized"]:
                self._send_json({"error": "MT5 not initialized"}, status_code=503)
                return

            tf = mt5.TIMEFRAME_M1 if tf_str == "1m" else mt5.TIMEFRAME_M5
            rates = mt5.copy_rates_from_pos(sym, tf, 0, count)
            if rates is None or len(rates) == 0:
                self._send_json({"rates": []})
                return

            candles = []
            for r in rates:
                candles.append({
                    "time": int(r["time"]),
                    "open": round(float(r["open"]), 2),
                    "high": round(float(r["high"]), 2),
                    "low": round(float(r["low"]), 2),
                    "close": round(float(r["close"]), 2),
                    "tick_volume": int(r["tick_volume"]) if "tick_volume" in r.dtype.names else 0,
                    "spread": float(r["spread"]) if "spread" in r.dtype.names else 0.0,
                })
            self._send_json({"rates": candles})

        elif path == "/rates_range":
            sym = query.get("symbol", [_state.get("resolved_symbol") or "XAUUSD"])[0]
            tf_str = query.get("timeframe", ["1m"])[0]
            date_from_ts = int(query.get("date_from", [0])[0])
            date_to_ts = int(query.get("date_to", [int(time.time())])[0])

            if not MT5_LIB_AVAILABLE or not _state["initialized"]:
                self._send_json({"error": "MT5 not initialized"}, status_code=503)
                return

            tf = mt5.TIMEFRAME_M1 if tf_str == "1m" else mt5.TIMEFRAME_M5
            dt_from = datetime.fromtimestamp(date_from_ts, tz=timezone.utc)
            dt_to = datetime.fromtimestamp(date_to_ts, tz=timezone.utc)

            rates = mt5.copy_rates_range(sym, tf, dt_from, dt_to)
            if rates is None or len(rates) == 0:
                self._send_json({"rates": []})
                return

            candles = []
            for r in rates:
                candles.append({
                    "time": int(r["time"]),
                    "open": round(float(r["open"]), 2),
                    "high": round(float(r["high"]), 2),
                    "low": round(float(r["low"]), 2),
                    "close": round(float(r["close"]), 2),
                    "tick_volume": int(r["tick_volume"]) if "tick_volume" in r.dtype.names else 0,
                    "spread": float(r["spread"]) if "spread" in r.dtype.names else 0.0,
                })
            self._send_json({"rates": candles})

        else:
            self._send_json({"error": "Endpoint not found"}, status_code=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if path == "/initialize":
            term_path = payload.get("path")
            pref_sym = payload.get("preferred_symbol", "XAUUSD")
            success, err_msg = _init_mt5(term_path, pref_sym)
            if success:
                self._send_json({
                    "success": True,
                    "resolved_symbol": _state["resolved_symbol"],
                    "symbol_info": _state["symbol_info"],
                    "terminal_build": _state["terminal_build"]
                })
            else:
                self._send_json({"success": False, "error": err_msg}, status_code=500)

        elif path == "/shutdown":
            if MT5_LIB_AVAILABLE and mt5 and _state["initialized"]:
                mt5.shutdown()
            _state["initialized"] = False
            _state["terminal_connected"] = False
            self._send_json({"success": True})

        else:
            self._send_json({"error": "Endpoint not found"}, status_code=404)

    def log_message(self, format, *args):
        pass  # suppress HTTP request logs for ultra-fast performance


def run_server():
    logger.info("Starting local MT5 Wine Bridge Server on %s:%d...", HOST, PORT)
    # Automatically initialize MT5 on startup
    _init_mt5()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), MT5BridgeHandler) as httpd:
        logger.info("MT5 Wine Bridge Server active and listening on http://%s:%d", HOST, PORT)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down bridge server...")
        finally:
            if MT5_LIB_AVAILABLE and mt5 and _state["initialized"]:
                mt5.shutdown()


if __name__ == "__main__":
    run_server()
