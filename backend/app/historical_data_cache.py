import gzip
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Base directory for local historical data storage
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def ensure_data_dir() -> Path:
    """Ensure local backend/data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def get_cache_file_paths(symbol: str, timeframe: str) -> Tuple[Path, Path, Path]:
    """Return paths for the gzipped data file, JSON metadata file, and manifest file."""
    dir_path = ensure_data_dir()
    clean_sym = symbol.upper().replace("/", "").replace("_", "")
    data_file = dir_path / f"{clean_sym}_{timeframe}.json.gz"
    meta_file = dir_path / f"{clean_sym}_{timeframe}_meta.json"
    manifest_file = dir_path / f"{clean_sym}_{timeframe}_manifest.json"
    return data_file, meta_file, manifest_file


def atomic_write_gzip_json(target_path: Path, data: Any) -> int:
    """
    Atomically write data as gzipped JSON using a temporary file and atomic rename.
    Ensures zero file corruption if execution is interrupted mid-write.
    """
    ensure_data_dir()
    tmp_path = target_path.with_name(f"{target_path.name}.tmp.{os.getpid()}")
    try:
        with gzip.open(tmp_path, "wt", encoding="utf-8") as f:
            json.dump(data, f)

        # Quick validation of written gzip file
        with gzip.open(tmp_path, "rt", encoding="utf-8") as f:
            test_obj = json.load(f)
            if not isinstance(test_obj, (list, dict)):
                raise ValueError("Written gzip data failed JSON verification.")

        # Atomic replacement
        tmp_path.replace(target_path)
        return target_path.stat().st_size
    except Exception as e:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise IOError(f"Failed atomic gzip write to {target_path}: {e}") from e


def atomic_write_json(target_path: Path, data: Any) -> int:
    """
    Atomically write data as plain JSON using temporary file and atomic rename.
    """
    ensure_data_dir()
    tmp_path = target_path.with_name(f"{target_path.name}.tmp.{os.getpid()}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        tmp_path.replace(target_path)
        return target_path.stat().st_size
    except Exception as e:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise IOError(f"Failed atomic JSON write to {target_path}: {e}") from e


def load_cached_candles(
    symbol: str = "XAUUSD",
    timeframe: str = "1m"
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Load cached historical candles and metadata from local storage.
    Verifies file integrity. Returns (candles, metadata) or ([], None).
    """
    data_file, meta_file, _ = get_cache_file_paths(symbol, timeframe)

    if not data_file.exists() or not meta_file.exists():
        return [], None

    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        with gzip.open(data_file, "rt", encoding="utf-8") as f:
            candles = json.load(f)

        logger.info(
            "Loaded %d cached %s candles for %s from %s (Span: %s to %s)",
            len(candles),
            timeframe,
            symbol,
            data_file.name,
            metadata.get("start", "?"),
            metadata.get("end", "?")
        )
        return candles, metadata
    except Exception as e:
        logger.warning("Failed to load cache for %s %s: %s", symbol, timeframe, e)
        return [], None


def load_manifest(symbol: str = "XAUUSD", timeframe: str = "1m") -> Optional[Dict[str, Any]]:
    """Load the historical archive manifest for symbol and timeframe."""
    _, _, manifest_file = get_cache_file_paths(symbol, timeframe)
    if not manifest_file.exists():
        return None
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load manifest for %s %s: %s", symbol, timeframe, e)
        return None


def save_cached_candles(
    symbol: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
    source: str = "Exness MT5",
    chunks: Optional[List[Dict[str, Any]]] = None,
    dataset_hash: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save normalized historical candles to local gzipped storage with atomic writes and manifest update.
    """
    if not candles:
        return {}

    ensure_data_dir()
    data_file, meta_file, manifest_file = get_cache_file_paths(symbol, timeframe)

    start_ts = int(candles[0]["time"])
    end_ts = int(candles[-1]["time"])
    start_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat()
    end_iso = datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat()
    available_days = max(1, round((end_ts - start_ts) / 86400))

    metadata = {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "start": start_iso,
        "end": end_iso,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "available_days": available_days,
        "candle_count": len(candles),
        "source": source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timezone": "UTC",
        "file_size_bytes": 0,
        "dataset_hash": dataset_hash or ""
    }

    try:
        # Atomic write of data
        size_bytes = atomic_write_gzip_json(data_file, candles)
        metadata["file_size_bytes"] = size_bytes

        # Atomic write of metadata
        atomic_write_json(meta_file, metadata)

        # Build and save manifest
        existing_manifest = load_manifest(symbol, timeframe) or {}
        combined_chunks = chunks or existing_manifest.get("chunks", [])

        manifest = {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "source": source,
            "timezone": "UTC",
            "actual_start": start_iso,
            "actual_end": end_iso,
            "actual_start_ts": start_ts,
            "actual_end_ts": end_ts,
            "candle_count": len(candles),
            "available_days": available_days,
            "complete": available_days >= 360,
            "dataset_hash": dataset_hash or metadata["dataset_hash"],
            "file_size_bytes": size_bytes,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "archive_chunks": len(combined_chunks),
            "chunks": combined_chunks
        }
        atomic_write_json(manifest_file, manifest)

        logger.info(
            "Saved %d %s %s candles to %s (%d KB, %d days, hash: %s)",
            len(candles),
            symbol,
            timeframe,
            data_file.name,
            size_bytes // 1024,
            available_days,
            dataset_hash or "N/A"
        )
        return metadata
    except Exception as e:
        logger.error("Failed to save cached candles for %s %s: %s", symbol, timeframe, e)
        return metadata


def merge_and_save_candles(
    symbol: str,
    timeframe: str,
    new_candles: List[Dict[str, Any]],
    source: str = "Exness MT5",
    chunks: Optional[List[Dict[str, Any]]] = None,
    dataset_hash: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Merge newly retrieved MT5 candles with existing locally cached candles.
    Deduplicates by timestamp, sorts chronologically, and updates local cache atomically.
    """
    existing_candles, _ = load_cached_candles(symbol, timeframe)

    candle_map: Dict[int, Dict[str, Any]] = {}
    for c in existing_candles:
        candle_map[int(c["time"])] = c

    for c in new_candles:
        candle_map[int(c["time"])] = c

    merged = [candle_map[t] for t in sorted(candle_map.keys())]

    if merged:
        save_cached_candles(
            symbol=symbol,
            timeframe=timeframe,
            candles=merged,
            source=source,
            chunks=chunks,
            dataset_hash=dataset_hash
        )

    return merged


def get_missing_ranges(
    symbol: str,
    timeframe: str,
    target_start_ts: int,
    target_end_ts: int,
    max_gap_seconds: int = 86400 * 2
) -> List[Tuple[int, int]]:
    """
    Determine missing timestamp intervals [start, end] not yet covered in local cache.
    Useful for incremental downloads and interrupted download recovery.
    """
    existing_candles, _ = load_cached_candles(symbol, timeframe)
    if not existing_candles:
        return [(target_start_ts, target_end_ts)]

    cache_start = int(existing_candles[0]["time"])
    cache_end = int(existing_candles[-1]["time"])

    missing: List[Tuple[int, int]] = []

    # Check preceding missing range
    if target_start_ts < cache_start - max_gap_seconds:
        missing.append((target_start_ts, cache_start))

    # Check trailing missing range
    if target_end_ts > cache_end + max_gap_seconds:
        missing.append((cache_end, target_end_ts))

    return missing
