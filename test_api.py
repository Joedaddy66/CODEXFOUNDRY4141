"""
Tests for RA Longevity MLOps API

Run with: pytest test_api.py -v
"""

import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, ARTIFACTS_DIR

# Test client
client = TestClient(app)

# Test bearer token
TEST_TOKEN = "demo-token-replace-in-production"
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_TOKEN}"}


def create_test_analysis():
    """Helper function to create a test analysis and return run_id"""
    test_data = {
        "data": [
            {"value": 10, "metric": 20},
            {"value": 15, "metric": 25},
            {"value": 20, "metric": 30},
            {"value": 25, "metric": 35},
            {"value": 30, "metric": 40}
        ],
        "mode": "tabular"
    }
    
    response = client.post(
        "/api/longevity/analyze",
        headers=AUTH_HEADERS,
        json=test_data
    )
    
    assert response.status_code == 200
    return response.json()["run_id"]


def test_root_endpoint():
    """Test root endpoint returns API information"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["service"] == "RA Longevity MLOps API"
    assert "endpoints" in data


def test_unauthorized_access():
    """Test that endpoints require authentication"""
    # Test without token
    response = client.post("/api/longevity/analyze")
    assert response.status_code == 401
    
    # Test with invalid token
    response = client.post(
        "/api/longevity/analyze",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401


def test_analyze_with_json_data():
    """Test analyze endpoint with JSON data"""
    test_data = {
        "data": [
            {"value": 10, "metric": 20},
            {"value": 15, "metric": 25},
            {"value": 20, "metric": 30},
            {"value": 25, "metric": 35},
            {"value": 30, "metric": 40}
        ],
        "mode": "tabular"
    }
    
    response = client.post(
        "/api/longevity/analyze",
        headers=AUTH_HEADERS,
        json=test_data
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "run_id" in data
    assert "predictions" in data
    assert "ldrop_metrics" in data
    assert "ra_score_deltas" in data
    assert "timestamp" in data
    
    # Verify predictions
    assert len(data["predictions"]) == 5
    assert all(isinstance(p, (int, float)) for p in data["predictions"])
    
    # Verify ldrop_metrics
    assert "mean_prediction" in data["ldrop_metrics"]
    assert "std_prediction" in data["ldrop_metrics"]
    assert "ldrop_threshold" in data["ldrop_metrics"]
    
    # Verify ra_score_deltas
    assert "ra_mean" in data["ra_score_deltas"]


def test_analyze_with_csv_file():
    """Test analyze endpoint with CSV file upload"""
    # Create temporary CSV content
    csv_content = "value,metric\n10,20\n15,25\n20,30\n25,35\n30,40"
    
    files = {"file": ("test_data.csv", csv_content, "text/csv")}
    
    response = client.post(
        "/api/longevity/analyze/csv",
        headers=AUTH_HEADERS,
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "run_id" in data
    assert "predictions" in data
    assert len(data["predictions"]) == 5


def test_get_report_json():
    """Test retrieving JSON report"""
    # First create an analysis
    run_id = create_test_analysis()
    
    # Get JSON report
    response = client.get(
        f"/api/longevity/report/{run_id}",
        headers=AUTH_HEADERS
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "run_id" in data
    assert data["run_id"] == run_id
    assert "predictions" in data
    assert "ldrop_metrics" in data


def test_get_report_html():
    """Test retrieving HTML report"""
    # First create an analysis
    run_id = create_test_analysis()
    
    # Get HTML report
    response = client.get(
        f"/api/longevity/report/{run_id}?format=html",
        headers=AUTH_HEADERS
    )
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"RA Longevity Analysis Report" in response.content


def test_get_report_not_found():
    """Test retrieving report for non-existent run_id"""
    response = client.get(
        "/api/longevity/report/nonexistent-run-id",
        headers=AUTH_HEADERS
    )
    
    assert response.status_code == 404


def test_deploy_model_success():
    """Test successful model deployment"""
    # First create an analysis
    run_id = create_test_analysis()
    
    # Deploy the model
    deploy_data = {
        "run_id": run_id,
        "human_key": "human-approval-key-12345678",
        "logic_key": "logic-validation-key-87654321",
        "model_name": "test_model_v1"
    }
    
    response = client.post(
        "/api/longevity/deploy",
        headers=AUTH_HEADERS,
        json=deploy_data
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["run_id"] == run_id
    assert data["model_name"] == "test_model_v1"
    assert "deployed_at" in data


def test_deploy_model_missing_keys():
    """Test deployment fails with missing keys"""
    run_id = create_test_analysis()
    
    # Try to deploy without keys
    deploy_data = {
        "run_id": run_id,
        "human_key": "",
        "logic_key": "logic-key"
    }
    
    response = client.post(
        "/api/longevity/deploy",
        headers=AUTH_HEADERS,
        json=deploy_data
    )
    
    assert response.status_code == 400


def test_deploy_model_short_keys():
    """Test deployment fails with short keys"""
    run_id = create_test_analysis()
    
    # Try to deploy with keys that are too short
    deploy_data = {
        "run_id": run_id,
        "human_key": "short",
        "logic_key": "key"
    }
    
    response = client.post(
        "/api/longevity/deploy",
        headers=AUTH_HEADERS,
        json=deploy_data
    )
    
    assert response.status_code == 400


def test_deploy_model_not_found():
    """Test deployment fails for non-existent run_id"""
    deploy_data = {
        "run_id": "nonexistent-run-id",
        "human_key": "human-approval-key-12345678",
        "logic_key": "logic-validation-key-87654321"
    }
    
    response = client.post(
        "/api/longevity/deploy",
        headers=AUTH_HEADERS,
        json=deploy_data
    )
    
    assert response.status_code == 404


def test_ra_feature_encoding():
    """Test that RA features are properly encoded"""
    from main import encode_ra_features
    import pandas as pd
    
    # Create test dataframe
    df = pd.DataFrame({
        'value': [10, 15, 20, 25, 30],
        'metric': [20, 25, 30, 35, 40]
    })
    
    # Encode features
    df_encoded = encode_ra_features(df)
    
    # Check that RA features are present
    assert 'RA' in df_encoded.columns
    assert 'D' in df_encoded.columns
    assert 'M' in df_encoded.columns
    assert 'S' in df_encoded.columns
    assert 'LR' in df_encoded.columns
    
    # Check RA is normalized (between 0 and 1)
    assert df_encoded['RA'].min() >= 0
    assert df_encoded['RA'].max() <= 1


def test_ldrop_metrics_calculation():
    """Test L-drop metrics calculation"""
    from main import calculate_ldrop_metrics
    import pandas as pd
    
    df = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
    predictions = [0.3, 0.6, 0.7, 0.4, 0.8]
    
    metrics = calculate_ldrop_metrics(df, predictions)
    
    assert "mean_prediction" in metrics
    assert "std_prediction" in metrics
    assert "min_prediction" in metrics
    assert "max_prediction" in metrics
    assert "ldrop_threshold" in metrics
    assert "samples_below_threshold" in metrics
    
    # Verify calculations
    assert metrics["samples_below_threshold"] == 2  # 0.3 and 0.4 are below 0.5


def test_ra_score_deltas_calculation():
    """Test RA score deltas calculation"""
    from main import calculate_ra_score_deltas, encode_ra_features
    import pandas as pd
    
    df = pd.DataFrame({'value': [10, 15, 20, 25, 30]})
    df_encoded = encode_ra_features(df)
    
    deltas = calculate_ra_score_deltas(df_encoded)
    
    assert "ra_mean" in deltas
    assert "ra_std" in deltas
    assert "ra_delta_mean" in deltas
    assert "ra_momentum" in deltas
    assert "ra_stability" in deltas


def test_artifacts_created():
    """Test that artifacts are created after analysis"""
    run_id = create_test_analysis()
    
    run_dir = ARTIFACTS_DIR / run_id
    
    # Check that artifacts directory exists
    assert run_dir.exists()
    
    # Check that required files exist
    assert (run_dir / "results.json").exists()
    assert (run_dir / "report.html").exists()
    assert (run_dir / "bundle.zip").exists()
    
    # Check if DKIL lock was created (depends on threshold)
    # This may or may not exist depending on the data


def test_dkil_check():
    """Test DKIL check functionality"""
    from main import check_dkil
    
    run_id = create_test_analysis()
    
    # Check DKIL - may pass or fail depending on data
    passed, dkil_data = check_dkil(run_id)
    
    # If DKIL file doesn't exist, check should fail
    if not passed:
        assert "error" in dkil_data or "integrity_check" in dkil_data


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
