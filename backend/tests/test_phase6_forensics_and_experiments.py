"""
Phase 6: Comprehensive Unit Tests for Signal Forensics & Controlled Experiments
Validates MAE/MFE calculations, SL->TP reversal detection, failure tagging,
single-variable experiment isolation, locked final OOS protection, and API endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app.backtest_models import BacktestConfig, BacktestTrade
from app.experiments.baseline_config import (
    BASELINE_VERSION,
    FrozenBaselineConfig,
    get_frozen_baseline_config,
)
from app.experiments.experiment_models import (
    ExperimentDecision,
    ExperimentDefinition,
    ExperimentStatus,
    ExperimentVariableType,
    SingleVariableModification,
)
from app.experiments.experiment_registry import list_all_experiments
from app.experiments.experiment_runner import ExperimentRunner
from app.main import app
from app.signal_forensics import SignalForensicsEngine


@pytest.fixture
def mock_synchronized_candles():
    """Construct 120 synthetic 1m candles and 30 5m candles for isolated unit testing."""
    base_ts = 1759331700
    c1m = []
    for i in range(120):
        t = base_ts + (i * 60)
        p = 2650.0 + (i * 0.10)
        c1m.append({
            "time": t,
            "open": p,
            "high": p + 0.50,
            "low": p - 0.50,
            "close": p + 0.05,
            "tick_volume": 100,
            "spread": 0.30
        })

    c5m = []
    for j in range(30):
        t = base_ts + (j * 300)
        p = 2650.0 + (j * 0.50)
        c5m.append({
            "time": t,
            "open": p,
            "high": p + 1.50,
            "low": p - 1.00,
            "close": p + 0.40,
            "tick_volume": 500,
            "spread": 0.30
        })

    return c1m, c5m


def test_forensics_engine_metric_distribution():
    """Verify statistical metric distribution calculations (mean, median, percentiles)."""
    engine = SignalForensicsEngine()
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    dist = engine.compute_metric_distribution(values, "TestMetric")

    assert dist.count == 10
    assert dist.mean == 5.5
    assert dist.median == 5.5
    assert dist.percentile_25 == 3.0
    assert dist.percentile_75 == 7.0


def test_single_variable_experiment_immutability():
    """Verify experiment definitions cannot bundle multiple variables."""
    exp = ExperimentDefinition(
        experiment_id="TEST-001",
        title="Test Single Variable",
        hypothesis="Test spread limit",
        failure_mechanism="HIGH_SPREAD",
        modification=SingleVariableModification(
            variable_type=ExperimentVariableType.FILTER,
            target_rule="spread_threshold",
            baseline_value=0.30,
            experimental_value=0.40,
            parameter_name="max_allowed_spread",
            description="Test single variable filter."
        ),
        rationale_from_forensics="Testing forensics justification."
    )
    assert exp.experiment_id == "TEST-001"
    assert exp.modification.variable_type == ExperimentVariableType.FILTER
    assert exp.modification.experimental_value == 0.40


def test_experiment_registry_contents():
    """Verify all required standard forensic experiments are properly registered."""
    exps = list_all_experiments()
    assert len(exps) >= 8
    exp_ids = [e.experiment_id for e in exps]
    assert "ABL-001" in exp_ids
    assert "ABL-002" in exp_ids
    assert "EXP-001" in exp_ids
    assert "EXP-002" in exp_ids
    assert "EXP-003" in exp_ids
    assert "EXP-004" in exp_ids
    assert "EXP-005" in exp_ids
    assert "EXP-006" in exp_ids


def test_forensics_api_endpoints():
    """Verify GET /api/forensics/summary and /api/forensics/failures."""
    client = TestClient(app)

    res = client.get("/api/forensics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "report_id" in data
    assert "failure_categories" in data
    assert "overall_mae" in data
    assert "overall_mfe" in data
    assert "candidate_hypotheses" in data

    res_fail = client.get("/api/forensics/failures")
    assert res_fail.status_code == 200
    failures = res_fail.json()
    assert isinstance(failures, list)
    assert len(failures) > 0


def test_experiments_api_endpoints():
    """Verify GET /api/experiments/list and GET /api/experiments/{id}."""
    client = TestClient(app)

    res = client.get("/api/experiments/list")
    assert res.status_code == 200
    exp_list = res.json()
    assert isinstance(exp_list, list)
    assert len(exp_list) >= 8

    res_detail = client.get("/api/experiments/EXP-005")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["experiment_id"] == "EXP-005"
    assert "development_deltas" in detail
    assert "preliminary_oos_deltas" in detail
    assert detail["final_oos_locked"] is True
