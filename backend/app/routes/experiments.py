"""
Phase 6: Strategy Experiments API Endpoints
Provides registration, execution, and benchmarking of controlled single-variable hypotheses.
"""
import gzip
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.experiments.experiment_audit import run_experiment_audit
from app.experiments.experiment_models import (
    ExperimentAuditReport,
    ExperimentDecision,
    ExperimentDefinition,
    ExperimentResult,
    ExperimentStatus,
)
from app.experiments.experiment_registry import (
    EXPERIMENT_REGISTRY,
    get_experiment_by_id,
    list_all_experiments,
)
from app.experiments.experiment_runner import ExperimentRunner
from app.historical_data_cache import ensure_data_dir, load_cached_candles
from app.signal_models import MarketSignal

router = APIRouter(prefix="/api/experiments", tags=["Strategy Experiments"])
logger = logging.getLogger(__name__)


class ExperimentRunRequest(BaseModel):
    experiment_id: str


def _load_or_run_experiment(experiment_id: str) -> ExperimentResult:
    """Load cached experiment result or execute it against the dataset."""
    exp_def = get_experiment_by_id(experiment_id)
    if not exp_def:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment '{experiment_id}' not found in registry."
        )

    # Check disk cache
    res_file = ensure_data_dir() / "experiments" / f"{exp_def.experiment_id}_result.json"
    if res_file.exists():
        try:
            with open(res_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ExperimentResult(**data)
        except Exception as e:
            logger.warning("Could not load cached experiment result: %s", e)

    # Execute experiment
    c1, _ = load_cached_candles("XAUUSD", "1m")
    c5, _ = load_cached_candles("XAUUSD", "5m")
    if not c1 or not c5:
        raise HTTPException(
            status_code=404,
            detail="Historical candle cache not found. Please run history download first."
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

    runner = ExperimentRunner()
    result = runner.run_experiment(exp_def, c1, c5, precomputed_signals=sig_cache)
    return result


@router.get("")
@router.get("/list")
def list_experiments():
    """List all registered single-variable experiments with their latest status and deltas."""
    results: List[Dict[str, Any]] = []
    for exp in list_all_experiments():
        res_file = ensure_data_dir() / "experiments" / f"{exp.experiment_id}_result.json"
        summary_info = {
            "experiment_id": exp.experiment_id,
            "title": exp.title,
            "hypothesis": exp.hypothesis,
            "failure_mechanism": exp.failure_mechanism,
            "variable_type": exp.modification.variable_type.value,
            "parameter_name": exp.modification.parameter_name,
            "baseline_value": exp.modification.baseline_value,
            "experimental_value": exp.modification.experimental_value,
            "status": "DRAFT",
            "decision": "NEEDS_MORE_DATA",
            "delta_expectancy": None,
            "delta_profit_factor": None,
            "delta_total_r": None,
            "executed_at_iso": None
        }
        if res_file.exists():
            try:
                with open(res_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    summary_info["status"] = cached_data.get("status")
                    summary_info["decision"] = cached_data.get("decision")
                    summary_info["executed_at_iso"] = cached_data.get("executed_at_iso")
                    prelim_deltas = cached_data.get("preliminary_oos_deltas", {})
                    summary_info["delta_expectancy"] = prelim_deltas.get("delta_expectancy")
                    summary_info["delta_profit_factor"] = prelim_deltas.get("delta_profit_factor")
                    summary_info["delta_total_r"] = prelim_deltas.get("delta_total_r")
            except Exception:
                pass
        results.append(summary_info)
    return results


@router.get("/audit/{experiment_id}", response_model=ExperimentAuditReport)
def get_experiment_audit_endpoint(experiment_id: str) -> ExperimentAuditReport:
    """Run an independent audit and reconstruction of the experiment."""
    try:
        return run_experiment_audit(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Audit failed for experiment %s", experiment_id)
        raise HTTPException(status_code=500, detail=f"Audit execution failed: {e}")


@router.post("/audit/{experiment_id}", response_model=ExperimentAuditReport)
def post_experiment_audit_endpoint(experiment_id: str) -> ExperimentAuditReport:
    """Trigger a fresh independent audit of the experiment."""
    try:
        return run_experiment_audit(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Audit failed for experiment %s", experiment_id)
        raise HTTPException(status_code=500, detail=f"Audit execution failed: {e}")


@router.get("/{experiment_id}", response_model=ExperimentResult)
def get_experiment_detail(experiment_id: str) -> ExperimentResult:
    """Get full details and benchmarks for a specific experiment."""
    return _load_or_run_experiment(experiment_id)


@router.post("/run", response_model=ExperimentResult)
def run_experiment_endpoint(req: ExperimentRunRequest) -> ExperimentResult:
    """Trigger re-execution of a registered experiment."""
    return _load_or_run_experiment(req.experiment_id)

