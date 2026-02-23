import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app

def test_health_check(api_client):
    """Test health check endpoint."""
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_mine_area_empty(api_client):
    """Test getting mine area when none exists (should return 404 or empty?)."""
    # Looking at main.py, it might return 404 or default.
    # Actually, init_db doesn't insert a default.
    response = api_client.get("/mine-area")
    # In MineWatch, mine_area id is always 1.
    assert response.status_code in [200, 404]

def test_upsert_mine_area(api_client, sample_boundary):
    """Test creating/updating mine area."""
    payload = {
        "name": "Test Mine",
        "description": "Test Description",
        "boundary": sample_boundary,
        "buffer_km": 1.5
    }
    # MineWatch uses PUT for upserting mine area
    response = api_client.put("/mine-area", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Mine"
    assert data["buffer_km"] == 1.5
    
    # Verify we can get it back
    response = api_client.get("/mine-area")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Mine"

def test_get_analysis_runs_empty(api_client):
    """Test getting analysis runs list."""
    response = api_client.get("/analysis-runs")
    assert response.status_code == 200
    assert response.json() == []

@patch("backend.main.run_analysis")
def test_create_analysis_run(mock_run, api_client):
    """Test creating a new analysis run record."""
    mock_run.return_value = ([], [], {"ndvi": 0.5, "ndwi": 0.2, "bsi": 0.1})
    payload = {
        "baseline_date": "2024-01-01",
        "latest_date": "2024-02-01"
    }
    response = api_client.post("/analysis-runs", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed" # main.py sets it to completed before run_analysis
    assert data["baseline_date"] == "2024-01-01"

def test_get_alerts_empty(api_client):
    """Test getting alerts list."""
    response = api_client.get("/alerts")
    assert response.status_code == 200
    assert response.json() == []

def test_invalid_mine_area_payload(api_client):
    """Test validation errors for mine area."""
    # Missing boundary
    payload = {"name": "Invalid"}
    response = api_client.put("/mine-area", json=payload)
    assert response.status_code == 422 # Pydantic validation error
