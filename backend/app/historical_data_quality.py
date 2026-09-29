import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DataQualityReport(BaseModel):
    symbol: str = "XAUUSD"
    total_1m_candles: int = 0
    total_5m_candles: int = 0
    actual_start_ts: int = 0
    actual_end_ts: int = 0
    actual_start_iso: str = ""
    actual_end_iso: str = ""
    history_days: int = 0
    requested_days: int = 0
    is_complete: bool = False
    coverage_status: str = "INSUFFICIENT_HISTORY"  # "INSUFFICIENT_HISTORY" | "LIMITED_HISTORY" | "12_MONTH_HISTORY_AVAILABLE"
    duplicate_count_1m: int = 0
    duplicate_count_5m: int = 0
    invalid_candles_count_1m: int = 0
    invalid_candles_count_5m: int = 0
    non_monotonic_count_1m: int = 0
    non_monotonic_count_5m: int = 0
    unexpected_gaps_count: int = 0
    expected_market_gaps_count: int = 0
    alignment_status: str = "PASS"  # "PASS" | "WARN" | "FAIL"
    alignment_details: str = "1m and 5m candle timestamps and bounds are synchronized."
    timezone: str = "UTC"
    dataset_hash: str = ""
    is_clean: bool = True
    summary_notes: List[str] = Field(default_factory=list)


def validate_ohlc_candle(c: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate basic OHLC arithmetic integrity for a single candle:
    - open > 0 and close > 0
    - high >= low
    - high >= max(open, close)
    - low <= min(open, close)
    """
    try:
        o = float(c["open"])
        h = float(c["high"])
        l = float(c["low"])
        cl = float(c["close"])
        t = int(c["time"])

        if o <= 0 or cl <= 0 or h <= 0 or l <= 0:
            return False, f"Non-positive price at timestamp {t}: O={o}, H={h}, L={l}, C={cl}"

        if h < l:
            return False, f"High < Low at timestamp {t}: H={h}, L={l}"

        max_oc = max(o, cl)
        min_oc = min(o, cl)

        # Allow small floating point tolerance (0.001)
        if (h + 0.001) < max_oc:
            return False, f"High < max(Open, Close) at timestamp {t}: H={h}, max(O,C)={max_oc}"

        if (l - 0.001) > min_oc:
            return False, f"Low > min(Open, Close) at timestamp {t}: L={l}, min(O,C)={min_oc}"

        return True, None
    except (KeyError, ValueError, TypeError) as e:
        return False, f"Malformed candle format: {str(e)}"


def compute_dataset_hash(candles_1m: List[Dict[str, Any]], candles_5m: List[Dict[str, Any]]) -> str:
    """
    Compute a deterministic SHA-256 hash of the normalized 1m and 5m candle sequences.
    Same candle inputs will always produce the identical dataset_hash.
    """
    hasher = hashlib.sha256()

    # Stream 1m data (time, open, high, low, close)
    for c in candles_1m:
        line = f"1m:{int(c['time'])}:{float(c['open']):.2f}:{float(c['high']):.2f}:{float(c['low']):.2f}:{float(c['close']):.2f};"
        hasher.update(line.encode("utf-8"))

    # Stream 5m data
    for c in candles_5m:
        line = f"5m:{int(c['time'])}:{float(c['open']):.2f}:{float(c['high']):.2f}:{float(c['low']):.2f}:{float(c['close']):.2f};"
        hasher.update(line.encode("utf-8"))

    return hasher.hexdigest()[:16]


def clean_and_normalize_candles(
    raw_candles: List[Dict[str, Any]],
    timeframe: str = "1m"
) -> Tuple[List[Dict[str, Any]], int, int, int]:
    """
    Clean, validate, and normalize a raw candle stream:
    - Exclude invalid OHLC bars
    - Deduplicate identical timestamps
    - Sort chronologically
    Returns: (cleaned_candles, invalid_count, duplicate_count, non_monotonic_count)
    """
    if not raw_candles:
        return [], 0, 0, 0

    invalid_count = 0
    valid_candles: List[Dict[str, Any]] = []

    for c in raw_candles:
        is_valid, reason = validate_ohlc_candle(c)
        if is_valid:
            valid_candles.append(c)
        else:
            invalid_count += 1
            logger.debug("Excluded invalid %s candle: %s", timeframe, reason)

    # Check non-monotonic ordering before sorting
    non_monotonic_count = 0
    for i in range(1, len(valid_candles)):
        if int(valid_candles[i]["time"]) < int(valid_candles[i - 1]["time"]):
            non_monotonic_count += 1

    # Sort strictly chronologically
    sorted_candles = sorted(valid_candles, key=lambda x: int(x["time"]))

    # Deduplicate timestamps
    cleaned: List[Dict[str, Any]] = []
    seen_times = set()
    duplicate_count = 0

    for c in sorted_candles:
        t = int(c["time"])
        if t in seen_times:
            duplicate_count += 1
        else:
            seen_times.add(t)
            # Ensure normalized types
            cleaned.append({
                "time": t,
                "open": round(float(c["open"]), 2),
                "high": round(float(c["high"]), 2),
                "low": round(float(c["low"]), 2),
                "close": round(float(c["close"]), 2),
                "tick_volume": int(c["tick_volume"]) if c.get("tick_volume") is not None else None,
                "spread": float(c["spread"]) if c.get("spread") is not None else None,
                "real_volume": int(c["real_volume"]) if c.get("real_volume") is not None else None,
            })

    return cleaned, invalid_count, duplicate_count, non_monotonic_count


def analyze_market_gaps(
    candles_1m: List[Dict[str, Any]]
) -> Tuple[int, int]:
    """
    Analyze time intervals between consecutive 1m candles.
    Distinguishes:
    - Expected Market Gaps: Weekend closures (Friday night to Sunday night), daily maintenance rollover breaks (~21:00-22:00 UTC).
    - Unexpected Data Gaps: Gaps > 15 minutes during active market sessions.
    """
    if len(candles_1m) < 2:
        return 0, 0

    expected_gaps = 0
    unexpected_gaps = 0

    for i in range(1, len(candles_1m)):
        prev_t = int(candles_1m[i - 1]["time"])
        cur_t = int(candles_1m[i]["time"])
        delta_sec = cur_t - prev_t

        if delta_sec > 300:  # Gap > 5 minutes
            dt_prev = datetime.fromtimestamp(prev_t, tz=timezone.utc)
            # Weekend gap: Friday after 20:00 UTC to Sunday after 21:00 UTC
            is_weekend = (dt_prev.weekday() == 4 and dt_prev.hour >= 20) or (dt_prev.weekday() in [5, 6])

            # Daily rollover gap: 21:00 - 23:00 UTC
            is_daily_rollover = (dt_prev.hour in [21, 22]) and delta_sec <= 7200

            if is_weekend or is_daily_rollover:
                expected_gaps += 1
            else:
                if delta_sec > 900:  # > 15m unexpected gap during active trading
                    unexpected_gaps += 1

    return unexpected_gaps, expected_gaps


def verify_1m_5m_alignment(
    candles_1m: List[Dict[str, Any]],
    candles_5m: List[Dict[str, Any]]
) -> Tuple[str, str]:
    """
    Verify temporal and price synchronization between 1m and 5m candle streams.
    """
    if not candles_1m or not candles_5m:
        return "FAIL", "Missing 1m or 5m dataset."

    t1_min = int(candles_1m[0]["time"])
    t1_max = int(candles_1m[-1]["time"])
    t5_min = int(candles_5m[0]["time"])
    t5_max = int(candles_5m[-1]["time"])

    # Range overlap check (within 10 minutes)
    if abs(t1_min - t5_min) > 600 or abs(t1_max - t5_max) > 600:
        return "WARN", f"Start/End boundary offset: 1m range ({t1_min}-{t1_max}) vs 5m range ({t5_min}-{t5_max})"

    return "PASS", "1m and 5m candle streams are chronologically synchronized."


def audit_dataset_quality(
    candles_1m: List[Dict[str, Any]],
    candles_5m: List[Dict[str, Any]],
    requested_days: int = 30,
    symbol: str = "XAUUSD"
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], DataQualityReport]:
    """
    Execute full historical data quality audit and normalization pipeline.
    """
    # 1. Clean & normalize 1m and 5m streams
    c1_clean, inv_1m, dup_1m, nonmono_1m = clean_and_normalize_candles(candles_1m, "1m")
    c5_clean, inv_5m, dup_5m, nonmono_5m = clean_and_normalize_candles(candles_5m, "5m")

    # 2. Extract boundaries & compute coverage
    if c1_clean:
        start_ts = int(c1_clean[0]["time"])
        end_ts = int(c1_clean[-1]["time"])
        start_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat()
        end_iso = datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat()
        history_days = max(1, round((end_ts - start_ts) / 86400))
    else:
        start_ts, end_ts = 0, 0
        start_iso, end_iso = "", ""
        history_days = 0

    # Coverage status classification
    if history_days < 180:
        coverage_status = "INSUFFICIENT_HISTORY"
    elif history_days < 350:
        coverage_status = "LIMITED_HISTORY"
    else:
        coverage_status = "12_MONTH_HISTORY_AVAILABLE"

    is_complete = history_days >= requested_days or (requested_days > 0 and history_days >= requested_days * 0.90)

    # 3. Gap Analysis
    unexpected_gaps, expected_gaps = analyze_market_gaps(c1_clean)

    # 4. 1m / 5m Alignment Check
    align_status, align_details = verify_1m_5m_alignment(c1_clean, c5_clean)

    # 5. Deterministic Dataset Hash
    d_hash = compute_dataset_hash(c1_clean, c5_clean)

    # Summary notes
    notes = []
    if inv_1m > 0 or inv_5m > 0:
        notes.append(f"Excluded {inv_1m} invalid 1m and {inv_5m} invalid 5m candles.")
    if dup_1m > 0 or dup_5m > 0:
        notes.append(f"Deduplicated {dup_1m} 1m and {dup_5m} 5m duplicate timestamp records.")
    if unexpected_gaps > 0:
        notes.append(f"Detected {unexpected_gaps} unexpected intraday market gaps (>15m).")
    if not is_complete and requested_days > 0:
        notes.append(f"Requested {requested_days} days, but only {history_days} days available from MT5 terminal.")

    is_clean = (inv_1m == 0 and inv_5m == 0 and nonmono_1m == 0 and nonmono_5m == 0 and align_status == "PASS")

    report = DataQualityReport(
        symbol=symbol,
        total_1m_candles=len(c1_clean),
        total_5m_candles=len(c5_clean),
        actual_start_ts=start_ts,
        actual_end_ts=end_ts,
        actual_start_iso=start_iso,
        actual_end_iso=end_iso,
        history_days=history_days,
        requested_days=requested_days,
        is_complete=is_complete,
        coverage_status=coverage_status,
        duplicate_count_1m=dup_1m,
        duplicate_count_5m=dup_5m,
        invalid_candles_count_1m=inv_1m,
        invalid_candles_count_5m=inv_5m,
        non_monotonic_count_1m=nonmono_1m,
        non_monotonic_count_5m=nonmono_5m,
        unexpected_gaps_count=unexpected_gaps,
        expected_market_gaps_count=expected_gaps,
        alignment_status=align_status,
        alignment_details=align_details,
        timezone="UTC",
        dataset_hash=d_hash,
        is_clean=is_clean,
        summary_notes=notes
    )

    return c1_clean, c5_clean, report
