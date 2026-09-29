import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_validation_api_unsupported_symbol():
    resp = client.post(
        "/api/validation/xauusd",
        json={"symbol": "EURUSD"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "UNSUPPORTED_SYMBOL"


def test_validation_api_invalid_date_range():
    resp = client.post(
        "/api/validation/xauusd",
        json={
            "symbol": "XAUUSD",
            "start": "2026-03-10T00:00:00",
            "end": "2026-03-01T00:00:00"  # End is before start
        }
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_DATE_RANGE"


def test_validation_api_invalid_simulations():
    resp = client.post(
        "/api/validation/xauusd",
        json={
            "symbol": "XAUUSD",
            "monte_carlo_simulations": 5  # Below minimum allowed
        }
    )
    assert resp.status_code in [400, 422]


def test_validation_api_valid_request():
    resp = client.post(
        "/api/validation/xauusd",
        json={
            "symbol": "XAUUSD",
            "start": "2026-09-15T00:00:00",
            "end": "2026-09-25T00:00:00",
            "train_days": 7,
            "validation_days": 2,
            "step_days": 1,
            "signal_threshold": 7,
            "monte_carlo_simulations": 100,
            "random_seed": 42
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "XAUUSD"
    assert "validation_run_id" in data
    assert "dataset_coverage" in data
    assert "data_quality" in data
    assert "validation_status" in data
    assert "oos_consistency" in data
    assert "overall_metrics" in data
    assert "walk_forward" in data
    assert "out_of_sample" in data
    assert "spread_sensitivity" in data
    assert "threshold_sensitivity_development" in data
    assert "exit_sensitivity_development" in data
    assert "monte_carlo" in data
    assert "robustness_summary" in data


def test_validation_api_export():
    # First run a validation to populate or pass body
    resp = client.post(
        "/api/validation/xauusd/export",
        json={
            "symbol": "XAUUSD",
            "start": "2026-09-15T00:00:00",
            "end": "2026-09-25T00:00:00",
            "train_days": 7,
            "validation_days": 2,
            "step_days": 1,
            "signal_threshold": 7,
            "monte_carlo_simulations": 100,
            "random_seed": 42
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "csv_files" in data
    assert "historical_data_summary.csv" in data["csv_files"]
    assert "walk_forward_results.csv" in data["csv_files"]
    assert "oos_results.csv" in data["csv_files"]
    assert "monthly_results.csv" in data["csv_files"]
    assert "spread_sensitivity.csv" in data["csv_files"]
    assert "threshold_sensitivity.csv" in data["csv_files"]
    assert "exit_sensitivity.csv" in data["csv_files"]
    assert "diagnostics.csv" in data["csv_files"]

