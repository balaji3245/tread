"""
Phase 6I: Shadow Monitoring REST API Router
Provides read-only telemetry, state machine status, journal logs, and paper-trade statistics
with explicit epoch separation (PRE_FIX vs POST_TIMESTAMP_FIX).
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.phase6i.models import ShadowHealthStatus, ShadowJournalEntry
from app.phase6i.shadow_engine import live_shadow_engine, JOURNAL_FILE, DAILY_SUMMARY_FILE

router = APIRouter(prefix="/api/shadow", tags=["Shadow Monitoring"])

# Canonical Epoch Boundary for Timestamp Synchronization Fix
EPOCH_POST_FIX_START_UTC = "2026-09-28T19:00:00+00:00"
EPOCH_PRE_FIX_LAST_EVENT_ID = "EVT_XAUUSD_1m_1790572598_SHORT_TIMEOUT"


def _compute_epoch_metrics(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate rolling trade and signal metrics for a subset of journal entries."""
    total_signals = len(entries)
    filled_count = 0
    timeouts_count = 0
    invals_count = 0
    concurrency_blocked_count = 0
    virtual_trades = []

    for data in entries:
        st = data.get("entry_state")
        if data.get("entry_triggered"):
            filled_count += 1
            if data.get("result"):
                virtual_trades.append(data)
        elif data.get("timeout") or st == "TIMED_OUT":
            timeouts_count += 1
        elif data.get("invalidation") or st == "INVALIDATED":
            invals_count += 1
        elif st == "CONCURRENCY_BLOCKED":
            concurrency_blocked_count += 1

    n_trades = len(virtual_trades)
    wins = sum(1 for t in virtual_trades if (t.get("r_multiple") or 0) > 0)
    losses = sum(1 for t in virtual_trades if (t.get("r_multiple") or 0) < 0)
    net_r = sum((t.get("r_multiple") or 0) for t in virtual_trades)
    gp = sum((t.get("r_multiple") or 0) for t in virtual_trades if (t.get("r_multiple") or 0) > 0)
    gl = sum(abs(t.get("r_multiple") or 0) for t in virtual_trades if (t.get("r_multiple") or 0) < 0)
    pf = round(gp / gl, 2) if gl > 0 else (1.0 if n_trades > 0 and wins == n_trades else 0.0)

    return {
        "signals_count": total_signals,
        "filled_count": filled_count,
        "timeouts_count": timeouts_count,
        "invalidations_count": invals_count,
        "concurrency_blocked_count": concurrency_blocked_count,
        "virtual_trades_count": n_trades,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wins / n_trades * 100, 2) if n_trades > 0 else 0.0,
        "total_net_r": round(net_r, 2),
        "expectancy_r": round(net_r / n_trades, 3) if n_trades > 0 else 0.0,
        "profit_factor": pf,
    }


@router.get("/status", response_model=ShadowHealthStatus)
def get_shadow_status() -> ShadowHealthStatus:
    """Return live status, market state, and operational telemetry of the H006 shadow engine."""
    return live_shadow_engine.get_health_status()


@router.get("/journal", response_model=List[Dict[str, Any]])
def get_shadow_journal(
    limit: int = Query(50, ge=1, le=500),
    epoch: Optional[str] = Query(None, description="Filter epoch: 'prefix', 'postfix', 'live', or all"),
) -> List[Dict[str, Any]]:
    """Return recent immutable shadow journal records with optional epoch filtering."""
    if not JOURNAL_FILE.exists():
        return []

    entries = []
    try:
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    ts_utc = data.get("timestamp_utc", "")
                    if epoch in ["postfix", "live"] and ts_utc < EPOCH_POST_FIX_START_UTC:
                        continue
                    if epoch == "prefix" and ts_utc >= EPOCH_POST_FIX_START_UTC:
                        continue
                    entries.append(data)
        return entries[-limit:][::-1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read shadow journal: {e}")


@router.get("/summary", response_model=Dict[str, Any])
def get_shadow_summary(
    epoch: str = Query("live", description="Target epoch: 'live' (post-fix), 'prefix', or 'all'"),
) -> Dict[str, Any]:
    """Return shadow performance metrics with forensic epoch separation."""
    status = live_shadow_engine.get_health_status()

    all_entries = []
    prefix_entries = []
    postfix_entries = []

    if JOURNAL_FILE.exists():
        try:
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        all_entries.append(data)
                        if data.get("timestamp_utc", "") < EPOCH_POST_FIX_START_UTC:
                            prefix_entries.append(data)
                        else:
                            postfix_entries.append(data)
        except Exception:
            pass

    prefix_metrics = _compute_epoch_metrics(prefix_entries)
    postfix_metrics = _compute_epoch_metrics(postfix_entries)
    all_metrics = _compute_epoch_metrics(all_entries)

    # Select target epoch metrics for top-level display
    if epoch.lower() in ["postfix", "live"]:
        active_metrics = postfix_metrics
        active_epoch_name = "POST_TIMESTAMP_FIX (LIVE PROSPECTIVE)"
    elif epoch.lower() == "prefix":
        active_metrics = prefix_metrics
        active_epoch_name = "PRE_FIX (HISTORICAL AUDIT ARTIFACT)"
    else:
        active_metrics = all_metrics
        active_epoch_name = "ALL_EPOCHS_COMBINED"

    return {
        "candidate": "V6F-H006",
        "candidate_version": "phase6f-h006-v1",
        "mode": "SHADOW_ONLY (PAPER VALIDATION)",
        "live_strategy": "phase6-baseline-v1",
        "trading_execution": "NONE",
        "market_feed_status": status.market_feed_status,
        "current_epoch": active_epoch_name,
        "epoch_boundary_utc": EPOCH_POST_FIX_START_UTC,
        "epoch_boundary_event_id": EPOCH_PRE_FIX_LAST_EVENT_ID,
        **active_metrics,
        "epochs_breakdown": {
            "pre_fix": {
                "epoch_label": "PRE_FIX (Pre-timestamp synchronization, 3h delta artifact)",
                "events_count": len(prefix_entries),
                "artificial_timeouts": prefix_metrics["timeouts_count"],
                "fills_count": prefix_metrics["filled_count"],
                "invalidations_count": prefix_metrics["invalidations_count"],
                "virtual_trades_count": prefix_metrics["virtual_trades_count"],
                "note": "Preserved immutable for forensic audit; caused by host-UTC vs broker GMT+3 timebase delta.",
            },
            "post_fix": {
                "epoch_label": "POST_TIMESTAMP_FIX (Live prospective synchronized feed)",
                "signals_count": len(postfix_entries),
                "fills_count": postfix_metrics["filled_count"],
                "timeouts_count": postfix_metrics["timeouts_count"],
                "invalidations_count": postfix_metrics["invalidations_count"],
                "concurrency_blocked_count": postfix_metrics["concurrency_blocked_count"],
                "virtual_trades_count": postfix_metrics["virtual_trades_count"],
                "wins": postfix_metrics["wins"],
                "losses": postfix_metrics["losses"],
                "win_rate_pct": postfix_metrics["win_rate_pct"],
                "total_net_r": postfix_metrics["total_net_r"],
                "expectancy_r": postfix_metrics["expectancy_r"],
                "profit_factor": postfix_metrics["profit_factor"],
            },
            "all": all_metrics,
        },
        "checkpoint_milestone": status.checkpoint_milestone,
        "disclaimer": "PAPER / SHADOW — NO REAL ORDERS SUBMITTED",
    }

