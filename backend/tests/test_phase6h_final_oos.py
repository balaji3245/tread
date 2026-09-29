"""
Phase 6H: Locked Final OOS Validation Tests
Validates:
1. Final OOS date boundaries and timestamps
2. Immutable pre-registration manifest hash
3. Frozen candidate parameters (V6F-H006: 0.15 ATR / 2m max wait)
4. Final OOS artifact contract and PASS_FINAL_OOS verdict
5. Baseline comparator immutability
6. Zero live strategy modifications and zero trading execution
"""
import json
import os
from pathlib import Path
import pytest

from app.experiments.baseline_config import get_frozen_baseline_config
from app.phase6h.models import (
    FINAL_OOS_DATE_RANGE,
    FINAL_OOS_END_TS,
    FINAL_OOS_START_TS,
    FinalOOSManifest,
    FinalOOSVerdict,
)


def test_final_oos_date_boundaries():
    """Verify exact canonical Final OOS boundaries."""
    assert FINAL_OOS_START_TS == 1787843700
    assert FINAL_OOS_END_TS == 1790377140
    assert FINAL_OOS_DATE_RANGE == "2026-08-27 to 2026-09-25"


def test_manifest_pre_registration_freeze():
    """Verify pre-registration manifest parameters are strictly frozen."""
    manifest = FinalOOSManifest()
    assert manifest.candidate_id == "V6F-H006"
    assert manifest.candidate_version == "phase6f-h006-v1"
    assert manifest.candidate_parameters["retrace_atr"] == 0.15
    assert manifest.candidate_parameters["max_wait_bars"] == 2
    assert manifest.baseline_version == "phase6-baseline-v1"
    assert manifest.dataset_hash == "e9db340c4efa9e63"
    assert manifest.spread_dollars == 0.30
    assert manifest.same_candle_policy == "stop_first"
    assert manifest.concurrency_policy == "max_concurrent_1"
    assert manifest.holding_time_policy == "60_minutes_entry_origin"

    # Hash should be non-empty sha256
    m_hash = manifest.compute_manifest_hash()
    assert len(m_hash) == 64


def test_final_oos_artifact_contract():
    """Verify that V6F-H006_final_oos_result.json is valid and contains verified PASS_FINAL_OOS verdict."""
    art_path = Path("data/experiments/V6F-H006_final_oos_result.json")
    assert art_path.exists(), "Final OOS validation result artifact must exist"

    with open(art_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["candidate_id"] == "V6F-H006"
    assert data["final_oos_locked"] is True
    assert data["final_oos_evaluated"] is True
    assert data["verdict"] == FinalOOSVerdict.PASS_FINAL_OOS.value
    assert data["live_strategy"] == "phase6-baseline-v1"
    assert data["trading_execution"] == "NONE"
    assert data["strategy_promotion"] == "BLOCKED"

    # Verify quantitative performance
    cand_m = data["candidate_metrics"]
    assert cand_m["executed_trades"] > 1000  # 1,146 trades
    assert cand_m["win_rate_pct"] > 50.0    # 52.62%
    assert cand_m["total_net_r"] > 0.0      # +112.82R
    assert cand_m["expectancy_r"] > 0.0     # +0.098R
    assert cand_m["profit_factor"] > 1.15   # 1.21

    # Verify baseline comparison
    base_m = data["baseline_metrics"]
    assert base_m["executed_trades"] == 1875
    assert base_m["total_net_r"] < 0.0      # -239.88R
    assert base_m["expectancy_r"] < 0.0     # -0.128R


def test_baseline_immutability_phase6h():
    """Verify baseline configuration remains strictly frozen."""
    base_cfg = get_frozen_baseline_config()
    assert base_cfg.version == "phase6-baseline-v1"
    assert base_cfg.signal_threshold == 7
    assert base_cfg.sl_atr_multiplier == 1.0
    assert base_cfg.tp1_atr_multiplier == 1.0
    assert base_cfg.tp2_atr_multiplier == 2.0
    assert base_cfg.max_holding_minutes == 60
    assert base_cfg.assumed_spread == 0.30
    assert base_cfg.same_candle_policy == "stop_first"
    assert base_cfg.max_concurrent_trades == 1
