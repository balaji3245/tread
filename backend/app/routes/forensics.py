"""
Phase 6: Signal Forensics API Endpoints
Exposes granular post-trade failure classifications, MAE/MFE distributions,
condition contribution matrices, and evidence-backed candidate hypotheses.
"""
import gzip
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.historical_data_cache import ensure_data_dir, load_cached_candles
from app.signal_forensics import (
    FailureCategoryStat,
    ForensicTradeRecord,
    ForensicsReport,
    SignalForensicsEngine,
)
from app.signal_models import MarketSignal

router = APIRouter(prefix="/api/forensics", tags=["Signal Forensics"])
logger = logging.getLogger(__name__)


def _get_or_compute_forensics_report() -> ForensicsReport:
    """Load cached forensics report from disk if present, or compute on-demand."""
    report_file = ensure_data_dir() / "reports" / "phase6_forensics_report.json"
    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ForensicsReport(**data)
        except Exception as e:
            logger.warning("Could not read cached forensics report: %s", e)

    # Compute on-demand
    c1, _ = load_cached_candles("XAUUSD", "1m")
    c5, _ = load_cached_candles("XAUUSD", "5m")
    if not c1 or not c5:
        raise HTTPException(
            status_code=404,
            detail="Historical XAUUSD candle cache not found. Please run history acquisition first."
        )

    sig_cache = None
    sig_path = ensure_data_dir() / "signals_e9db340c4efa9e63_7.json.gz"
    if sig_path.exists():
        try:
            with gzip.open(sig_path, "rt", encoding="utf-8") as f:
                raw = json.load(f)
                sig_cache = {int(k): (MarketSignal(**v[0]), float(v[1])) for k, v in raw.items()}
        except Exception as e:
            logger.warning("Could not load signals cache: %s", e)

    engine = SignalForensicsEngine()
    _, report = engine.analyze_forensics(c1, c5, precomputed_signals=sig_cache)
    return report


@router.get("/summary", response_model=ForensicsReport)
def get_forensics_summary() -> ForensicsReport:
    """Return the complete forensic diagnostic summary report."""
    return _get_or_compute_forensics_report()


@router.get("/failures", response_model=List[FailureCategoryStat])
def get_failure_categories() -> List[FailureCategoryStat]:
    """Return empirical failure categories ordered by occurrence frequency."""
    report = _get_or_compute_forensics_report()
    return report.failure_categories


@router.get("/hypotheses")
def get_candidate_hypotheses():
    """Return evidence-backed candidate hypotheses for strategy improvement."""
    report = _get_or_compute_forensics_report()
    return report.candidate_hypotheses


@router.get("/excursions")
def get_forensics_excursions():
    """Return granular MAE/MFE distributions, time-to-excursions, and recovery tables."""
    from app.signal_forensics import get_excursions_forensic_report
    return get_excursions_forensic_report()


@router.get("/entry-quality")
def get_forensics_entry_quality():
    """Return entry quality analysis including overextension and S/R clearance."""
    from app.signal_forensics import get_entry_quality_forensic_report
    return get_entry_quality_forensic_report()


@router.get("/holding-time")
def get_forensics_holding_time():
    """Return trade duration buckets and early noise analysis (1-2m trades)."""
    from app.signal_forensics import get_holding_time_forensic_report
    return get_holding_time_forensic_report()


@router.get("/exit-paths")
def get_forensics_exit_paths(count: int = Query(default=20, ge=1, le=100)):
    """Return representative historical exit paths (Entry -> MAE -> MFE -> Exit)."""
    from app.signal_forensics import get_exit_paths_forensic_samples
    samples = get_exit_paths_forensic_samples(count=count)
    return {"count": len(samples), "samples": samples}

