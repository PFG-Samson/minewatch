import os
import sqlite3
import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import rasterio
from fastapi.testclient import TestClient

# Add the backend directory to sys.path if needed
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.main import app, init_db, get_db

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Fixture for a temporary data directory."""
    tmp_dir = tmp_path_factory.mktemp("minewatch_data")
    (tmp_dir / "imagery").mkdir()
    (tmp_dir / "mosaics").mkdir()
    (tmp_dir / "indices").mkdir()
    (tmp_dir / "cache").mkdir()
    return tmp_dir

@pytest.fixture(scope="function")
def mock_db(tmp_path):
    """Fixture for an in-memory SQLite database with schema."""
    db_file = tmp_path / "test_minewatch.db"
    
    # Patch the DB_PATH in main.py
    with patch("backend.main.DB_PATH", db_file):
        init_db()
        # Use check_same_thread=False for FastAPI/TestClient
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.close()

@pytest.fixture(scope="function")
def api_client(tmp_path):
    """Fixture for FastAPI TestClient with its own fresh DB."""
    db_file = tmp_path / "test_minewatch.db"
    
    with patch("backend.main.DB_PATH", db_file):
        init_db()
        
        def _get_test_db():
            conn = sqlite3.connect(db_file, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
            
        with patch("backend.main.get_db", side_effect=_get_test_db):
            client = TestClient(app)
            yield client

@pytest.fixture
def mock_raster_file(tmp_path):
    """Helper to create a dummy raster file."""
    def _create_raster(filename, shape=(100, 100), crs="EPSG:4326", transform=None, dtype=np.uint16, nodata=0):
        path = tmp_path / filename
        if transform is None:
            from rasterio.transform import from_origin
            transform = from_origin(0, 10, 0.1, 0.1)
        
        with rasterio.open(
            path, 'w',
            driver='GTiff',
            height=shape[0],
            width=shape[1],
            count=1,
            dtype=dtype,
            crs=crs,
            transform=transform,
            nodata=nodata
        ) as dst:
            dst.write(np.ones(shape, dtype=dtype) * 100, 1)
        return str(path)
    return _create_raster

@pytest.fixture
def mock_requests():
    """Fixture to mock outgoing HTTP requests."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        yield mock_get, mock_post

@pytest.fixture
def sample_boundary():
    """Valid GeoJSON boundary for testing."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [0.0, 0.0],
            [0.1, 0.0],
            [0.1, 0.1],
            [0.0, 0.1],
            [0.0, 0.0]
        ]]
    }
