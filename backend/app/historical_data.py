import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.historical_data_cache import (
    get_missing_ranges,
    load_cached_candles,
    load_manifest,
    merge_and_save_candles,
    save_cached_candles,
)
from app.historical_data_quality import audit_dataset_quality, compute_dataset_hash
from app.market_data import market_service

mt5_client = market_service.mt5_client

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("historical_data")


def fetch_and_cache_historical_dataset(
    symbol: str = "XAUUSD",
    months: int = 12,
    timeframe: str = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Fetch large historical datasets for 1m and/or 5m timeframes from MetaTrader 5,
    audit data quality, generate manifests, and store in local compressed disk cache.
    Supports incremental updates, interrupted download recovery, and atomic writes.
    """
    now = datetime.now(timezone.utc)
    if end_date:
        dt_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    else:
        dt_end = now

    requested_days = months * 30
    if start_date:
        dt_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        requested_days = max(1, round((dt_end - dt_start).total_seconds() / 86400))
    else:
        dt_start = dt_end - timedelta(days=requested_days)

    target_start_ts = int(dt_start.timestamp())
    target_end_ts = int(dt_end.timestamp())

    timeframes_to_fetch = ["1m", "5m"] if timeframe in ["all", "both"] else [timeframe]

    logger.info("=" * 60)
    logger.info("  Historical Dataset Expansion: %s (%d Months / %d Days)", symbol, months, requested_days)
    logger.info("  Timeframes: %s", ", ".join(timeframes_to_fetch))
    logger.info("  Requested Target Window: %s -> %s", dt_start.strftime("%Y-%m-%d %H:%M UTC"), dt_end.strftime("%Y-%m-%d %H:%M UTC"))
    logger.info("=" * 60)

    # Initialize MT5 if not connected
    if not mt5_client.is_connected:
        logger.info("Connecting to MetaTrader 5 terminal...")
        connected = mt5_client.connect()
        if not connected:
            logger.warning("MT5 connection failed (%s), checking local cache...", mt5_client.connection_error)

    t0_all = time.time()
    results_by_tf: Dict[str, Any] = {}

    for tf in timeframes_to_fetch:
        logger.info("\n--- Processing %s Historical Data ---", tf.upper())

        # Check existing cache & missing intervals
        missing_intervals = [(target_start_ts, target_end_ts)] if force_refresh else get_missing_ranges(
            symbol=symbol,
            timeframe=tf,
            target_start_ts=target_start_ts,
            target_end_ts=target_end_ts
        )

        existing_candles, _ = load_cached_candles(symbol, tf)
        existing_count = len(existing_candles)

        if not missing_intervals and existing_count > 0:
            logger.info("✔ Local cache already completely covers %s range (%d candles).", tf, existing_count)
            candles_tf = existing_candles
            chunks_tf = (load_manifest(symbol, tf) or {}).get("chunks", [])
        else:
            logger.info("➤ Fetching %s historical candles from MT5 (Missing intervals: %d)...", tf, len(missing_intervals))
            chunk_days = 14 if tf == "1m" else 30
            downloaded_candles: List[Dict[str, Any]] = []
            all_chunks: List[Dict[str, Any]] = []

            if mt5_client.is_connected:
                for idx, (m_start_ts, m_end_ts) in enumerate(missing_intervals, start=1):
                    m_start_dt = datetime.fromtimestamp(m_start_ts, tz=timezone.utc)
                    m_end_dt = datetime.fromtimestamp(m_end_ts, tz=timezone.utc)
                    logger.info(
                        "  [Interval %d/%d] Requesting MT5 chunk [%s -> %s]...",
                        idx,
                        len(missing_intervals),
                        m_start_dt.strftime("%Y-%m-%d"),
                        m_end_dt.strftime("%Y-%m-%d")
                    )
                    c_chunk, m_chunk = mt5_client.get_historical_candles_chunked(
                        timeframe=tf,
                        date_from=m_start_dt,
                        date_to=m_end_dt,
                        chunk_days=chunk_days,
                        return_manifest=True
                    )
                    downloaded_candles.extend(c_chunk)
                    all_chunks.extend(m_chunk)

            if force_refresh:
                candles_tf = downloaded_candles
                if candles_tf:
                    save_cached_candles(symbol, tf, candles_tf, chunks=all_chunks)
            else:
                candles_tf = merge_and_save_candles(
                    symbol=symbol,
                    timeframe=tf,
                    new_candles=downloaded_candles,
                    chunks=all_chunks
                ) if downloaded_candles else existing_candles

        results_by_tf[tf] = {
            "candles": candles_tf,
            "count": len(candles_tf),
            "span": (
                datetime.fromtimestamp(candles_tf[0]["time"], tz=timezone.utc).strftime("%Y-%m-%d") + " -> " +
                datetime.fromtimestamp(candles_tf[-1]["time"], tz=timezone.utc).strftime("%Y-%m-%d")
            ) if candles_tf else "N/A"
        }

    # Load both 1m and 5m for combined quality audit
    candles_1m, _ = load_cached_candles(symbol, "1m")
    candles_5m, _ = load_cached_candles(symbol, "5m")

    logger.info("\n➤ Running Historical Data Quality & Multi-Timeframe Integrity Audit...")
    c1_clean, c5_clean, quality_report = audit_dataset_quality(
        candles_1m=candles_1m,
        candles_5m=candles_5m,
        requested_days=requested_days,
        symbol=symbol
    )

    # Update manifest with final dataset hash
    dataset_hash = quality_report.dataset_hash
    if candles_1m:
        save_cached_candles(symbol, "1m", c1_clean, dataset_hash=dataset_hash)
    if candles_5m:
        save_cached_candles(symbol, "5m", c5_clean, dataset_hash=dataset_hash)

    total_time = round(time.time() - t0_all, 2)

    logger.info("=" * 60)
    logger.info("  Phase 5B Historical Capacity & Quality Summary:")
    logger.info("  - Available History Days: %d days (Requested: %d)", quality_report.history_days, requested_days)
    logger.info("  - 1m Candles: %d | 5m Candles: %d", quality_report.total_1m_candles, quality_report.total_5m_candles)
    logger.info("  - Coverage Status: %s", quality_report.coverage_status)
    logger.info("  - Dataset Completeness: %s", "COMPLETE (100%)" if quality_report.is_complete else f"PARTIAL ({quality_report.history_days}/{requested_days} days)")
    logger.info("  - Invalid OHLC Bars: %d (1m) / %d (5m)", quality_report.invalid_candles_count_1m, quality_report.invalid_candles_count_5m)
    logger.info("  - Duplicate Timestamps: %d (1m) / %d (5m)", quality_report.duplicate_count_1m, quality_report.duplicate_count_5m)
    logger.info("  - Unexpected Market Gaps: %d", quality_report.unexpected_gaps_count)
    logger.info("  - 1m/5m Alignment: %s", quality_report.alignment_status)
    logger.info("  - Dataset Hash: %s", dataset_hash)
    logger.info("  - Total Elapsed Time: %.2f seconds", total_time)
    logger.info("=" * 60)

    return {
        "symbol": symbol,
        "quality_report": quality_report.model_dump(),
        "total_1m_candles": len(c1_clean),
        "total_5m_candles": len(c5_clean),
        "dataset_hash": dataset_hash,
        "time_elapsed_sec": total_time
    }


def main():
    parser = argparse.ArgumentParser(description="XAUUSD Historical Market Data Downloader & Cache Manager")
    parser.add_argument("--symbol", type=str, default="XAUUSD", help="Market symbol (default: XAUUSD)")
    parser.add_argument("--months", type=int, default=12, help="Months of history to fetch (default: 12)")
    parser.add_argument("--timeframe", type=str, default="all", choices=["1m", "5m", "all", "both"], help="Timeframe (default: all)")
    parser.add_argument("--start", type=str, default=None, help="Start date (ISO or YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None, help="End date (ISO or YYYY-MM-DD)")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh and overwrite existing cache")

    args = parser.parse_args()

    result = fetch_and_cache_historical_dataset(
        symbol=args.symbol,
        months=args.months,
        timeframe=args.timeframe,
        start_date=args.start,
        end_date=args.end,
        force_refresh=args.force_refresh
    )
    print(f"\n✔ Completed historical dataset update for {result['symbol']} (1m: {result['total_1m_candles']}, 5m: {result['total_5m_candles']}, Hash: {result['dataset_hash']})")


if __name__ == "__main__":
    main()
