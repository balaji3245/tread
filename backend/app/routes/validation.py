import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException

from app.backtester import parse_date_to_timestamp
from app.historical_data_cache import load_cached_candles, merge_and_save_candles
from app.market_data import market_service
from app.validation.report_builder import export_validation_to_csv_dict
from app.validation.robustness import run_strategy_validation
from app.validation.validation_models import ValidationRequest, ValidationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/validation", tags=["Strategy Validation & Walk-Forward"])

_LAST_VALIDATION_RESPONSE: Optional[ValidationResponse] = None


@router.post("/xauusd", response_model=ValidationResponse)
def run_xauusd_validation(req: ValidationRequest):
    """
    Execute comprehensive multi-period historical strategy validation,
    chronological walk-forward analysis, sensitivity matrices, and Monte Carlo simulation on XAUUSD.
    Executed synchronously so FastAPI offloads CPU-heavy validation to a worker thread.
    """
    global _LAST_VALIDATION_RESPONSE

    # 1. Input parameter validation
    if req.symbol.upper() not in ["XAUUSD", "GOLD"]:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "UNSUPPORTED_SYMBOL",
                "message": f"Symbol '{req.symbol}' is unsupported. Only 'XAUUSD' is supported."
            }
        )

    if req.train_days <= 0 or req.validation_days <= 0 or req.step_days <= 0:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "INVALID_WALK_FORWARD_CONFIG",
                "message": "train_days, validation_days, and step_days must all be greater than 0."
            }
        )

    if req.initial_capital <= 0:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "code": "INVALID_CAPITAL", "message": "initial_capital must be greater than 0."}
        )

    if req.sl_atr_multiplier <= 0 or req.tp1_atr_multiplier <= 0 or req.tp2_atr_multiplier <= 0:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "code": "INVALID_MULTIPLIER", "message": "ATR multipliers must be greater than 0."}
        )

    if req.monte_carlo_simulations < 10 or req.monte_carlo_simulations > 50000:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "INVALID_SIMULATION_COUNT",
                "message": "monte_carlo_simulations must be between 10 and 50,000."
            }
        )

    # 2. Date Range Parsing
    now_ts = int(time.time())
    if req.months:
        req_span_sec = req.months * 30 * 86400
        start_ts = now_ts - req_span_sec
        end_ts = now_ts
    else:
        start_ts = parse_date_to_timestamp(req.start, now_ts - (86400 * 90))
        end_ts = parse_date_to_timestamp(req.end, now_ts)

    if end_ts <= start_ts:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "INVALID_DATE_RANGE",
                "message": "end date must be strictly greater than start date."
            }
        )

    # 3. Retrieve Historical Data (From local cache first, then MT5)
    cached_1m, _ = load_cached_candles(req.symbol, "1m")
    cached_5m, _ = load_cached_candles(req.symbol, "5m")

    # If cached data covers the range, slice from cache
    need_mt5_fetch = False
    if not cached_1m or not cached_5m:
        need_mt5_fetch = True
    else:
        cache_start_1m = int(cached_1m[0]["time"])
        cache_end_1m = int(cached_1m[-1]["time"])
        # If cache doesn't cover requested range with 2-day margin
        if (start_ts < cache_start_1m - 86400) or (end_ts > cache_end_1m + 86400):
            need_mt5_fetch = True

    if need_mt5_fetch and market_service.mt5_client.is_connected:
        dt_start = datetime.fromtimestamp(start_ts, tz=timezone.utc)
        dt_end = datetime.fromtimestamp(end_ts, tz=timezone.utc)
        count_1m = max(5000, round((end_ts - start_ts) / 60))
        count_5m = max(1000, round((end_ts - start_ts) / 300))

        raw_1m = market_service.mt5_client.get_historical_candles_range(
            timeframe="1m", date_from=dt_start, date_to=dt_end, count=count_1m
        )
        raw_5m = market_service.mt5_client.get_historical_candles_range(
            timeframe="5m", date_from=dt_start, date_to=dt_end, count=count_5m
        )
        if raw_1m:
            cached_1m = merge_and_save_candles(req.symbol, "1m", raw_1m)
        if raw_5m:
            cached_5m = merge_and_save_candles(req.symbol, "5m", raw_5m)

    # Fallback to in-memory buffers if MT5 range failed or was partial
    if not cached_1m:
        cached_1m = market_service.candles_1m.get_candles(count=5000) or market_service.mt5_client.get_historical_candles("1m", 5000)
    if not cached_5m:
        cached_5m = market_service.candles_5m.get_candles(count=2000) or market_service.mt5_client.get_historical_candles("5m", 2000)

    # Offline test fallback if both cache and MT5 disconnected
    if len(cached_1m) < 40 and market_service.mt5_client._mock_candles_1m:
        cached_1m = market_service.mt5_client._mock_candles_1m
    if len(cached_5m) < 15 and market_service.mt5_client._mock_candles_5m:
        cached_5m = market_service.mt5_client._mock_candles_5m

    # Filter candles strictly to the available range that intersects with requested [start_ts, end_ts]
    # Keep warmup bars if available before start_ts
    candles_1m = [c for c in cached_1m if int(c["time"]) <= end_ts]
    candles_5m = [c for c in cached_5m if int(c["time"]) <= end_ts]

    # Filter start with slice or all available if dataset is smaller
    if candles_1m and int(candles_1m[0]["time"]) < start_ts:
        candles_1m = [c for c in candles_1m if int(c["time"]) >= start_ts - 3600]
    if candles_5m and int(candles_5m[0]["time"]) < start_ts:
        candles_5m = [c for c in candles_5m if int(c["time"]) >= start_ts - 7200]

    if len(candles_1m) < 40 and market_service.mt5_client._mock_candles_1m:
        candles_1m = market_service.mt5_client._mock_candles_1m
    if len(candles_5m) < 15 and market_service.mt5_client._mock_candles_5m:
        candles_5m = market_service.mt5_client._mock_candles_5m

    if len(candles_1m) < 40 or len(candles_5m) < 15:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": "INSUFFICIENT_HISTORICAL_DATA",
                "message": f"Retrieved only {len(candles_1m)} 1m and {len(candles_5m)} 5m candles. Minimum required is 40 1m and 15 5m bars."
            }
        )

    # 4. Run Strategy Validation Engine
    try:
        response = run_strategy_validation(
            candles_1m=candles_1m,
            candles_5m=candles_5m,
            req=req,
            requested_start_ts=start_ts,
            requested_end_ts=end_ts
        )
        _LAST_VALIDATION_RESPONSE = response
        return response
    except Exception as e:
        logger.error("Error executing strategy validation: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": "VALIDATION_EXECUTION_ERROR",
                "message": f"Strategy validation execution failed: {str(e)}"
            }
        )


@router.post("/xauusd/export")
def export_xauusd_validation(req: Optional[ValidationRequest] = None):
    """
    Export current or requested validation datasets into structured CSV files and full JSON.
    """
    global _LAST_VALIDATION_RESPONSE

    val_resp = _LAST_VALIDATION_RESPONSE
    if req is not None:
        val_resp = run_xauusd_validation(req)

    if val_resp is None:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": "NO_VALIDATION_DATA",
                "message": "No validation results available to export. Run validation first."
            }
        )

    csv_dict = export_validation_to_csv_dict(val_resp)

    return {
        "symbol": val_resp.symbol,
        "validation_run_id": val_resp.validation_run_id,
        "configuration_hash": val_resp.configuration_hash,
        "dataset_coverage": val_resp.dataset_coverage.model_dump(),
        "data_quality": val_resp.data_quality.model_dump(),
        "validation_status": val_resp.validation_status.model_dump(),
        "json_data": val_resp.model_dump(),
        "csv_files": csv_dict
    }

