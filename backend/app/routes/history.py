import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.historical_data import fetch_and_cache_historical_dataset
from app.historical_data_cache import load_cached_candles, load_manifest
from app.historical_data_quality import audit_dataset_quality
from app.market_data import market_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["Historical Data & Cache"])


class HistoryDownloadRequest(BaseModel):
    symbol: str = "XAUUSD"
    months: int = Field(default=12, ge=1, le=36)
    timeframe: str = "all"  # "1m", "5m", "all"
    start: Optional[str] = None
    end: Optional[str] = None
    force_refresh: bool = False


@router.get("/xauusd/status")
def get_xauusd_history_status():
    """
    Retrieve current local cache, archive manifest, and data quality status for XAUUSD historical datasets.
    """
    symbol = "XAUUSD"
    candles_1m, meta_1m = load_cached_candles(symbol, "1m")
    candles_5m, meta_5m = load_cached_candles(symbol, "5m")
    manifest_1m = load_manifest(symbol, "1m") or {}
    manifest_5m = load_manifest(symbol, "5m") or {}

    # If no cached files, fallback to live memory buffer
    if not candles_1m:
        candles_1m = market_service.candles_1m.get_candles(count=2000) or []
    if not candles_5m:
        candles_5m = market_service.candles_5m.get_candles(count=1000) or []

    c1_clean, c5_clean, quality_report = audit_dataset_quality(
        candles_1m=candles_1m,
        candles_5m=candles_5m,
        requested_days=365,
        symbol=symbol
    )

    t1_start = meta_1m.get("start", quality_report.actual_start_iso) if meta_1m else quality_report.actual_start_iso
    t1_end = meta_1m.get("end", quality_report.actual_end_iso) if meta_1m else quality_report.actual_end_iso
    t5_start = meta_5m.get("start", quality_report.actual_start_iso) if meta_5m else quality_report.actual_start_iso
    t5_end = meta_5m.get("end", quality_report.actual_end_iso) if meta_5m else quality_report.actual_end_iso

    m1_days = 0
    if c1_clean:
        m1_days = max(1, round((int(c1_clean[-1]["time"]) - int(c1_clean[0]["time"])) / 86400))
    m5_days = 0
    if c5_clean:
        m5_days = max(1, round((int(c5_clean[-1]["time"]) - int(c5_clean[0]["time"])) / 86400))

    diag_summary = (
        f"Available M1: {len(c1_clean)} bars (~{m1_days}d), M5: {len(c5_clean)} bars (~{m5_days}d). "
        f"Coverage status: {quality_report.coverage_status}."
    )

    return {
        "symbol": symbol,
        "mt5_connected": market_service.mt5_client.is_connected,
        "m1": {
            "available": len(c1_clean) > 0,
            "actual_start": t1_start,
            "actual_end": t1_end,
            "candles": len(c1_clean),
            "available_days": m1_days,
            "complete": m1_days >= 360,
            "archive_chunks": manifest_1m.get("archive_chunks", 0)
        },
        "m5": {
            "available": len(c5_clean) > 0,
            "actual_start": t5_start,
            "actual_end": t5_end,
            "candles": len(c5_clean),
            "available_days": m5_days,
            "complete": m5_days >= 360,
            "archive_chunks": manifest_5m.get("archive_chunks", 0)
        },
        "timeframes": {
            "1m": {
                "start": t1_start,
                "end": t1_end,
                "candles": len(c1_clean),
                "available_days": m1_days,
                "archive_chunks": manifest_1m.get("archive_chunks", 0)
            },
            "5m": {
                "start": t5_start,
                "end": t5_end,
                "candles": len(c5_clean),
                "available_days": m5_days,
                "archive_chunks": manifest_5m.get("archive_chunks", 0)
            }
        },
        "requested_days": 365,
        "available_days_m1": m1_days,
        "available_days_m5": m5_days,
        "history_days": quality_report.history_days,
        "coverage_status": quality_report.coverage_status,
        "history_limit_issue": len(c1_clean) == 100000,
        "data_complete": quality_report.is_complete,
        "diagnostic": diag_summary,
        "data_quality": quality_report.model_dump(),
        "complete": quality_report.is_complete,
        "dataset_hash": quality_report.dataset_hash,
        "manifest_1m": manifest_1m,
        "manifest_5m": manifest_5m
    }


@router.post("/xauusd/download")
def download_xauusd_history(req: HistoryDownloadRequest):
    """
    Trigger download and local caching of historical XAUUSD data from MT5.
    """
    if req.symbol.upper() not in ["XAUUSD", "GOLD"]:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "code": "INVALID_SYMBOL", "message": "Only XAUUSD is supported."}
        )

    try:
        result = fetch_and_cache_historical_dataset(
            symbol=req.symbol,
            months=req.months,
            timeframe=req.timeframe,
            start_date=req.start,
            end_date=req.end,
            force_refresh=req.force_refresh
        )
        return {
            "status": "success",
            "message": f"Historical dataset update complete for {req.symbol}.",
            "data": result
        }
    except Exception as e:
        logger.error("Failed to download historical dataset: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "code": "DOWNLOAD_FAILED", "message": str(e)}
        )
