"""
Historical Data Diagnostic Tool for XAUUSD / MT5 Terminal.
Safely inspects MetaTrader 5 terminal connection, account server info (no secrets),
symbol resolution, and tests M1 / M5 historical retrieval across 1d, 7d, 30d, 90d, 180d, 270d, 365d.
"""

import argparse
import datetime
import os
import sys
from typing import Any, Dict, List, Optional

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import importlib
    mt5: Any = importlib.import_module("MetaTrader5")
    MT5_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    MT5_AVAILABLE = False
    mt5 = None

from app.historical_data_cache import load_cached_candles, load_manifest


def run_diagnostic(symbol: str = "XAUUSD") -> Dict[str, Any]:
    """Execute deep diagnostic on MT5 terminal historical data availability."""
    print("=" * 60)
    print("       XAUUSD MT5 HISTORICAL DATA DIAGNOSTIC")
    print("=" * 60)

    py_exe = sys.executable
    py_ver = sys.version.split()[0]
    mt5_ver = mt5.__version__ if MT5_AVAILABLE else "NOT_INSTALLED"

    print("Environment:")
    print(f"  Python Interpreter : {py_exe} (v{py_ver})")
    print(f"  MetaTrader5 Package: {mt5_ver}")
    print()

    if not MT5_AVAILABLE:
        print("Terminal:")
        print("  Connected: NO (MetaTrader5 C-extension not available in this Python interpreter)")
        print("  Note     : Run using Wine Windows Python 3.11 for direct MT5 communication.")
        print("=" * 60)
        return {
            "mt5_available": False,
            "connected": False,
            "error": "MetaTrader5 Python extension not available."
        }

    # 1. Initialize MT5
    initialized = mt5.initialize()
    if not initialized:
        err = mt5.last_error()
        print("Terminal:")
        print(f"  Connected: NO (Initialization failed: {err})")
        print("=" * 60)
        return {
            "mt5_available": True,
            "connected": False,
            "error": f"Initialization failed: {err}"
        }

    term_info = mt5.terminal_info()
    term_dict = term_info._asdict() if term_info else {}
    acc_info = mt5.account_info()
    acc_dict = acc_info._asdict() if acc_info else {}

    print("Terminal:")
    print(f"  Connected : YES")
    print(f"  Build     : {term_dict.get('build', 'Unknown')}")
    print(f"  Max Bars  : {term_dict.get('maxbars', 'Unknown')}")
    print(f"  Company   : {term_dict.get('company', 'Unknown')}")
    print(f"  Server    : {acc_dict.get('server', 'Unknown')}")
    print(f"  Trade Mode: {acc_dict.get('trade_mode', 'Unknown')}")
    print()

    # 2. Symbol Resolution & Visibility
    resolved_sym = symbol
    sym_info = mt5.symbol_info(symbol)
    if sym_info is None:
        all_syms = mt5.symbols_get()
        candidates = [s.name for s in (all_syms or []) if symbol.upper() in s.name.upper()]
        if candidates:
            resolved_sym = candidates[0]
            sym_info = mt5.symbol_info(resolved_sym)

    if sym_info is not None:
        mt5.symbol_select(resolved_sym, True)
        sym_info = mt5.symbol_info(resolved_sym)
        visible = sym_info.visible if sym_info else False
        spread = sym_info.spread if sym_info else None
        digits = sym_info.digits if sym_info else None
        point = sym_info.point if sym_info else None
    else:
        visible = False
        spread = None
        digits = None
        point = None

    print("Symbol:")
    print(f"  Resolved: {resolved_sym}")
    print(f"  Visible : {'YES' if visible else 'NO'}")
    print(f"  Spread  : {spread} points")
    print(f"  Digits  : {digits}")
    print(f"  Point   : {point}")
    print()

    # 3. Timeframe Availability Tests
    now = datetime.datetime.now(datetime.timezone.utc)
    periods = [1, 7, 30, 90, 180, 270, 365]

    m1_results = {}
    m5_results = {}

    print("M1 Historical Retrieval (Direct Range vs Chunked):")
    for days in periods:
        start_dt = now - datetime.timedelta(days=days)
        # Direct query
        r1m_direct = mt5.copy_rates_range(resolved_sym, mt5.TIMEFRAME_M1, start_dt, now)
        err_direct = mt5.last_error()
        count_direct = len(r1m_direct) if r1m_direct is not None else 0

        # Chunked query (14-day chunks)
        chunk_count = 0
        cur_end = now
        oldest_ts = None
        newest_ts = None
        while cur_end > start_dt:
            cur_start = max(start_dt, cur_end - datetime.timedelta(days=14))
            chunk_rates = mt5.copy_rates_range(resolved_sym, mt5.TIMEFRAME_M1, cur_start, cur_end)
            if chunk_rates is not None and len(chunk_rates) > 0:
                chunk_count += len(chunk_rates)
                if newest_ts is None:
                    newest_ts = chunk_rates[-1]["time"]
                oldest_ts = chunk_rates[0]["time"]
            cur_end = cur_start

        m1_results[days] = {
            "direct_count": count_direct,
            "chunked_count": chunk_count,
            "direct_error": err_direct,
            "oldest_iso": datetime.datetime.fromtimestamp(oldest_ts, tz=datetime.timezone.utc).isoformat() if oldest_ts else "N/A",
            "newest_iso": datetime.datetime.fromtimestamp(newest_ts, tz=datetime.timezone.utc).isoformat() if newest_ts else "N/A"
        }

        print(f"  {days:3d} days → Direct: {count_direct:6d} bars | Chunked: {chunk_count:6d} bars (Oldest: {m1_results[days]['oldest_iso']})")

    print()
    print("M5 Historical Retrieval:")
    for days in periods:
        start_dt = now - datetime.timedelta(days=days)
        r5m = mt5.copy_rates_range(resolved_sym, mt5.TIMEFRAME_M5, start_dt, now)
        err5m = mt5.last_error()
        count5m = len(r5m) if r5m is not None else 0
        oldest5m = datetime.datetime.fromtimestamp(r5m[0]["time"], tz=datetime.timezone.utc).isoformat() if count5m > 0 else "N/A"
        m5_results[days] = {
            "count": count5m,
            "error": err5m,
            "oldest_iso": oldest5m
        }
        print(f"  {days:3d} days → {count5m:6d} bars (Oldest: {oldest5m})")

    print()
    print("Local Archive:")
    c1_cached, meta1 = load_cached_candles(resolved_sym, "1m")
    c5_cached, meta5 = load_cached_candles(resolved_sym, "5m")
    manifest1 = load_manifest(resolved_sym, "1m") or {}

    print(f"  1m Archive: {len(c1_cached)} bars ({meta1.get('available_days', '?') if meta1 else '?'} days, Hash: {meta1.get('dataset_hash', 'N/A') if meta1 else 'N/A'})")
    print(f"  5m Archive: {len(c5_cached)} bars ({meta5.get('available_days', '?') if meta5 else '?'} days, Hash: {meta5.get('dataset_hash', 'N/A') if meta5 else 'N/A'})")
    print(f"  Archive Chunks: {manifest1.get('archive_chunks', 0)}")
    print()

    print("Data Source:")
    print("  Exness MT5")
    print()

    # Determine Diagnosis Status
    max_m1_days = max([d for d, res in m1_results.items() if res["chunked_count"] > 100] or [0])
    max_m5_days = max([d for d, res in m5_results.items() if res["count"] > 100] or [0])

    if max_m1_days >= 365 and max_m5_days >= 365:
        diag_status = "FULL_12_MONTH_HISTORY_AVAILABLE"
    elif max_m1_days >= 90 or max_m5_days >= 180:
        diag_status = f"MULTI_MONTH_HISTORY_AVAILABLE (M1: ~{max_m1_days}d / M5: ~{max_m5_days}d)"
    else:
        diag_status = "LIMITED_HISTORY"

    print(f"Status: {diag_status}")
    print("=" * 60)

    mt5.shutdown()

    return {
        "mt5_available": True,
        "connected": True,
        "terminal": term_dict,
        "account": {
            "server": acc_dict.get("server"),
            "company": acc_dict.get("company"),
            "trade_mode": acc_dict.get("trade_mode")
        },
        "symbol": {
            "resolved": resolved_sym,
            "visible": visible,
            "spread": spread,
            "digits": digits
        },
        "m1_tests": m1_results,
        "m5_tests": m5_results,
        "status": diag_status
    }


def main():
    parser = argparse.ArgumentParser(description="XAUUSD MT5 Historical Data Diagnostic Tool")
    parser.add_argument("--symbol", type=str, default="XAUUSD", help="Symbol to diagnose (default: XAUUSD)")
    args = parser.parse_args()
    run_diagnostic(symbol=args.symbol)


if __name__ == "__main__":
    main()
