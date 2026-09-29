"""
Phase 6H: One-Shot Final OOS Validation Script
Executes frozen candidate V6F-H006 on the canonical Final OOS window (2026-08-27 to 2026-09-25)
and generates permanent artifact backend/data/experiments/V6F-H006_final_oos_result.json.
"""
import copy
import gzip
import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.historical_data_quality import compute_dataset_hash
from app.phase6h.final_oos_engine import FinalOOSValidationEngine
from app.phase6h.models import (
    FINAL_OOS_DATE_RANGE,
    FINAL_OOS_END_TS,
    FINAL_OOS_START_TS,
    FinalOOSManifest,
    FinalOOSVerdict,
)
from app.signal_models import MarketSignal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phase6h_final_oos_runner")


def load_candles_and_signals():
    data_dir = backend_dir / "data"
    c1_path = data_dir / "XAUUSD_1m.json.gz"
    c5_path = data_dir / "XAUUSD_5m.json.gz"
    sig_path = data_dir / "signals_e9db340c4efa9e63_7.json.gz"

    logger.info("Loading M1 candles...")
    with gzip.open(c1_path, "rt", encoding="utf-8") as f:
        candles_1m = json.load(f)

    logger.info("Loading M5 candles...")
    with gzip.open(c5_path, "rt", encoding="utf-8") as f:
        candles_5m = json.load(f)

    logger.info("Loading precomputed signals...")
    with gzip.open(sig_path, "rt", encoding="utf-8") as f:
        raw_signals = json.load(f)
        precomputed_signals = {int(k): (MarketSignal(**v[0]), float(v[1])) for k, v in raw_signals.items()}

    logger.info("Loaded %d 1m bars, %d 5m bars, %d signals", len(candles_1m), len(candles_5m), len(precomputed_signals))
    return candles_1m, candles_5m, precomputed_signals


def main():
    logger.info("=== PHASE 6H: LOCKED FINAL OOS VALIDATION ===")
    candles_1m, candles_5m, precomputed_signals = load_candles_and_signals()
    ds_hash = compute_dataset_hash(candles_1m, candles_5m)
    logger.info("Dataset Hash: %s", ds_hash)

    manifest = FinalOOSManifest()
    manifest_hash = manifest.compute_manifest_hash()
    logger.info("Candidate ID: %s (%s)", manifest.candidate_id, manifest.candidate_version)
    logger.info("Manifest Hash: %s", manifest_hash)
    logger.info("Final OOS Period: %s (%d -> %d)", FINAL_OOS_DATE_RANGE, FINAL_OOS_START_TS, FINAL_OOS_END_TS)

    # Instantiate validation engine
    engine = FinalOOSValidationEngine(candles_1m, candles_5m, precomputed_signals)

    logger.info("Executing ONE-SHOT Final OOS validation...")
    artifact = engine.execute_final_oos_validation()

    # Save permanent JSON artifact
    out_dir = backend_dir / "data" / "experiments"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "V6F-H006_final_oos_result.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(artifact.model_dump(), f, indent=2)

    logger.info("Saved permanent validation artifact to %s", out_path)

    # Print summary
    base_m = artifact.baseline_metrics
    cand_m = artifact.candidate_metrics
    comp = artifact.comparison

    logger.info("=== FINAL OOS RESULTS SUMMARY ===")
    logger.info("Baseline:  %d trades, WR %.2f%%, Net %.2fR, Exp %.3fR, PF %.2f, MaxDD %.2fR, EarlyStop %.2f%%",
                base_m.executed_trades, base_m.win_rate_pct, base_m.total_net_r, base_m.expectancy_r, base_m.profit_factor, base_m.max_drawdown_r, base_m.early_stop_rate_pct)
    logger.info("V6F-H006:  %d trades, WR %.2f%%, Net %.2fR, Exp %.3fR, PF %.2f, MaxDD %.2fR, EarlyStop %.2f%%",
                cand_m.executed_trades, cand_m.win_rate_pct, cand_m.total_net_r, cand_m.expectancy_r, cand_m.profit_factor, cand_m.max_drawdown_r, cand_m.early_stop_rate_pct)
    logger.info("Delta:     %+d trades (reduc %.1f%%), WR %+.2f%%, Net %+.2fR, Exp %+.3fR, PF %+.2f, MaxDD Reduction %.2fR",
                comp.trades_delta, comp.trade_reduction_pct, comp.win_rate_delta_pct, comp.net_r_delta, comp.expectancy_delta_r, comp.profit_factor_delta, comp.drawdown_reduction_r)
    logger.info("Verdict:   %s", artifact.verdict.value)
    logger.info("Rationale: %s", artifact.verdict_rationale)


if __name__ == "__main__":
    main()
